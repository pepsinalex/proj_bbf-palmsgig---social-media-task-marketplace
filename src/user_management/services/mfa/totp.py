"""
TOTP (Time-based One-Time Password) service for MFA.

Implements TOTP secret generation, QR code creation, token verification,
backup codes generation, and time window validation using pyotp library.
"""

import base64
import io
import logging
import secrets
from typing import Optional

import pyotp
import qrcode
from cryptography.fernet import Fernet

from src.shared.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class TOTPService:
    """Service for TOTP-based multi-factor authentication operations."""

    def __init__(self) -> None:
        """
        Initialize TOTP service.

        Sets up encryption cipher for secure secret storage using the
        application's secret key.
        """
        # Create a Fernet cipher for encrypting TOTP secrets
        key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32, b"0"))
        self.cipher = Fernet(key)
        logger.debug("TOTPService initialized with encryption cipher")

    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret.

        Creates a cryptographically secure random base32-encoded secret
        suitable for use with TOTP authenticator apps.

        Returns:
            Base32-encoded TOTP secret string

        Example:
            >>> totp_service = TOTPService()
            >>> secret = totp_service.generate_secret()
            >>> len(secret) == 32
            True
        """
        try:
            secret = pyotp.random_base32()
            logger.info("Generated new TOTP secret")
            return secret
        except Exception as e:
            logger.error(f"Failed to generate TOTP secret: {e}", exc_info=True)
            raise ValueError(f"Failed to generate TOTP secret: {e}")

    def encrypt_secret(self, secret: str) -> str:
        """
        Encrypt a TOTP secret for secure storage.

        Args:
            secret: Plain text TOTP secret to encrypt

        Returns:
            Base64-encoded encrypted secret

        Raises:
            ValueError: If encryption fails

        Example:
            >>> totp_service = TOTPService()
            >>> encrypted = totp_service.encrypt_secret("JBSWY3DPEHPK3PXP")
            >>> isinstance(encrypted, str)
            True
        """
        try:
            encrypted = self.cipher.encrypt(secret.encode())
            encrypted_str = base64.b64encode(encrypted).decode()
            logger.debug("TOTP secret encrypted successfully")
            return encrypted_str
        except Exception as e:
            logger.error(f"Failed to encrypt TOTP secret: {e}", exc_info=True)
            raise ValueError(f"Failed to encrypt TOTP secret: {e}")

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """
        Decrypt a stored TOTP secret.

        Args:
            encrypted_secret: Base64-encoded encrypted secret

        Returns:
            Decrypted plain text secret

        Raises:
            ValueError: If decryption fails

        Example:
            >>> totp_service = TOTPService()
            >>> secret = "JBSWY3DPEHPK3PXP"
            >>> encrypted = totp_service.encrypt_secret(secret)
            >>> decrypted = totp_service.decrypt_secret(encrypted)
            >>> decrypted == secret
            True
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_secret.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            secret = decrypted.decode()
            logger.debug("TOTP secret decrypted successfully")
            return secret
        except Exception as e:
            logger.error(f"Failed to decrypt TOTP secret: {e}", exc_info=True)
            raise ValueError(f"Failed to decrypt TOTP secret: {e}")

    def generate_qr_code(
        self, secret: str, user_email: str, issuer: str = "PalmsGig"
    ) -> str:
        """
        Generate QR code for TOTP setup.

        Creates a QR code image containing the TOTP provisioning URI
        that can be scanned by authenticator apps.

        Args:
            secret: TOTP secret key
            user_email: User's email address for identification
            issuer: Application name (default: "PalmsGig")

        Returns:
            Base64-encoded PNG image data URL

        Raises:
            ValueError: If QR code generation fails

        Example:
            >>> totp_service = TOTPService()
            >>> secret = totp_service.generate_secret()
            >>> qr_code = totp_service.generate_qr_code(secret, "user@example.com")
            >>> qr_code.startswith("data:image/png;base64,")
            True
        """
        try:
            # Create TOTP URI for authenticator apps
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(name=user_email, issuer_name=issuer)

            # Generate QR code image
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert image to base64 data URL
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            data_url = f"data:image/png;base64,{img_base64}"

            logger.info(f"Generated QR code for user: {user_email}")
            return data_url

        except Exception as e:
            logger.error(f"Failed to generate QR code for {user_email}: {e}", exc_info=True)
            raise ValueError(f"Failed to generate QR code: {e}")

    def verify_token(
        self, secret: str, token: str, valid_window: int = 1
    ) -> bool:
        """
        Verify a TOTP token.

        Validates the provided token against the secret, allowing for
        clock drift within the specified time window.

        Args:
            secret: TOTP secret key
            token: 6-digit TOTP token to verify
            valid_window: Number of time windows to check before/after (default: 1)

        Returns:
            True if token is valid, False otherwise

        Raises:
            ValueError: If verification fails due to invalid input

        Example:
            >>> totp_service = TOTPService()
            >>> secret = totp_service.generate_secret()
            >>> totp = pyotp.TOTP(secret)
            >>> token = totp.now()
            >>> totp_service.verify_token(secret, token)
            True
        """
        try:
            if not token or not token.isdigit() or len(token) != 6:
                logger.warning(f"Invalid token format: {token}")
                return False

            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(token, valid_window=valid_window)

            if is_valid:
                logger.info("TOTP token verified successfully")
            else:
                logger.warning("TOTP token verification failed")

            return is_valid

        except Exception as e:
            logger.error(f"Failed to verify TOTP token: {e}", exc_info=True)
            raise ValueError(f"Failed to verify TOTP token: {e}")

    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """
        Generate backup recovery codes.

        Creates cryptographically secure backup codes that can be used
        for account recovery when the primary MFA method is unavailable.

        Args:
            count: Number of backup codes to generate (default: 10)

        Returns:
            List of backup codes in format XXXX-XXXX-XXXX

        Raises:
            ValueError: If count is invalid or generation fails

        Example:
            >>> totp_service = TOTPService()
            >>> codes = totp_service.generate_backup_codes(count=5)
            >>> len(codes)
            5
            >>> all(len(code.replace('-', '')) == 12 for code in codes)
            True
        """
        try:
            if count <= 0 or count > 50:
                raise ValueError("Backup code count must be between 1 and 50")

            codes = []
            for _ in range(count):
                # Generate 12 alphanumeric characters
                code = secrets.token_hex(6).upper()
                # Format as XXXX-XXXX-XXXX
                formatted_code = f"{code[0:4]}-{code[4:8]}-{code[8:12]}"
                codes.append(formatted_code)

            logger.info(f"Generated {count} backup codes")
            return codes

        except Exception as e:
            logger.error(f"Failed to generate backup codes: {e}", exc_info=True)
            raise ValueError(f"Failed to generate backup codes: {e}")

    def encrypt_backup_codes(self, codes: list[str]) -> str:
        """
        Encrypt backup codes for secure storage.

        Args:
            codes: List of backup codes to encrypt

        Returns:
            Base64-encoded encrypted backup codes as JSON string

        Raises:
            ValueError: If encryption fails

        Example:
            >>> totp_service = TOTPService()
            >>> codes = ["0123-4567-89AB", "CDEF-0123-4567"]
            >>> encrypted = totp_service.encrypt_backup_codes(codes)
            >>> isinstance(encrypted, str)
            True
        """
        try:
            import json

            codes_json = json.dumps(codes)
            encrypted = self.cipher.encrypt(codes_json.encode())
            encrypted_str = base64.b64encode(encrypted).decode()
            logger.debug(f"Encrypted {len(codes)} backup codes")
            return encrypted_str
        except Exception as e:
            logger.error(f"Failed to encrypt backup codes: {e}", exc_info=True)
            raise ValueError(f"Failed to encrypt backup codes: {e}")

    def decrypt_backup_codes(self, encrypted_codes: str) -> list[str]:
        """
        Decrypt stored backup codes.

        Args:
            encrypted_codes: Base64-encoded encrypted backup codes

        Returns:
            List of decrypted backup codes

        Raises:
            ValueError: If decryption fails

        Example:
            >>> totp_service = TOTPService()
            >>> codes = ["0123-4567-89AB", "CDEF-0123-4567"]
            >>> encrypted = totp_service.encrypt_backup_codes(codes)
            >>> decrypted = totp_service.decrypt_backup_codes(encrypted)
            >>> decrypted == codes
            True
        """
        try:
            import json

            encrypted_bytes = base64.b64decode(encrypted_codes.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            codes = json.loads(decrypted.decode())
            logger.debug(f"Decrypted {len(codes)} backup codes")
            return codes
        except Exception as e:
            logger.error(f"Failed to decrypt backup codes: {e}", exc_info=True)
            raise ValueError(f"Failed to decrypt backup codes: {e}")

    def verify_backup_code(
        self, encrypted_codes: str, code: str
    ) -> tuple[bool, Optional[str]]:
        """
        Verify a backup code and remove it from the list if valid.

        Args:
            encrypted_codes: Encrypted backup codes string
            code: Backup code to verify

        Returns:
            Tuple of (is_valid, updated_encrypted_codes)
            - is_valid: True if code was valid and removed
            - updated_encrypted_codes: New encrypted codes without the used code,
              or None if invalid

        Example:
            >>> totp_service = TOTPService()
            >>> codes = totp_service.generate_backup_codes(count=3)
            >>> encrypted = totp_service.encrypt_backup_codes(codes)
            >>> is_valid, new_encrypted = totp_service.verify_backup_code(encrypted, codes[0])
            >>> is_valid
            True
            >>> new_codes = totp_service.decrypt_backup_codes(new_encrypted)
            >>> len(new_codes)
            2
        """
        try:
            # Decrypt existing codes
            codes = self.decrypt_backup_codes(encrypted_codes)

            # Check if code exists (case-insensitive)
            code_upper = code.upper().strip()
            if code_upper in codes:
                # Remove the used code
                codes.remove(code_upper)

                # Re-encrypt the remaining codes
                new_encrypted = self.encrypt_backup_codes(codes)

                logger.info("Backup code verified and removed successfully")
                return True, new_encrypted
            else:
                logger.warning(f"Invalid backup code attempted")
                return False, None

        except Exception as e:
            logger.error(f"Failed to verify backup code: {e}", exc_info=True)
            return False, None

    def get_current_token(self, secret: str) -> str:
        """
        Get the current TOTP token for a secret.

        Useful for testing and validation purposes.

        Args:
            secret: TOTP secret key

        Returns:
            Current 6-digit TOTP token

        Raises:
            ValueError: If token generation fails

        Example:
            >>> totp_service = TOTPService()
            >>> secret = totp_service.generate_secret()
            >>> token = totp_service.get_current_token(secret)
            >>> len(token)
            6
            >>> token.isdigit()
            True
        """
        try:
            totp = pyotp.TOTP(secret)
            token = totp.now()
            logger.debug("Generated current TOTP token")
            return token
        except Exception as e:
            logger.error(f"Failed to get current token: {e}", exc_info=True)
            raise ValueError(f"Failed to get current token: {e}")

    def get_time_remaining(self) -> int:
        """
        Get seconds remaining in current TOTP time window.

        Returns:
            Number of seconds until the current token expires

        Example:
            >>> totp_service = TOTPService()
            >>> remaining = totp_service.get_time_remaining()
            >>> 0 <= remaining <= 30
            True
        """
        try:
            import time

            totp = pyotp.TOTP(pyotp.random_base32())
            time_remaining = totp.interval - (time.time() % totp.interval)
            return int(time_remaining)
        except Exception as e:
            logger.error(f"Failed to get time remaining: {e}", exc_info=True)
            return 30  # Default TOTP interval
