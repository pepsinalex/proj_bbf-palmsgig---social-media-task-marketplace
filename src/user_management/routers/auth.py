"""
Authentication Router for user registration and verification.

Provides endpoints for user registration, email verification, and phone verification.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import (
    get_app_settings,
    get_database_session,
    get_redis,
    require_authentication,
)
from src.shared.config import Settings
from src.user_management.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserRegistration,
    UserResponse,
    UserSessionsResponse,
    VerificationRequest,
    VerificationResponse,
)
from src.user_management.services.auth import AuthService
from src.user_management.services.notification import NotificationService
from src.user_management.services.password import PasswordService
from src.user_management.services.user import UserService
from src.user_management.services.verification import VerificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


async def get_password_service() -> PasswordService:
    """Dependency for password service."""
    return PasswordService(bcrypt_rounds=12)


async def get_verification_service(
    redis: Annotated[Redis, Depends(get_redis)]
) -> VerificationService:
    """Dependency for verification service."""
    return VerificationService(redis_client=redis)


async def get_notification_service() -> NotificationService:
    """Dependency for notification service."""
    return NotificationService()


async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_database_session)]
) -> UserService:
    """Dependency for user service."""
    return UserService(session=session)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthService:
    """Dependency for auth service."""
    return AuthService(db_session=session, redis_client=redis, settings=settings)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and phone verification required",
)
async def register_user(
    registration_data: UserRegistration,
    user_service: Annotated[UserService, Depends(get_user_service)],
    password_service: Annotated[PasswordService, Depends(get_password_service)],
    verification_service: Annotated[VerificationService, Depends(get_verification_service)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> UserResponse:
    """
    Register a new user account.

    This endpoint:
    1. Validates input data (email format, password strength, phone number format)
    2. Checks for duplicate email/username/phone
    3. Hashes the password using bcrypt
    4. Creates the user account in the database
    5. Generates and stores verification tokens for email and phone
    6. Sends verification emails and SMS

    Args:
        registration_data: User registration data
        user_service: User service dependency
        password_service: Password service dependency
        verification_service: Verification service dependency
        notification_service: Notification service dependency

    Returns:
        Created user data

    Raises:
        HTTPException 400: If email/username/phone already exists
        HTTPException 500: If registration fails
    """
    try:
        logger.info(f"Registration attempt for email: {registration_data.email}")

        is_valid, error_message = password_service.validate_password_strength(
            registration_data.password
        )
        if not is_valid:
            logger.warning(f"Weak password provided: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
            )

        if await user_service.email_exists(registration_data.email):
            logger.warning(f"Email already exists: {registration_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered",
            )

        if await user_service.username_exists(registration_data.username):
            logger.warning(f"Username already exists: {registration_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken",
            )

        if await user_service.phone_exists(registration_data.phone_number):
            logger.warning(f"Phone already exists: {registration_data.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already registered",
            )

        password_hash = password_service.hash_password(registration_data.password)

        user = await user_service.create_user(
            email=registration_data.email,
            username=registration_data.username,
            password_hash=password_hash,
            phone_number=registration_data.phone_number,
            full_name=registration_data.full_name,
        )

        email_token = verification_service.generate_token()
        phone_token = verification_service.generate_token()

        await verification_service.store_token(
            identifier=user.email,
            token=email_token,
            token_type="email",
            user_id=str(user.id),
        )
        await verification_service.store_token(
            identifier=user.phone,
            token=phone_token,
            token_type="phone",
            user_id=str(user.id),
        )

        await notification_service.send_email_verification(
            to_email=user.email,
            token=email_token,
            username=user.username,
        )
        await notification_service.send_phone_verification(
            to_phone=user.phone,
            token=phone_token,
        )

        logger.info(f"User registered successfully: {user.id} ({user.email})")

        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.profile_data.get("full_name") if user.profile_data else None,
            phone_number=user.phone,
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during registration: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later.",
        )


@router.post(
    "/verify-email",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email address",
    description="Verify user's email address using the verification token sent via email",
)
async def verify_email(
    verification_data: VerificationRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
    verification_service: Annotated[VerificationService, Depends(get_verification_service)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> VerificationResponse:
    """
    Verify user's email address.

    Args:
        verification_data: Verification request with email and token
        user_service: User service dependency
        verification_service: Verification service dependency
        notification_service: Notification service dependency

    Returns:
        Verification response with success status

    Raises:
        HTTPException 400: If verification fails or rate limit exceeded
    """
    try:
        if not verification_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is required for email verification",
            )

        logger.info(f"Email verification attempt for: {verification_data.email}")

        is_valid, user_id = await verification_service.verify_token(
            identifier=verification_data.email,
            token=verification_data.token,
            token_type="email",
        )

        if not is_valid:
            logger.warning(f"Invalid email verification token for: {verification_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        if not user_id:
            user = await user_service.get_user_by_email(verification_data.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            user_id = str(user.id)

        success = await user_service.verify_email(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify email",
            )

        user = await user_service.get_user_by_id(user_id)
        if user:
            await notification_service.send_welcome_email(
                to_email=user.email, username=user.username
            )

        logger.info(f"Email verified successfully: {verification_data.email}")

        return VerificationResponse(
            success=True, message="Email verified successfully", user_id=user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed. Please try again later.",
        )


@router.post(
    "/verify-phone",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify phone number",
    description="Verify user's phone number using the verification token sent via SMS",
)
async def verify_phone(
    verification_data: VerificationRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
    verification_service: Annotated[VerificationService, Depends(get_verification_service)],
) -> VerificationResponse:
    """
    Verify user's phone number.

    Args:
        verification_data: Verification request with phone and token
        user_service: User service dependency
        verification_service: Verification service dependency

    Returns:
        Verification response with success status

    Raises:
        HTTPException 400: If verification fails or rate limit exceeded
    """
    try:
        if not verification_data.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required for phone verification",
            )

        logger.info(f"Phone verification attempt for: {verification_data.phone_number}")

        is_valid, user_id = await verification_service.verify_token(
            identifier=verification_data.phone_number,
            token=verification_data.token,
            token_type="phone",
        )

        if not is_valid:
            logger.warning(
                f"Invalid phone verification token for: {verification_data.phone_number}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        if not user_id:
            user = await user_service.get_user_by_phone(verification_data.phone_number)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            user_id = str(user.id)

        success = await user_service.verify_phone(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify phone",
            )

        logger.info(f"Phone verified successfully: {verification_data.phone_number}")

        return VerificationResponse(
            success=True, message="Phone verified successfully", user_id=user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Phone verification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Phone verification failed. Please try again later.",
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with email and password, returning JWT tokens",
)
async def login(
    login_data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    request: Annotated[Any, Depends(lambda: None)],
) -> LoginResponse:
    """
    Login user with email and password.

    This endpoint:
    1. Validates credentials (email and password)
    2. Checks account status (locked, inactive)
    3. Creates JWT access and refresh tokens
    4. Establishes a new session with device fingerprinting
    5. Returns tokens and user information

    Args:
        login_data: Login credentials
        auth_service: Auth service dependency
        request: FastAPI request object for extracting IP and user agent

    Returns:
        Login response with JWT tokens and user info

    Raises:
        HTTPException 400: If credentials are invalid
        HTTPException 401: If account is locked or inactive
        HTTPException 500: If login fails
    """
    try:
        logger.info(f"Login attempt for email: {login_data.email}")

        user_agent = None
        ip_address = None

        result = await auth_service.login(
            email=login_data.email,
            password=login_data.password,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        logger.info(f"User logged in successfully: {login_data.email}")

        return LoginResponse(**result)

    except ValueError as e:
        logger.warning(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Login failed with unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again later.",
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout user by invalidating access and refresh tokens",
)
async def logout(
    logout_data: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    access_token: Annotated[str, Depends(require_authentication)],
) -> LogoutResponse:
    """
    Logout user by invalidating tokens.

    This endpoint:
    1. Validates and blacklists the access token
    2. Optionally blacklists the refresh token
    3. Terminates the associated session

    Args:
        logout_data: Logout request with optional refresh token
        auth_service: Auth service dependency
        access_token: Current access token from Authorization header

    Returns:
        Logout response with confirmation message

    Raises:
        HTTPException 401: If token is invalid
        HTTPException 500: If logout fails
    """
    try:
        logger.info("Logout attempt")

        result = await auth_service.logout(
            access_token=access_token,
            refresh_token=logout_data.refresh_token,
        )

        logger.info("User logged out successfully")

        return LogoutResponse(**result)

    except ValueError as e:
        logger.warning(f"Logout failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Logout failed with unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed. Please try again later.",
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh tokens",
    description="Refresh access token using a valid refresh token",
)
async def refresh_tokens(
    refresh_data: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    request: Annotated[Any, Depends(lambda: None)],
) -> RefreshTokenResponse:
    """
    Refresh access and refresh tokens.

    This endpoint:
    1. Validates the provided refresh token
    2. Generates new access and refresh tokens (token rotation)
    3. Blacklists the old refresh token
    4. Updates the session with new token information

    Args:
        refresh_data: Refresh token request
        auth_service: Auth service dependency
        request: FastAPI request object for extracting IP and user agent

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException 401: If refresh token is invalid or expired
        HTTPException 500: If token refresh fails
    """
    try:
        logger.info("Token refresh attempt")

        user_agent = None
        ip_address = None

        result = await auth_service.refresh_tokens(
            refresh_token=refresh_data.refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        logger.info("Tokens refreshed successfully")

        return RefreshTokenResponse(**result)

    except ValueError as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Token refresh failed with unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please try again later.",
        )


@router.get(
    "/sessions",
    response_model=UserSessionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user sessions",
    description="Get all active sessions for the authenticated user",
)
async def get_sessions(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[str, Depends(require_authentication)],
) -> UserSessionsResponse:
    """
    Get all active sessions for the authenticated user.

    This endpoint:
    1. Validates the access token
    2. Retrieves all active sessions for the user
    3. Returns session information including device and activity details

    Args:
        auth_service: Auth service dependency
        user_id: User ID from authenticated token

    Returns:
        List of active user sessions

    Raises:
        HTTPException 401: If token is invalid
        HTTPException 500: If retrieval fails
    """
    try:
        logger.info(f"Retrieving sessions for user: {user_id}")

        sessions = await auth_service.get_user_sessions(user_id)

        logger.info(f"Retrieved {len(sessions)} sessions for user: {user_id}")

        return UserSessionsResponse(sessions=sessions)

    except Exception as e:
        logger.error(f"Failed to retrieve user sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions. Please try again later.",
        )


@router.post(
    "/logout-all",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Logout from all devices",
    description="Logout user from all active sessions",
)
async def logout_all_devices(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: Annotated[str, Depends(require_authentication)],
) -> dict:
    """
    Logout user from all devices.

    This endpoint:
    1. Validates the access token
    2. Terminates all active sessions for the user
    3. Blacklists all refresh tokens

    Args:
        auth_service: Auth service dependency
        user_id: User ID from authenticated token

    Returns:
        Dictionary with count of terminated sessions

    Raises:
        HTTPException 401: If token is invalid
        HTTPException 500: If logout fails
    """
    try:
        logger.info(f"Logout all devices for user: {user_id}")

        result = await auth_service.logout_all_devices(user_id)

        logger.info(f"User logged out from all devices: {user_id}")

        return result

    except Exception as e:
        logger.error(f"Logout all devices failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout from all devices. Please try again later.",
        )
