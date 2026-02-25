"""
Social Media Account API Endpoints.

Provides REST API for social media account management including OAuth flows,
account linking, verification, and disconnection with proper authentication
and error handling.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import get_database_session, require_authentication
from src.social_media.schemas.social_account import (
    AccountDisconnectResponse,
    AccountInfo,
    AccountLinkRequest,
    AccountLinkResponse,
    AccountList,
    AccountVerificationResponse,
    OAuthCallback,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social-accounts", tags=["social-accounts"])


@router.get(
    "/connect/{platform}",
    response_model=AccountLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate social media account connection",
    description="Generate OAuth authorization URL for connecting a social media account",
)
async def connect_account(
    platform: str,
    user_id: Annotated[str, Depends(require_authentication)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    scopes: Annotated[list[str] | None, Query()] = None,
    redirect_uri: Annotated[str | None, Query(max_length=500)] = None,
) -> AccountLinkResponse:
    """
    Initiate OAuth flow for connecting a social media account.

    Generates an authorization URL with state token for CSRF protection.
    User should be redirected to the authorization URL to grant permissions.

    Args:
        platform: Social media platform (facebook, instagram, twitter, etc.)
        user_id: Authenticated user ID from dependency
        session: Database session
        scopes: Optional custom OAuth scopes
        redirect_uri: Optional custom redirect URI

    Returns:
        Authorization URL and state token

    Raises:
        HTTPException 400: If platform is invalid or validation fails
        HTTPException 409: If account is already connected
        HTTPException 500: If OAuth service fails
    """
    logger.info(
        "Initiating account connection",
        extra={
            "user_id": user_id,
            "platform": platform,
            "scopes": scopes,
        },
    )

    try:
        # Import here to avoid circular imports
        from src.social_media.services.oauth_service import OAuthService

        oauth_service = OAuthService(session)

        # Generate authorization URL with state token
        auth_response = await oauth_service.generate_authorization_url(
            user_id=user_id,
            platform=platform,
            scopes=scopes,
            redirect_uri=redirect_uri,
        )

        logger.info(
            "Authorization URL generated",
            extra={
                "user_id": user_id,
                "platform": platform,
                "state": auth_response["state"][:10] + "...",
            },
        )

        return AccountLinkResponse(
            authorization_url=auth_response["authorization_url"],
            state=auth_response["state"],
            platform=platform,
        )

    except ValueError as e:
        logger.warning(
            "Account connection validation failed",
            extra={"user_id": user_id, "platform": platform, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Account connection failed",
            extra={
                "user_id": user_id,
                "platform": platform,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate account connection",
        )


@router.get(
    "/callback/{platform}",
    response_model=AccountInfo,
    status_code=status.HTTP_200_OK,
    summary="OAuth callback handler",
    description="Handle OAuth provider callback and complete account linking",
)
async def oauth_callback(
    platform: str,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query()] = None,
    session: Annotated[AsyncSession, Depends(get_database_session)] = None,
) -> AccountInfo:
    """
    Handle OAuth callback from social media platform.

    Exchanges authorization code for access token and creates/updates
    social media account record. Validates state token for CSRF protection.

    Args:
        platform: Social media platform
        code: Authorization code from OAuth provider
        state: State token for CSRF validation
        error: Error code from OAuth provider
        error_description: Error description from provider
        session: Database session

    Returns:
        Created/updated account information

    Raises:
        HTTPException 400: If callback parameters are invalid or OAuth fails
        HTTPException 401: If state validation fails (CSRF)
        HTTPException 500: If account creation fails
    """
    logger.info(
        "Processing OAuth callback",
        extra={
            "platform": platform,
            "has_code": code is not None,
            "has_error": error is not None,
            "state": state[:10] + "..." if state else None,
        },
    )

    # Check for OAuth error
    if error:
        logger.warning(
            "OAuth provider returned error",
            extra={
                "platform": platform,
                "error": error,
                "error_description": error_description,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}. {error_description or ''}",
        )

    # Validate required parameters
    if not code or not state:
        logger.warning(
            "Missing required OAuth callback parameters",
            extra={
                "platform": platform,
                "has_code": code is not None,
                "has_state": state is not None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters: code and state",
        )

    try:
        # Import here to avoid circular imports
        from src.social_media.services.account_service import AccountService
        from src.social_media.services.oauth_service import OAuthService

        oauth_service = OAuthService(session)
        account_service = AccountService(session)

        # Validate state and get user_id
        user_id = await oauth_service.validate_state(state)

        # Exchange code for tokens
        token_data = await oauth_service.exchange_code_for_token(
            platform=platform,
            code=code,
            state=state,
        )

        # Fetch account profile from platform
        profile_data = await oauth_service.fetch_account_profile(
            platform=platform,
            access_token=token_data["access_token"],
        )

        # Create or update account
        account = await account_service.link_account(
            user_id=user_id,
            platform=platform,
            account_id=profile_data["account_id"],
            username=profile_data.get("username"),
            display_name=profile_data.get("display_name"),
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=token_data.get("expires_at"),
            scope=token_data.get("scope"),
        )

        logger.info(
            "Account linked successfully",
            extra={
                "user_id": user_id,
                "platform": platform,
                "account_id": account.id,
            },
        )

        return AccountInfo.model_validate(account)

    except ValueError as e:
        logger.warning(
            "OAuth callback validation failed",
            extra={
                "platform": platform,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "OAuth callback processing failed",
            extra={
                "platform": platform,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process OAuth callback",
        )


@router.post(
    "/verify/{platform}",
    response_model=AccountVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify social media account ownership",
    description="Verify ownership of a connected social media account",
)
async def verify_account(
    platform: str,
    user_id: Annotated[str, Depends(require_authentication)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AccountVerificationResponse:
    """
    Verify ownership of a connected social media account.

    Performs verification by making an authenticated API call to the platform
    to confirm the account is still accessible and owned by the user.

    Args:
        platform: Social media platform
        user_id: Authenticated user ID from dependency
        session: Database session

    Returns:
        Verification status and timestamp

    Raises:
        HTTPException 400: If platform is invalid
        HTTPException 404: If account is not found
        HTTPException 401: If token is expired or invalid
        HTTPException 500: If verification fails
    """
    logger.info(
        "Verifying account",
        extra={
            "user_id": user_id,
            "platform": platform,
        },
    )

    try:
        # Import here to avoid circular imports
        from src.social_media.services.account_service import AccountService

        account_service = AccountService(session)

        # Verify account ownership
        account = await account_service.verify_account(
            user_id=user_id,
            platform=platform,
        )

        logger.info(
            "Account verified successfully",
            extra={
                "user_id": user_id,
                "platform": platform,
                "account_id": account.id,
            },
        )

        return AccountVerificationResponse(
            account_id=account.id,
            platform=platform,
            is_verified=account.is_verified,
            verified_at=account.last_verified_at,
            message="Account verified successfully",
        )

    except ValueError as e:
        logger.warning(
            "Account verification validation failed",
            extra={
                "user_id": user_id,
                "platform": platform,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Account verification failed",
            extra={
                "user_id": user_id,
                "platform": platform,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify account",
        )


@router.delete(
    "/disconnect/{platform}",
    response_model=AccountDisconnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Disconnect social media account",
    description="Remove connection to a social media account",
)
async def disconnect_account(
    platform: str,
    user_id: Annotated[str, Depends(require_authentication)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AccountDisconnectResponse:
    """
    Disconnect a social media account.

    Removes the account connection and securely deletes stored tokens.
    This action cannot be undone - user must reconnect to restore access.

    Args:
        platform: Social media platform
        user_id: Authenticated user ID from dependency
        session: Database session

    Returns:
        Disconnection confirmation

    Raises:
        HTTPException 400: If platform is invalid
        HTTPException 404: If account is not found
        HTTPException 500: If disconnection fails
    """
    logger.info(
        "Disconnecting account",
        extra={
            "user_id": user_id,
            "platform": platform,
        },
    )

    try:
        # Import here to avoid circular imports
        from src.social_media.services.account_service import AccountService

        account_service = AccountService(session)

        # Disconnect account
        account = await account_service.disconnect_account(
            user_id=user_id,
            platform=platform,
        )

        logger.info(
            "Account disconnected successfully",
            extra={
                "user_id": user_id,
                "platform": platform,
                "account_id": account.id,
            },
        )

        return AccountDisconnectResponse(
            account_id=account.id,
            platform=platform,
            message="Account disconnected successfully",
        )

    except ValueError as e:
        logger.warning(
            "Account disconnection validation failed",
            extra={
                "user_id": user_id,
                "platform": platform,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Account disconnection failed",
            extra={
                "user_id": user_id,
                "platform": platform,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect account",
        )


@router.get(
    "/accounts",
    response_model=AccountList,
    status_code=status.HTTP_200_OK,
    summary="List connected social media accounts",
    description="Get list of all connected social media accounts for authenticated user",
)
async def list_accounts(
    user_id: Annotated[str, Depends(require_authentication)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    platform: Annotated[str | None, Query(max_length=50)] = None,
    verified_only: Annotated[bool, Query()] = False,
) -> AccountList:
    """
    List all connected social media accounts.

    Returns list of accounts with filtering options. Does not expose
    sensitive token information.

    Args:
        user_id: Authenticated user ID from dependency
        session: Database session
        platform: Optional filter by platform
        verified_only: Only return verified accounts

    Returns:
        List of account information with total count

    Raises:
        HTTPException 400: If filters are invalid
        HTTPException 500: If retrieval fails
    """
    logger.info(
        "Listing accounts",
        extra={
            "user_id": user_id,
            "platform": platform,
            "verified_only": verified_only,
        },
    )

    try:
        # Import here to avoid circular imports
        from src.social_media.services.account_service import AccountService

        account_service = AccountService(session)

        # Get accounts with filters
        accounts = await account_service.get_user_accounts(
            user_id=user_id,
            platform=platform,
            verified_only=verified_only,
        )

        logger.info(
            "Accounts retrieved successfully",
            extra={
                "user_id": user_id,
                "count": len(accounts),
            },
        )

        account_infos = [AccountInfo.model_validate(account) for account in accounts]

        return AccountList(
            accounts=account_infos,
            total=len(account_infos),
        )

    except ValueError as e:
        logger.warning(
            "Account listing validation failed",
            extra={
                "user_id": user_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Account listing failed",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve accounts",
        )


@router.post(
    "/refresh/{platform}",
    response_model=AccountInfo,
    status_code=status.HTTP_200_OK,
    summary="Refresh social media account data",
    description="Fetch and update social media account data from platform API",
)
async def refresh_social_account(
    platform: str,
    user_id: Annotated[str, Depends(require_authentication)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AccountInfo:
    """
    Refresh social media account data.

    Fetches updated account information from the platform API including
    follower count and other profile details, then updates the stored
    account record in the database.

    Args:
        platform: Social media platform
        user_id: Authenticated user ID from dependency
        session: Database session

    Returns:
        Updated account information

    Raises:
        HTTPException 400: If platform is invalid or not supported
        HTTPException 404: If account is not found
        HTTPException 401: If token is expired or invalid
        HTTPException 500: If refresh fails or API error
    """
    logger.info(
        "Refreshing social account data",
        extra={
            "user_id": user_id,
            "platform": platform,
        },
    )

    try:
        # Import here to avoid circular imports
        from src.social_media.enums.platform_enums import Platform, get_platform_config
        from src.social_media.services.account_service import AccountService
        from src.social_media.services.platform_clients.facebook_client import (
            FacebookClient,
        )
        from src.social_media.services.platform_clients.instagram_client import (
            InstagramClient,
        )
        from src.social_media.services.platform_clients.twitter_client import (
            TwitterClient,
        )

        account_service = AccountService(session)

        # Get user's account for the platform
        accounts = await account_service.get_user_accounts(
            user_id=user_id,
            platform=platform,
        )

        if not accounts:
            logger.warning(
                "Social account not found",
                extra={
                    "user_id": user_id,
                    "platform": platform,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {platform} account found for this user",
            )

        account = accounts[0]

        # Validate platform
        try:
            platform_enum = Platform(platform.lower())
        except ValueError:
            logger.warning(
                "Invalid platform",
                extra={
                    "user_id": user_id,
                    "platform": platform,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform '{platform}' is not supported",
            )

        # Get access token
        access_token = account.get_access_token()
        if not access_token:
            logger.warning(
                "No access token available",
                extra={
                    "user_id": user_id,
                    "platform": platform,
                    "account_id": account.id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token not available. Please reconnect your account.",
            )

        # Check if token is expired
        if account.is_token_expired():
            logger.warning(
                "Access token expired",
                extra={
                    "user_id": user_id,
                    "platform": platform,
                    "account_id": account.id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token expired. Please reconnect your account.",
            )

        # Create appropriate platform client
        client = None
        try:
            if platform_enum == Platform.FACEBOOK:
                client = FacebookClient(access_token=access_token, redis_client=None)
            elif platform_enum == Platform.INSTAGRAM:
                client = InstagramClient(access_token=access_token, redis_client=None)
            elif platform_enum == Platform.TWITTER:
                client = TwitterClient(access_token=access_token, redis_client=None)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Platform '{platform}' does not support refresh",
                )

            # Fetch updated profile data
            profile_data = await client.verify_account()

            # Update account with fresh data
            if profile_data.get("username"):
                account.username = profile_data["username"]
            if profile_data.get("display_name"):
                account.display_name = profile_data["display_name"]
            if profile_data.get("followers_count") is not None:
                account.followers_count = profile_data["followers_count"]
            if profile_data.get("profile_url"):
                account.profile_url = profile_data["profile_url"]

            # Update last verified timestamp
            from datetime import datetime

            account.last_verified_at = datetime.utcnow()
            account.is_verified = True

            await session.commit()
            await session.refresh(account)

            logger.info(
                "Social account refreshed successfully",
                extra={
                    "user_id": user_id,
                    "platform": platform,
                    "account_id": account.id,
                },
            )

            return AccountInfo.model_validate(account)

        finally:
            if client:
                await client.close()

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "Account refresh validation failed",
            extra={
                "user_id": user_id,
                "platform": platform,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Account refresh failed",
            extra={
                "user_id": user_id,
                "platform": platform,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh account data",
        )
