"""
Password Service for secure password hashing and verification.

Provides bcrypt-based password hashing with configurable rounds.
"""

import logging
import re
from typing import Optional

from passlib.context import CryptContext

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordService:
    """Service for password hashing, verification, and validation."""

    def __init__(self, bcrypt_rounds: int = 12):
        """
        Initialize the password service.

        Args:
            bcrypt_rounds: Number of bcrypt rounds for hashing (default: 12)
        """
        self.bcrypt_rounds = bcrypt_rounds
        logger.info(f"PasswordService initialized with {bcrypt_rounds} bcrypt rounds")

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string

        Raises:
            ValueError: If password is empty or invalid
        """
        if not password:
            logger.error("Attempted to hash empty password")
            raise ValueError("Password cannot be empty")

        try:
            hashed = pwd_context.hash(password, rounds=self.bcrypt_rounds)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Password hashing failed: {e}", exc_info=True)
            raise ValueError(f"Failed to hash password: {e}")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        try:
            is_valid = pwd_context.verify(plain_password, hashed_password)
            logger.debug(f"Password verification result: {is_valid}")
            return is_valid
        except Exception as e:
            logger.error(f"Password verification error: {e}", exc_info=True)
            return False

    def validate_password_strength(self, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength according to security requirements.

        Password must contain:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if password meets all requirements
            - error_message: None if valid, error description if invalid
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        logger.debug("Password strength validation passed")
        return True, None

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if a hashed password needs to be rehashed.

        This is useful when bcrypt rounds change or the algorithm is updated.

        Args:
            hashed_password: Hashed password to check

        Returns:
            True if password should be rehashed, False otherwise
        """
        try:
            needs_rehash = pwd_context.needs_update(hashed_password)
            if needs_rehash:
                logger.info("Password hash needs update")
            return needs_rehash
        except Exception as e:
            logger.error(f"Error checking if hash needs update: {e}")
            return False
