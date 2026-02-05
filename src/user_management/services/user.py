"""
User Service for CRUD operations and user management.

Handles user creation, retrieval, updates, and validation.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.user import User

logger = logging.getLogger(__name__)


class UserService:
    """Service for user CRUD operations and management."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the user service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.debug("UserService initialized")

    async def create_user(
        self,
        email: str,
        username: str,
        password_hash: str,
        phone_number: str,
        full_name: Optional[str] = None,
    ) -> User:
        """
        Create a new user account.

        Args:
            email: User email address
            username: Username
            password_hash: Hashed password
            phone_number: Phone number
            full_name: Full name (optional)

        Returns:
            Created User object

        Raises:
            ValueError: If email or username already exists
        """
        if await self.email_exists(email):
            logger.warning(f"Attempted to create user with existing email: {email}")
            raise ValueError(f"Email {email} is already registered")

        if await self.username_exists(username):
            logger.warning(f"Attempted to create user with existing username: {username}")
            raise ValueError(f"Username {username} is already taken")

        try:
            user = User(
                email=email,
                username=username,
                password_hash=password_hash,
                phone=phone_number,
                email_verified=False,
                phone_verified=False,
                is_active=True,
                profile_data={"full_name": full_name} if full_name else {},
            )

            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

            logger.info(f"Created new user: {user.id} ({email})")
            return user

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create user {email}: {e}", exc_info=True)
            raise ValueError(f"Failed to create user: {e}")

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve user by ID.

        Args:
            user_id: User ID

        Returns:
            User object if found, None otherwise
        """
        try:
            result = await self.session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user:
                logger.debug(f"Retrieved user by ID: {user_id}")
            else:
                logger.debug(f"User not found with ID: {user_id}")

            return user

        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {e}", exc_info=True)
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve user by email address.

        Args:
            email: Email address

        Returns:
            User object if found, None otherwise
        """
        try:
            result = await self.session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user:
                logger.debug(f"Retrieved user by email: {email}")
            else:
                logger.debug(f"User not found with email: {email}")

            return user

        except Exception as e:
            logger.error(f"Error retrieving user by email {email}: {e}", exc_info=True)
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve user by username.

        Args:
            username: Username

        Returns:
            User object if found, None otherwise
        """
        try:
            result = await self.session.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()

            if user:
                logger.debug(f"Retrieved user by username: {username}")
            else:
                logger.debug(f"User not found with username: {username}")

            return user

        except Exception as e:
            logger.error(f"Error retrieving user by username {username}: {e}", exc_info=True)
            return None

    async def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Retrieve user by phone number.

        Args:
            phone_number: Phone number

        Returns:
            User object if found, None otherwise
        """
        try:
            result = await self.session.execute(select(User).where(User.phone == phone_number))
            user = result.scalar_one_or_none()

            if user:
                logger.debug(f"Retrieved user by phone: {phone_number}")
            else:
                logger.debug(f"User not found with phone: {phone_number}")

            return user

        except Exception as e:
            logger.error(f"Error retrieving user by phone {phone_number}: {e}", exc_info=True)
            return None

    async def email_exists(self, email: str) -> bool:
        """
        Check if email is already registered.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        try:
            result = await self.session.execute(select(User.id).where(User.email == email))
            exists = result.scalar_one_or_none() is not None
            logger.debug(f"Email {email} exists: {exists}")
            return exists

        except Exception as e:
            logger.error(f"Error checking if email exists {email}: {e}", exc_info=True)
            return False

    async def username_exists(self, username: str) -> bool:
        """
        Check if username is already taken.

        Args:
            username: Username to check

        Returns:
            True if username exists, False otherwise
        """
        try:
            result = await self.session.execute(
                select(User.id).where(User.username == username)
            )
            exists = result.scalar_one_or_none() is not None
            logger.debug(f"Username {username} exists: {exists}")
            return exists

        except Exception as e:
            logger.error(f"Error checking if username exists {username}: {e}", exc_info=True)
            return False

    async def phone_exists(self, phone_number: str) -> bool:
        """
        Check if phone number is already registered.

        Args:
            phone_number: Phone number to check

        Returns:
            True if phone exists, False otherwise
        """
        try:
            result = await self.session.execute(select(User.id).where(User.phone == phone_number))
            exists = result.scalar_one_or_none() is not None
            logger.debug(f"Phone {phone_number} exists: {exists}")
            return exists

        except Exception as e:
            logger.error(f"Error checking if phone exists {phone_number}: {e}", exc_info=True)
            return False

    async def verify_email(self, user_id: str) -> bool:
        """
        Mark user's email as verified.

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Cannot verify email: user {user_id} not found")
                return False

            user.mark_email_verified()
            await self.session.commit()

            logger.info(f"Email verified for user: {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to verify email for user {user_id}: {e}", exc_info=True)
            return False

    async def verify_phone(self, user_id: str) -> bool:
        """
        Mark user's phone as verified.

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Cannot verify phone: user {user_id} not found")
                return False

            user.mark_phone_verified()
            await self.session.commit()

            logger.info(f"Phone verified for user: {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to verify phone for user {user_id}: {e}", exc_info=True)
            return False

    async def activate_user(self, user_id: str) -> bool:
        """
        Activate user account.

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Cannot activate: user {user_id} not found")
                return False

            user.activate()
            await self.session.commit()

            logger.info(f"User activated: {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to activate user {user_id}: {e}", exc_info=True)
            return False

    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user account (soft delete).

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Cannot deactivate: user {user_id} not found")
                return False

            user.deactivate()
            await self.session.commit()

            logger.info(f"User deactivated: {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to deactivate user {user_id}: {e}", exc_info=True)
            return False

    async def update_profile(
        self, user_id: str, full_name: Optional[str] = None, bio: Optional[str] = None
    ) -> bool:
        """
        Update user profile information.

        Args:
            user_id: User ID
            full_name: Updated full name
            bio: Updated bio

        Returns:
            True if successful, False otherwise
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Cannot update profile: user {user_id} not found")
                return False

            if full_name is not None:
                if user.profile_data is None:
                    user.profile_data = {}
                user.profile_data["full_name"] = full_name

            if bio is not None:
                user.bio = bio

            await self.session.commit()

            logger.info(f"Profile updated for user: {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update profile for user {user_id}: {e}", exc_info=True)
            return False
