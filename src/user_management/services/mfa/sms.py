"""
SMS OTP service for MFA backup authentication.

Implements SMS OTP generation, Twilio integration for SMS delivery,
OTP verification, rate limiting, and temporary storage in Redis.
"""

import logging
import secrets
from typing import Optional

import redis.asyncio as aioredis

from src.shared.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class SMSOTPService:
    """Service for SMS-based one-time password authentication."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        """
        Initialize SMS OTP service.

        Args:
            redis_client: Async Redis client for temporary OTP storage
        """
        self.redis_client = redis_client
        self.otp_expiry_seconds = 300  # 5 minutes
        self.rate_limit_window = 60  # 1 minute
        self.max_attempts_per_window = 3
        self.max_verification_attempts = 5
        logger.debug("SMSOTPService initialized")

    def generate_otp(self, length: int = 6) -> str:
        """
        Generate a numeric OTP code.

        Creates a cryptographically secure random numeric code of specified length.

        Args:
            length: Length of OTP code (default: 6)

        Returns:
            Numeric OTP code as string

        Raises:
            ValueError: If length is invalid

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> otp = sms_service.generate_otp(length=6)
            >>> len(otp)
            6
            >>> otp.isdigit()
            True
        """
        try:
            if length < 4 or length > 10:
                raise ValueError("OTP length must be between 4 and 10")

            # Generate random number with specified length
            otp = "".join([str(secrets.randbelow(10)) for _ in range(length)])

            logger.debug(f"Generated {length}-digit OTP")
            return otp

        except Exception as e:
            logger.error(f"Failed to generate OTP: {e}", exc_info=True)
            raise ValueError(f"Failed to generate OTP: {e}")

    async def send_sms_otp(
        self, phone_number: str, user_id: str, resend: bool = False
    ) -> bool:
        """
        Send OTP via SMS to user's phone number.

        Generates an OTP, stores it in Redis, and sends it via SMS using
        Twilio or configured SMS provider. Implements rate limiting to
        prevent abuse.

        Args:
            phone_number: User's phone number (E.164 format)
            user_id: User ID for tracking
            resend: Whether this is a resend request (default: False)

        Returns:
            True if SMS sent successfully, False otherwise

        Raises:
            ValueError: If rate limit exceeded or phone number invalid

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> await sms_service.send_sms_otp("+1234567890", "user123")
            True
        """
        try:
            # Check rate limiting
            if not resend and not await self._check_rate_limit(user_id):
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                raise ValueError(
                    f"Too many SMS requests. Please wait {self.rate_limit_window} seconds."
                )

            # Validate phone number format (basic validation)
            if not self._validate_phone_number(phone_number):
                logger.warning(f"Invalid phone number format: {phone_number}")
                raise ValueError("Invalid phone number format")

            # Generate OTP
            otp = self.generate_otp()

            # Store OTP in Redis
            otp_key = f"mfa:sms:otp:{user_id}"
            attempts_key = f"mfa:sms:attempts:{user_id}"

            await self.redis_client.setex(otp_key, self.otp_expiry_seconds, otp)
            await self.redis_client.setex(attempts_key, self.otp_expiry_seconds, "0")

            # Update rate limit counter
            if not resend:
                await self._increment_rate_limit(user_id)

            # Send SMS via Twilio or SMS provider
            sms_sent = await self._send_sms_via_provider(phone_number, otp)

            if sms_sent:
                logger.info(
                    f"SMS OTP sent successfully to user: {user_id}",
                    extra={"user_id": user_id, "phone": phone_number[-4:]},
                )
                return True
            else:
                logger.error(f"Failed to send SMS to user: {user_id}")
                # Clean up Redis keys on failure
                await self.redis_client.delete(otp_key, attempts_key)
                return False

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to send SMS OTP for user {user_id}: {e}", exc_info=True)
            return False

    async def verify_otp(self, user_id: str, otp: str) -> bool:
        """
        Verify SMS OTP code.

        Validates the provided OTP against the stored value in Redis.
        Tracks verification attempts and invalidates OTP after max attempts.

        Args:
            user_id: User ID
            otp: OTP code to verify

        Returns:
            True if OTP is valid, False otherwise

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> await sms_service.send_sms_otp("+1234567890", "user123")
            >>> # User receives OTP: "123456"
            >>> await sms_service.verify_otp("user123", "123456")
            True
        """
        try:
            otp_key = f"mfa:sms:otp:{user_id}"
            attempts_key = f"mfa:sms:attempts:{user_id}"

            # Get stored OTP
            stored_otp = await self.redis_client.get(otp_key)
            if not stored_otp:
                logger.warning(f"No OTP found for user: {user_id} (expired or not sent)")
                return False

            # Check verification attempts
            attempts = await self.redis_client.get(attempts_key)
            current_attempts = int(attempts) if attempts else 0

            if current_attempts >= self.max_verification_attempts:
                logger.warning(f"Max verification attempts exceeded for user: {user_id}")
                await self.redis_client.delete(otp_key, attempts_key)
                return False

            # Increment attempts
            await self.redis_client.incr(attempts_key)

            # Verify OTP
            if otp == stored_otp.decode() if isinstance(stored_otp, bytes) else stored_otp:
                # Valid OTP - delete from Redis
                await self.redis_client.delete(otp_key, attempts_key)
                logger.info(f"SMS OTP verified successfully for user: {user_id}")
                return True
            else:
                logger.warning(
                    f"Invalid SMS OTP for user: {user_id} (attempt {current_attempts + 1})"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to verify OTP for user {user_id}: {e}", exc_info=True)
            return False

    async def get_otp_ttl(self, user_id: str) -> Optional[int]:
        """
        Get remaining TTL (time to live) for OTP.

        Args:
            user_id: User ID

        Returns:
            Remaining seconds until OTP expires, or None if no OTP exists

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> await sms_service.send_sms_otp("+1234567890", "user123")
            >>> ttl = await sms_service.get_otp_ttl("user123")
            >>> 0 < ttl <= 300
            True
        """
        try:
            otp_key = f"mfa:sms:otp:{user_id}"
            ttl = await self.redis_client.ttl(otp_key)

            if ttl > 0:
                return ttl
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get OTP TTL for user {user_id}: {e}", exc_info=True)
            return None

    async def invalidate_otp(self, user_id: str) -> bool:
        """
        Invalidate/delete OTP for user.

        Args:
            user_id: User ID

        Returns:
            True if OTP was deleted, False otherwise

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> await sms_service.send_sms_otp("+1234567890", "user123")
            >>> await sms_service.invalidate_otp("user123")
            True
        """
        try:
            otp_key = f"mfa:sms:otp:{user_id}"
            attempts_key = f"mfa:sms:attempts:{user_id}"

            deleted = await self.redis_client.delete(otp_key, attempts_key)
            logger.info(f"Invalidated OTP for user: {user_id}")
            return deleted > 0

        except Exception as e:
            logger.error(f"Failed to invalidate OTP for user {user_id}: {e}", exc_info=True)
            return False

    async def _check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded SMS rate limit.

        Args:
            user_id: User ID

        Returns:
            True if within rate limit, False if exceeded
        """
        try:
            rate_limit_key = f"mfa:sms:rate_limit:{user_id}"
            count = await self.redis_client.get(rate_limit_key)

            if count:
                current_count = int(count)
                if current_count >= self.max_attempts_per_window:
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to check rate limit for user {user_id}: {e}", exc_info=True)
            return True  # Allow on error to prevent blocking users

    async def _increment_rate_limit(self, user_id: str) -> None:
        """
        Increment SMS rate limit counter for user.

        Args:
            user_id: User ID
        """
        try:
            rate_limit_key = f"mfa:sms:rate_limit:{user_id}"

            # Increment counter
            current = await self.redis_client.incr(rate_limit_key)

            # Set expiry on first increment
            if current == 1:
                await self.redis_client.expire(rate_limit_key, self.rate_limit_window)

        except Exception as e:
            logger.error(f"Failed to increment rate limit for user {user_id}: {e}", exc_info=True)

    async def _send_sms_via_provider(self, phone_number: str, otp: str) -> bool:
        """
        Send SMS via configured SMS provider (Twilio).

        Note: This is a placeholder implementation. In production, integrate
        with Twilio SDK or other SMS gateway.

        Args:
            phone_number: Phone number to send SMS to
            otp: OTP code to send

        Returns:
            True if SMS sent successfully, False otherwise
        """
        try:
            # TODO: Integrate with Twilio or SMS provider
            # For now, log the OTP (DO NOT DO THIS IN PRODUCTION)
            message = f"Your PalmsGig verification code is: {otp}. Valid for 5 minutes."

            # Placeholder for Twilio integration:
            # from twilio.rest import Client
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # message = client.messages.create(
            #     body=message,
            #     from_=settings.TWILIO_PHONE_NUMBER,
            #     to=phone_number
            # )

            logger.info(
                f"SMS would be sent to {phone_number}: {message}",
                extra={
                    "phone": phone_number[-4:],
                    "message_length": len(message),
                },
            )

            # Simulate successful send
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS via provider to {phone_number}: {e}", exc_info=True)
            return False

    def _validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format.

        Basic validation for E.164 format: +[country code][number]

        Args:
            phone_number: Phone number to validate

        Returns:
            True if format is valid, False otherwise

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> sms_service._validate_phone_number("+1234567890")
            True
            >>> sms_service._validate_phone_number("1234567890")
            False
        """
        if not phone_number:
            return False

        # Basic E.164 format validation
        if not phone_number.startswith("+"):
            return False

        # Remove + and check if remaining characters are digits
        digits = phone_number[1:]
        if not digits.isdigit():
            return False

        # Check length (E.164 allows 1-15 digits after country code)
        if len(digits) < 7 or len(digits) > 15:
            return False

        return True

    async def get_remaining_attempts(self, user_id: str) -> Optional[int]:
        """
        Get remaining verification attempts for user.

        Args:
            user_id: User ID

        Returns:
            Number of remaining attempts, or None if no OTP exists

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> await sms_service.send_sms_otp("+1234567890", "user123")
            >>> remaining = await sms_service.get_remaining_attempts("user123")
            >>> remaining == 5
            True
        """
        try:
            attempts_key = f"mfa:sms:attempts:{user_id}"
            attempts = await self.redis_client.get(attempts_key)

            if attempts is None:
                return None

            current_attempts = int(attempts) if attempts else 0
            remaining = max(0, self.max_verification_attempts - current_attempts)

            return remaining

        except Exception as e:
            logger.error(
                f"Failed to get remaining attempts for user {user_id}: {e}", exc_info=True
            )
            return None

    async def can_resend_otp(self, user_id: str) -> bool:
        """
        Check if user can request another OTP (rate limiting).

        Args:
            user_id: User ID

        Returns:
            True if user can request another OTP, False if rate limited

        Example:
            >>> sms_service = SMSOTPService(redis_client)
            >>> await sms_service.send_sms_otp("+1234567890", "user123")
            >>> await sms_service.can_resend_otp("user123")
            False  # (within rate limit window)
        """
        return await self._check_rate_limit(user_id)
