"""
MFA Manager coordinating TOTP and SMS authentication methods.

Implements MFA setup workflow, verification coordination, recovery code management,
MFA disable functionality, and backup method handling.
"""

import logging
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.user import User
from src.user_management.services.mfa.sms import SMSOTPService
from src.user_management.services.mfa.totp import TOTPService

logger = logging.getLogger(__name__)


class MFAManager:
    """Manager service for coordinating MFA operations."""

    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis) -> None:
        """
        Initialize MFA manager.

        Args:
            session: SQLAlchemy async session for database operations
            redis_client: Async Redis client for temporary storage
        """
        self.session = session
        self.redis_client = redis_client
        self.totp_service = TOTPService()
        self.sms_service = SMSOTPService(redis_client)
        logger.debug("MFAManager initialized")

    async def setup_totp_mfa(
        self, user: User, user_email: str
    ) -> dict[str, any]:
        """
        Setup TOTP MFA for user.

        Generates TOTP secret, creates QR code, generates backup codes,
        and returns setup information. Does not enable MFA until verified.

        Args:
            user: User object
            user_email: User's email address

        Returns:
            Dictionary containing:
            - secret: Plain TOTP secret (for manual entry)
            - qr_code: Base64 QR code image data URL
            - backup_codes: List of recovery codes

        Raises:
            ValueError: If MFA is already enabled or setup fails

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")
            >>> setup_data = await manager.setup_totp_mfa(user, "user@example.com")
            >>> "secret" in setup_data and "qr_code" in setup_data
            True
        """
        try:
            if user.mfa_enabled:
                logger.warning(f"MFA already enabled for user: {user.id}")
                raise ValueError("MFA is already enabled for this account")

            # Generate TOTP secret
            secret = self.totp_service.generate_secret()

            # Generate QR code
            qr_code = self.totp_service.generate_qr_code(secret, user_email)

            # Generate backup codes
            backup_codes = self.totp_service.generate_backup_codes(count=10)

            # Store setup data temporarily in Redis (15 minutes)
            setup_key = f"mfa:setup:{user.id}"
            setup_data = {
                "secret": secret,
                "backup_codes": backup_codes,
                "timestamp": datetime.utcnow().isoformat(),
            }

            import json

            await self.redis_client.setex(
                setup_key, 900, json.dumps(setup_data)  # 15 minutes
            )

            logger.info(
                f"TOTP MFA setup initiated for user: {user.id}",
                extra={"user_id": user.id},
            )

            return {
                "secret": secret,
                "qr_code": qr_code,
                "backup_codes": backup_codes,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to setup TOTP MFA for user {user.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to setup MFA: {e}")

    async def verify_and_enable_totp_mfa(
        self, user: User, token: str
    ) -> bool:
        """
        Verify TOTP token and enable MFA for user.

        Retrieves temporary setup data, verifies the provided token,
        encrypts and stores the secret and backup codes in the database,
        and enables MFA for the user.

        Args:
            user: User object
            token: TOTP token to verify

        Returns:
            True if verification and enablement succeeded

        Raises:
            ValueError: If setup not found, token invalid, or enablement fails

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")
            >>> await manager.setup_totp_mfa(user, "user@example.com")
            >>> # User scans QR code and gets token
            >>> await manager.verify_and_enable_totp_mfa(user, "123456")
            True
        """
        try:
            if user.mfa_enabled:
                logger.warning(f"MFA already enabled for user: {user.id}")
                raise ValueError("MFA is already enabled for this account")

            # Retrieve setup data from Redis
            setup_key = f"mfa:setup:{user.id}"
            setup_data_json = await self.redis_client.get(setup_key)

            if not setup_data_json:
                logger.warning(f"No MFA setup found for user: {user.id}")
                raise ValueError("MFA setup not found or expired. Please start setup again.")

            import json

            setup_data = json.loads(setup_data_json)
            secret = setup_data["secret"]
            backup_codes = setup_data["backup_codes"]

            # Verify TOTP token
            if not self.totp_service.verify_token(secret, token):
                logger.warning(f"Invalid TOTP token during MFA setup for user: {user.id}")
                raise ValueError("Invalid verification code. Please try again.")

            # Encrypt secret and backup codes
            encrypted_secret = self.totp_service.encrypt_secret(secret)
            encrypted_backup_codes = self.totp_service.encrypt_backup_codes(backup_codes)

            # Update user model
            user.mfa_enabled = True
            user.totp_secret = encrypted_secret
            user.backup_codes = encrypted_backup_codes
            user.mfa_setup_at = datetime.utcnow()

            await self.session.commit()

            # Clean up temporary setup data
            await self.redis_client.delete(setup_key)

            logger.info(f"TOTP MFA enabled successfully for user: {user.id}")
            return True

        except ValueError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to verify and enable TOTP MFA for user {user.id}: {e}", exc_info=True
            )
            raise ValueError(f"Failed to enable MFA: {e}")

    async def verify_totp_token(self, user: User, token: str) -> bool:
        """
        Verify TOTP token for enabled MFA user.

        Args:
            user: User object with MFA enabled
            token: TOTP token to verify

        Returns:
            True if token is valid

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")  # MFA enabled
            >>> await manager.verify_totp_token(user, "123456")
            True
        """
        try:
            if not user.mfa_enabled or not user.totp_secret:
                logger.warning(f"MFA not enabled for user: {user.id}")
                return False

            # Decrypt secret
            secret = self.totp_service.decrypt_secret(user.totp_secret)

            # Verify token
            is_valid = self.totp_service.verify_token(secret, token)

            if is_valid:
                logger.info(f"TOTP token verified for user: {user.id}")
            else:
                logger.warning(f"Invalid TOTP token for user: {user.id}")

            return is_valid

        except Exception as e:
            logger.error(f"Failed to verify TOTP token for user {user.id}: {e}", exc_info=True)
            return False

    async def verify_backup_code(self, user: User, code: str) -> bool:
        """
        Verify and consume backup recovery code.

        Args:
            user: User object with MFA enabled
            code: Backup code to verify

        Returns:
            True if code was valid and consumed

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")  # MFA enabled
            >>> await manager.verify_backup_code(user, "ABCD-1234-EFGH")
            True
        """
        try:
            if not user.mfa_enabled or not user.backup_codes:
                logger.warning(f"MFA not enabled or no backup codes for user: {user.id}")
                return False

            # Verify and update backup codes
            is_valid, new_encrypted = self.totp_service.verify_backup_code(
                user.backup_codes, code
            )

            if is_valid:
                # Update user's backup codes
                user.backup_codes = new_encrypted
                await self.session.commit()

                logger.info(f"Backup code verified and consumed for user: {user.id}")
                return True
            else:
                logger.warning(f"Invalid backup code for user: {user.id}")
                return False

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to verify backup code for user {user.id}: {e}", exc_info=True)
            return False

    async def regenerate_backup_codes(self, user: User) -> list[str]:
        """
        Regenerate backup recovery codes for user.

        Generates new backup codes and replaces existing ones.

        Args:
            user: User object with MFA enabled

        Returns:
            List of new backup codes

        Raises:
            ValueError: If MFA not enabled or regeneration fails

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")  # MFA enabled
            >>> new_codes = await manager.regenerate_backup_codes(user)
            >>> len(new_codes)
            10
        """
        try:
            if not user.mfa_enabled:
                logger.warning(f"MFA not enabled for user: {user.id}")
                raise ValueError("MFA is not enabled for this account")

            # Generate new backup codes
            backup_codes = self.totp_service.generate_backup_codes(count=10)

            # Encrypt and store
            encrypted_backup_codes = self.totp_service.encrypt_backup_codes(backup_codes)
            user.backup_codes = encrypted_backup_codes

            await self.session.commit()

            logger.info(f"Backup codes regenerated for user: {user.id}")
            return backup_codes

        except ValueError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to regenerate backup codes for user {user.id}: {e}", exc_info=True
            )
            raise ValueError(f"Failed to regenerate backup codes: {e}")

    async def disable_mfa(self, user: User) -> bool:
        """
        Disable MFA for user account.

        Clears MFA secret, backup codes, and disables MFA flag.

        Args:
            user: User object

        Returns:
            True if MFA was disabled successfully

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")  # MFA enabled
            >>> await manager.disable_mfa(user)
            True
        """
        try:
            if not user.mfa_enabled:
                logger.info(f"MFA already disabled for user: {user.id}")
                return True

            # Clear MFA data
            user.mfa_enabled = False
            user.totp_secret = None
            user.backup_codes = None
            user.mfa_setup_at = None

            await self.session.commit()

            logger.info(f"MFA disabled for user: {user.id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to disable MFA for user {user.id}: {e}", exc_info=True)
            return False

    async def send_sms_otp(self, user: User, resend: bool = False) -> bool:
        """
        Send SMS OTP as backup MFA method.

        Args:
            user: User object
            resend: Whether this is a resend request

        Returns:
            True if SMS sent successfully

        Raises:
            ValueError: If phone not verified or rate limit exceeded

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")
            >>> await manager.send_sms_otp(user)
            True
        """
        try:
            if not user.phone or not user.phone_verified:
                logger.warning(f"Phone not verified for user: {user.id}")
                raise ValueError("Phone number not verified. Cannot send SMS.")

            # Send SMS OTP
            success = await self.sms_service.send_sms_otp(user.phone, user.id, resend=resend)

            if success:
                logger.info(f"SMS OTP sent to user: {user.id}")
            else:
                logger.error(f"Failed to send SMS OTP to user: {user.id}")

            return success

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to send SMS OTP for user {user.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to send SMS OTP: {e}")

    async def verify_sms_otp(self, user: User, otp: str) -> bool:
        """
        Verify SMS OTP code.

        Args:
            user: User object
            otp: OTP code to verify

        Returns:
            True if OTP is valid

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")
            >>> await manager.send_sms_otp(user)
            >>> # User receives OTP
            >>> await manager.verify_sms_otp(user, "123456")
            True
        """
        try:
            is_valid = await self.sms_service.verify_otp(user.id, otp)

            if is_valid:
                logger.info(f"SMS OTP verified for user: {user.id}")
            else:
                logger.warning(f"Invalid SMS OTP for user: {user.id}")

            return is_valid

        except Exception as e:
            logger.error(f"Failed to verify SMS OTP for user {user.id}: {e}", exc_info=True)
            return False

    async def get_mfa_status(self, user: User) -> dict[str, any]:
        """
        Get MFA status for user.

        Returns comprehensive MFA status including enabled state,
        backup method availability, and setup timestamp.

        Args:
            user: User object

        Returns:
            Dictionary containing MFA status information

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")
            >>> status = await manager.get_mfa_status(user)
            >>> "mfa_enabled" in status
            True
        """
        try:
            status = {
                "mfa_enabled": user.mfa_enabled,
                "totp_configured": bool(user.totp_secret),
                "phone_verified": user.phone_verified,
                "sms_backup_available": user.phone_verified and bool(user.phone),
                "backup_codes_count": 0,
                "mfa_setup_at": user.mfa_setup_at.isoformat() if user.mfa_setup_at else None,
            }

            # Count remaining backup codes
            if user.mfa_enabled and user.backup_codes:
                try:
                    codes = self.totp_service.decrypt_backup_codes(user.backup_codes)
                    status["backup_codes_count"] = len(codes)
                except Exception:
                    logger.warning(f"Failed to decrypt backup codes for user: {user.id}")

            return status

        except Exception as e:
            logger.error(f"Failed to get MFA status for user {user.id}: {e}", exc_info=True)
            return {
                "mfa_enabled": False,
                "totp_configured": False,
                "phone_verified": False,
                "sms_backup_available": False,
                "backup_codes_count": 0,
                "mfa_setup_at": None,
            }

    async def can_resend_sms(self, user: User) -> bool:
        """
        Check if user can request another SMS OTP.

        Args:
            user: User object

        Returns:
            True if user can request another SMS

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")
            >>> await manager.can_resend_sms(user)
            True
        """
        try:
            return await self.sms_service.can_resend_otp(user.id)
        except Exception as e:
            logger.error(f"Failed to check SMS resend for user {user.id}: {e}", exc_info=True)
            return False

    async def get_sms_otp_ttl(self, user: User) -> Optional[int]:
        """
        Get remaining TTL for SMS OTP.

        Args:
            user: User object

        Returns:
            Remaining seconds until OTP expires, or None if no OTP

        Example:
            >>> manager = MFAManager(session, redis_client)
            >>> user = await get_user_by_id("user123")
            >>> await manager.send_sms_otp(user)
            >>> ttl = await manager.get_sms_otp_ttl(user)
            >>> 0 < ttl <= 300
            True
        """
        try:
            return await self.sms_service.get_otp_ttl(user.id)
        except Exception as e:
            logger.error(f"Failed to get SMS OTP TTL for user {user.id}: {e}", exc_info=True)
            return None
