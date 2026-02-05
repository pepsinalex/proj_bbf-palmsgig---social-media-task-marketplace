"""
MFA (Multi-Factor Authentication) API endpoints.

Provides REST API endpoints for MFA setup, verification, management,
backup codes, and SMS OTP operations.
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import get_current_user, get_database_session, get_redis
from src.shared.models.user import User
from src.user_management.schemas.mfa import (
    BackupCodeVerifyRequest,
    MFADisableRequest,
    MFASetupRequest,
    MFASetupResponse,
    MFAStatusResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    RecoveryCodesResponse,
    SMSOTPRequest,
    SMSOTPResponse,
    SMSOTPVerifyRequest,
)
from src.user_management.services.mfa.manager import MFAManager

router = APIRouter(prefix="/mfa", tags=["MFA"])
logger = logging.getLogger(__name__)


@router.post(
    "/setup",
    response_model=MFASetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Setup TOTP MFA",
    description="Initialize TOTP MFA setup and receive QR code and backup codes",
)
async def setup_mfa(
    request: MFASetupRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> MFASetupResponse:
    """
    Setup TOTP MFA for the authenticated user.

    Generates TOTP secret, QR code, and backup recovery codes.
    MFA is not enabled until verified with a valid token.

    Args:
        request: MFA setup request (empty body)
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        MFASetupResponse with secret, QR code, and backup codes

    Raises:
        HTTPException: If MFA is already enabled or setup fails
    """
    try:
        logger.info(f"MFA setup requested by user: {current_user.id}")

        mfa_manager = MFAManager(session, redis_client)
        setup_data = await mfa_manager.setup_totp_mfa(current_user, current_user.email)

        logger.info(f"MFA setup completed for user: {current_user.id}")
        return MFASetupResponse(**setup_data)

    except ValueError as e:
        logger.warning(f"MFA setup failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during MFA setup for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup MFA. Please try again later.",
        )


@router.post(
    "/verify",
    response_model=MFAVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify and enable TOTP MFA",
    description="Verify TOTP token and enable MFA for the account",
)
async def verify_and_enable_mfa(
    request: MFAVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> MFAVerifyResponse:
    """
    Verify TOTP token and enable MFA.

    Validates the provided TOTP token and enables MFA if valid.
    This must be called after /setup to complete MFA activation.

    Args:
        request: Verification request with TOTP token
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        MFAVerifyResponse indicating success or failure

    Raises:
        HTTPException: If verification fails or MFA already enabled
    """
    try:
        logger.info(f"MFA verification requested by user: {current_user.id}")

        mfa_manager = MFAManager(session, redis_client)
        success = await mfa_manager.verify_and_enable_totp_mfa(current_user, request.token)

        if success:
            logger.info(f"MFA enabled successfully for user: {current_user.id}")
            return MFAVerifyResponse(
                success=True,
                message="MFA has been enabled successfully",
            )
        else:
            logger.warning(f"MFA verification failed for user: {current_user.id}")
            return MFAVerifyResponse(
                success=False,
                message="Invalid verification code",
            )

    except ValueError as e:
        logger.warning(f"MFA verification error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during MFA verification for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA. Please try again later.",
        )


@router.post(
    "/disable",
    response_model=MFAVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Disable TOTP MFA",
    description="Disable MFA for the account after verifying TOTP token",
)
async def disable_mfa(
    request: MFADisableRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> MFAVerifyResponse:
    """
    Disable MFA for the user account.

    Requires a valid TOTP token to confirm the user's identity
    before disabling MFA.

    Args:
        request: Disable request with TOTP token
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        MFAVerifyResponse indicating success or failure

    Raises:
        HTTPException: If MFA not enabled or token invalid
    """
    try:
        logger.info(f"MFA disable requested by user: {current_user.id}")

        if not current_user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled for this account",
            )

        mfa_manager = MFAManager(session, redis_client)

        # Verify token before disabling
        token_valid = await mfa_manager.verify_totp_token(current_user, request.token)
        if not token_valid:
            logger.warning(f"Invalid token during MFA disable for user: {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification code",
            )

        # Disable MFA
        success = await mfa_manager.disable_mfa(current_user)

        if success:
            logger.info(f"MFA disabled successfully for user: {current_user.id}")
            return MFAVerifyResponse(
                success=True,
                message="MFA has been disabled successfully",
            )
        else:
            logger.error(f"Failed to disable MFA for user: {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disable MFA",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MFA disable for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable MFA. Please try again later.",
        )


@router.get(
    "/recovery-codes",
    response_model=RecoveryCodesResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate backup recovery codes",
    description="Generate new backup recovery codes (invalidates old ones)",
)
async def regenerate_recovery_codes(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> RecoveryCodesResponse:
    """
    Regenerate backup recovery codes.

    Generates new backup codes and invalidates existing ones.
    Requires MFA to be enabled.

    Args:
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        RecoveryCodesResponse with new backup codes

    Raises:
        HTTPException: If MFA not enabled or regeneration fails
    """
    try:
        logger.info(f"Recovery codes regeneration requested by user: {current_user.id}")

        if not current_user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled for this account",
            )

        mfa_manager = MFAManager(session, redis_client)
        backup_codes = await mfa_manager.regenerate_backup_codes(current_user)

        logger.info(f"Recovery codes regenerated for user: {current_user.id}")
        return RecoveryCodesResponse(
            backup_codes=backup_codes,
            generated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Recovery codes regeneration failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error regenerating recovery codes for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate recovery codes. Please try again later.",
        )


@router.post(
    "/sms",
    response_model=SMSOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Send SMS OTP",
    description="Send OTP via SMS as backup MFA method",
)
async def send_sms_otp(
    request: SMSOTPRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> SMSOTPResponse:
    """
    Send SMS OTP to user's phone.

    Sends a one-time password via SMS for backup authentication.
    Requires verified phone number and implements rate limiting.

    Args:
        request: SMS OTP request
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        SMSOTPResponse with send status and details

    Raises:
        HTTPException: If phone not verified or rate limit exceeded
    """
    try:
        logger.info(f"SMS OTP requested by user: {current_user.id}")

        mfa_manager = MFAManager(session, redis_client)
        success = await mfa_manager.send_sms_otp(current_user, resend=request.resend)

        if success:
            ttl = await mfa_manager.get_sms_otp_ttl(current_user)
            phone_last_digits = current_user.phone[-4:] if current_user.phone else None

            logger.info(f"SMS OTP sent successfully to user: {current_user.id}")
            return SMSOTPResponse(
                success=True,
                message="OTP sent successfully via SMS",
                phone_last_digits=phone_last_digits,
                expires_in=ttl,
            )
        else:
            logger.warning(f"Failed to send SMS OTP to user: {current_user.id}")
            return SMSOTPResponse(
                success=False,
                message="Failed to send SMS OTP",
                phone_last_digits=None,
                expires_in=None,
            )

    except ValueError as e:
        logger.warning(f"SMS OTP send error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error sending SMS OTP for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send SMS OTP. Please try again later.",
        )


@router.post(
    "/sms/verify",
    response_model=MFAVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify SMS OTP",
    description="Verify SMS OTP code",
)
async def verify_sms_otp(
    request: SMSOTPVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> MFAVerifyResponse:
    """
    Verify SMS OTP code.

    Validates the OTP code sent via SMS. Used as backup MFA method.

    Args:
        request: SMS OTP verification request
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        MFAVerifyResponse indicating success or failure

    Raises:
        HTTPException: If verification fails
    """
    try:
        logger.info(f"SMS OTP verification requested by user: {current_user.id}")

        mfa_manager = MFAManager(session, redis_client)
        is_valid = await mfa_manager.verify_sms_otp(current_user, request.otp)

        if is_valid:
            logger.info(f"SMS OTP verified successfully for user: {current_user.id}")
            return MFAVerifyResponse(
                success=True,
                message="SMS OTP verified successfully",
            )
        else:
            logger.warning(f"Invalid SMS OTP for user: {current_user.id}")
            return MFAVerifyResponse(
                success=False,
                message="Invalid or expired OTP code",
            )

    except Exception as e:
        logger.error(f"Unexpected error verifying SMS OTP for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify SMS OTP. Please try again later.",
        )


@router.get(
    "/status",
    response_model=MFAStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get MFA status",
    description="Get comprehensive MFA status for the account",
)
async def get_mfa_status(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> MFAStatusResponse:
    """
    Get MFA status for user.

    Returns comprehensive information about MFA configuration,
    backup methods, and remaining backup codes.

    Args:
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        MFAStatusResponse with detailed MFA status

    Raises:
        HTTPException: If status retrieval fails
    """
    try:
        logger.info(f"MFA status requested by user: {current_user.id}")

        mfa_manager = MFAManager(session, redis_client)
        status = await mfa_manager.get_mfa_status(current_user)

        return MFAStatusResponse(**status)

    except Exception as e:
        logger.error(f"Unexpected error getting MFA status for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve MFA status. Please try again later.",
        )


@router.post(
    "/verify-backup-code",
    response_model=MFAVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify backup recovery code",
    description="Verify and consume a backup recovery code",
)
async def verify_backup_code(
    request: BackupCodeVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis_client: Annotated[Redis, Depends(get_redis)],
) -> MFAVerifyResponse:
    """
    Verify backup recovery code.

    Validates a backup code and removes it from the available codes
    if valid (one-time use).

    Args:
        request: Backup code verification request
        current_user: Authenticated user
        session: Database session
        redis_client: Redis client

    Returns:
        MFAVerifyResponse indicating success or failure

    Raises:
        HTTPException: If MFA not enabled or verification fails
    """
    try:
        logger.info(f"Backup code verification requested by user: {current_user.id}")

        if not current_user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled for this account",
            )

        mfa_manager = MFAManager(session, redis_client)
        is_valid = await mfa_manager.verify_backup_code(current_user, request.code)

        if is_valid:
            logger.info(f"Backup code verified successfully for user: {current_user.id}")
            return MFAVerifyResponse(
                success=True,
                message="Backup code verified successfully",
            )
        else:
            logger.warning(f"Invalid backup code for user: {current_user.id}")
            return MFAVerifyResponse(
                success=False,
                message="Invalid backup code",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error verifying backup code for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify backup code. Please try again later.",
        )
