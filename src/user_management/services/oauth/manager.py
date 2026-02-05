"""
OAuth Manager for coordinating multiple OAuth providers.

This module provides the OAuthManager class that coordinates OAuth authentication
across multiple providers (Google, Facebook, Twitter) and handles account linking.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.shared.models.auth import AuthenticationMethod, OAuthToken
from src.shared.models.user import User
from src.user_management.services.oauth.base import BaseOAuthProvider, OAuthUserInfo
from src.user_management.services.oauth.facebook import FacebookOAuthProvider
from src.user_management.services.oauth.google import GoogleOAuthProvider
from src.user_management.services.oauth.twitter import TwitterOAuthProvider

logger = logging.getLogger(__name__)


class OAuthManager:
    """
    OAuth Manager for coordinating multiple OAuth providers.

    Manages OAuth authentication flows across multiple social media providers,
    handles user account linking, and coordinates token storage and refresh.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        google_client_id: Optional[str] = None,
        google_client_secret: Optional[str] = None,
        facebook_client_id: Optional[str] = None,
        facebook_client_secret: Optional[str] = None,
        twitter_client_id: Optional[str] = None,
        twitter_client_secret: Optional[str] = None,
        redirect_uri: str = "http://localhost:8000/api/v1/oauth/callback",
    ) -> None:
        """
        Initialize OAuth Manager.

        Args:
            db_session: SQLAlchemy async session
            google_client_id: Google OAuth client ID
            google_client_secret: Google OAuth client secret
            facebook_client_id: Facebook OAuth client ID
            facebook_client_secret: Facebook OAuth client secret
            twitter_client_id: Twitter OAuth client ID
            twitter_client_secret: Twitter OAuth client secret
            redirect_uri: OAuth callback redirect URI
        """
        self.db_session = db_session
        self.redirect_uri = redirect_uri
        self._providers: dict[str, BaseOAuthProvider] = {}

        if google_client_id and google_client_secret:
            self._providers["google"] = GoogleOAuthProvider(
                client_id=google_client_id,
                client_secret=google_client_secret,
                redirect_uri=redirect_uri,
            )
            logger.info("Initialized Google OAuth provider")

        if facebook_client_id and facebook_client_secret:
            self._providers["facebook"] = FacebookOAuthProvider(
                client_id=facebook_client_id,
                client_secret=facebook_client_secret,
                redirect_uri=redirect_uri,
            )
            logger.info("Initialized Facebook OAuth provider")

        if twitter_client_id and twitter_client_secret:
            self._providers["twitter"] = TwitterOAuthProvider(
                client_id=twitter_client_id,
                client_secret=twitter_client_secret,
                redirect_uri=redirect_uri,
            )
            logger.info("Initialized Twitter OAuth provider")

        logger.info(
            f"OAuth Manager initialized with {len(self._providers)} providers",
            extra={"providers": list(self._providers.keys())},
        )

    def get_provider(self, provider_name: str) -> BaseOAuthProvider:
        """
        Get OAuth provider by name.

        Args:
            provider_name: Provider name (google, facebook, twitter)

        Returns:
            OAuth provider instance

        Raises:
            ValueError: If provider is not configured
        """
        provider = self._providers.get(provider_name.lower())
        if not provider:
            logger.error(
                f"OAuth provider not configured: {provider_name}",
                extra={"available_providers": list(self._providers.keys())},
            )
            raise ValueError(
                f"OAuth provider '{provider_name}' is not configured. "
                f"Available providers: {', '.join(self._providers.keys())}"
            )
        return provider

    def get_available_providers(self) -> list[str]:
        """
        Get list of available OAuth providers.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def is_provider_available(self, provider_name: str) -> bool:
        """
        Check if OAuth provider is available.

        Args:
            provider_name: Provider name to check

        Returns:
            True if provider is configured, False otherwise
        """
        return provider_name.lower() in self._providers

    async def get_authorization_url(
        self, provider_name: str, state: Optional[str] = None, scopes: Optional[list[str]] = None
    ) -> str:
        """
        Get OAuth authorization URL for provider.

        Args:
            provider_name: Provider name (google, facebook, twitter)
            state: Optional state parameter for CSRF protection
            scopes: Optional list of OAuth scopes to request

        Returns:
            Authorization URL for OAuth flow

        Raises:
            ValueError: If provider is not configured
        """
        provider = self.get_provider(provider_name)
        auth_url = await provider.get_authorization_url(state=state, scopes=scopes)

        logger.info(
            f"Generated authorization URL for {provider_name}",
            extra={"provider": provider_name, "has_state": state is not None},
        )

        return auth_url

    async def handle_callback(
        self, provider_name: str, code: str, state: Optional[str] = None
    ) -> tuple[OAuthUserInfo, str, Optional[str], Optional[datetime]]:
        """
        Handle OAuth callback and exchange code for tokens.

        Args:
            provider_name: Provider name
            code: Authorization code from callback
            state: Optional state parameter for verification

        Returns:
            Tuple of (user_info, access_token, refresh_token, expires_at)

        Raises:
            ValueError: If provider is not configured
            Exception: If token exchange or user info retrieval fails
        """
        provider = self.get_provider(provider_name)

        try:
            token_response = await provider.exchange_code_for_token(code)

            expires_at = None
            if token_response.expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=token_response.expires_in)

            user_info = await provider.get_user_info(token_response.access_token)

            logger.info(
                f"Successfully handled OAuth callback for {provider_name}",
                extra={
                    "provider": provider_name,
                    "provider_user_id": user_info.provider_user_id,
                    "has_refresh_token": token_response.refresh_token is not None,
                },
            )

            return (
                user_info,
                token_response.access_token,
                token_response.refresh_token,
                expires_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to handle OAuth callback for {provider_name}",
                extra={"provider": provider_name, "error": str(e)},
                exc_info=True,
            )
            raise

    async def find_or_create_user(
        self, provider_name: str, user_info: OAuthUserInfo
    ) -> tuple[User, bool]:
        """
        Find existing user or create new user from OAuth data.

        Args:
            provider_name: OAuth provider name
            user_info: OAuth user information

        Returns:
            Tuple of (user, is_new_user)
        """
        auth_method = await self.get_authentication_method(provider_name, user_info.provider_user_id)

        if auth_method:
            await self.db_session.refresh(auth_method, ["user"])
            logger.info(
                f"Found existing user via {provider_name} authentication",
                extra={
                    "provider": provider_name,
                    "user_id": auth_method.user_id,
                    "provider_user_id": user_info.provider_user_id,
                },
            )
            return auth_method.user, False

        if user_info.email:
            stmt = select(User).where(User.email == user_info.email)
            result = await self.db_session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.info(
                    f"Found existing user by email, linking {provider_name} account",
                    extra={
                        "provider": provider_name,
                        "user_id": existing_user.id,
                        "email": user_info.email,
                    },
                )
                return existing_user, False

        new_user = User(
            email=user_info.email,
            username=self._generate_username_from_oauth(user_info),
            full_name=user_info.name,
            is_email_verified=bool(user_info.email),
            is_active=True,
        )
        self.db_session.add(new_user)
        await self.db_session.flush()

        logger.info(
            f"Created new user from {provider_name} OAuth",
            extra={
                "provider": provider_name,
                "user_id": new_user.id,
                "email": user_info.email,
                "username": new_user.username,
            },
        )

        return new_user, True

    async def link_oauth_account(
        self,
        user: User,
        provider_name: str,
        provider_user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        scope: Optional[str] = None,
        provider_data: Optional[dict] = None,
    ) -> AuthenticationMethod:
        """
        Link OAuth account to existing user.

        Args:
            user: User to link account to
            provider_name: OAuth provider name
            provider_user_id: User ID from OAuth provider
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_at: Token expiration timestamp (optional)
            scope: OAuth scopes granted (optional)
            provider_data: Additional provider data (optional)

        Returns:
            Created or updated authentication method
        """
        auth_method = await self.get_authentication_method(provider_name, provider_user_id)

        if auth_method:
            if auth_method.user_id != str(user.id):
                logger.warning(
                    f"OAuth account already linked to different user",
                    extra={
                        "provider": provider_name,
                        "provider_user_id": provider_user_id,
                        "current_user_id": auth_method.user_id,
                        "new_user_id": str(user.id),
                    },
                )
                raise ValueError(
                    f"This {provider_name} account is already linked to another user"
                )

            auth_method.update_tokens(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )
            if scope:
                auth_method.scope = scope
            if provider_data:
                auth_method.provider_data = provider_data

            logger.info(
                f"Updated existing {provider_name} authentication method",
                extra={
                    "provider": provider_name,
                    "user_id": str(user.id),
                    "auth_method_id": auth_method.id,
                },
            )
        else:
            auth_method = AuthenticationMethod(
                user_id=str(user.id),
                provider=provider_name,
                provider_user_id=provider_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                scope=scope,
                provider_data=provider_data,
                is_active=True,
                last_used_at=datetime.utcnow(),
            )
            self.db_session.add(auth_method)

            logger.info(
                f"Created new {provider_name} authentication method",
                extra={
                    "provider": provider_name,
                    "user_id": str(user.id),
                    "provider_user_id": provider_user_id,
                },
            )

        await self.db_session.flush()
        return auth_method

    async def get_authentication_method(
        self, provider_name: str, provider_user_id: str
    ) -> Optional[AuthenticationMethod]:
        """
        Get authentication method by provider and provider user ID.

        Args:
            provider_name: OAuth provider name
            provider_user_id: User ID from OAuth provider

        Returns:
            Authentication method if found, None otherwise
        """
        stmt = (
            select(AuthenticationMethod)
            .where(
                AuthenticationMethod.provider == provider_name,
                AuthenticationMethod.provider_user_id == provider_user_id,
            )
            .options(selectinload(AuthenticationMethod.user))
        )

        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_oauth_accounts(self, user_id: str) -> list[AuthenticationMethod]:
        """
        Get all OAuth accounts linked to user.

        Args:
            user_id: User ID

        Returns:
            List of authentication methods
        """
        stmt = (
            select(AuthenticationMethod)
            .where(AuthenticationMethod.user_id == user_id, AuthenticationMethod.is_active == True)
            .order_by(AuthenticationMethod.created_at)
        )

        result = await self.db_session.execute(stmt)
        methods = list(result.scalars().all())

        logger.debug(
            f"Retrieved OAuth accounts for user",
            extra={"user_id": user_id, "account_count": len(methods)},
        )

        return methods

    async def unlink_oauth_account(self, user_id: str, provider_name: str) -> bool:
        """
        Unlink OAuth account from user.

        Args:
            user_id: User ID
            provider_name: OAuth provider name

        Returns:
            True if account was unlinked, False if not found
        """
        stmt = select(AuthenticationMethod).where(
            AuthenticationMethod.user_id == user_id,
            AuthenticationMethod.provider == provider_name,
            AuthenticationMethod.is_active == True,
        )

        result = await self.db_session.execute(stmt)
        auth_method = result.scalar_one_or_none()

        if not auth_method:
            logger.warning(
                f"OAuth account not found for unlinking",
                extra={"user_id": user_id, "provider": provider_name},
            )
            return False

        auth_method.deactivate()
        await self.db_session.flush()

        logger.info(
            f"Unlinked {provider_name} OAuth account",
            extra={"user_id": user_id, "provider": provider_name, "auth_method_id": auth_method.id},
        )

        return True

    async def refresh_access_token(
        self, provider_name: str, refresh_token: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        """
        Refresh OAuth access token.

        Args:
            provider_name: OAuth provider name
            refresh_token: OAuth refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token, expires_at)

        Raises:
            ValueError: If provider is not configured
            Exception: If token refresh fails
        """
        provider = self.get_provider(provider_name)

        try:
            token_response = await provider.refresh_access_token(refresh_token)

            expires_at = None
            if token_response.expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=token_response.expires_in)

            logger.info(
                f"Successfully refreshed access token for {provider_name}",
                extra={"provider": provider_name},
            )

            return (
                token_response.access_token,
                token_response.refresh_token,
                expires_at,
            )

        except Exception as e:
            logger.error(
                f"Failed to refresh access token for {provider_name}",
                extra={"provider": provider_name, "error": str(e)},
                exc_info=True,
            )
            raise

    async def store_oauth_token(
        self,
        user_id: str,
        provider_name: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        scope: Optional[str] = None,
    ) -> OAuthToken:
        """
        Store OAuth token in database.

        Args:
            user_id: User ID
            provider_name: OAuth provider name
            access_token: OAuth access token (will be encrypted)
            refresh_token: OAuth refresh token (will be encrypted, optional)
            expires_at: Token expiration timestamp (optional)
            scope: OAuth scopes granted (optional)

        Returns:
            Created or updated OAuth token
        """
        stmt = select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider_name,
        )

        result = await self.db_session.execute(stmt)
        oauth_token = result.scalar_one_or_none()

        if oauth_token:
            oauth_token.update_tokens(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scope=scope,
            )

            logger.info(
                f"Updated OAuth token for {provider_name}",
                extra={"user_id": user_id, "provider": provider_name, "token_id": oauth_token.id},
            )
        else:
            oauth_token = OAuthToken(
                user_id=user_id,
                provider=provider_name,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scope=scope,
            )
            self.db_session.add(oauth_token)

            logger.info(
                f"Created new OAuth token for {provider_name}",
                extra={"user_id": user_id, "provider": provider_name},
            )

        await self.db_session.flush()
        return oauth_token

    async def get_oauth_token(self, user_id: str, provider_name: str) -> Optional[OAuthToken]:
        """
        Get stored OAuth token for user and provider.

        Args:
            user_id: User ID
            provider_name: OAuth provider name

        Returns:
            OAuth token if found, None otherwise
        """
        stmt = select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider_name,
        )

        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    def _generate_username_from_oauth(self, user_info: OAuthUserInfo) -> str:
        """
        Generate username from OAuth user info.

        Args:
            user_info: OAuth user information

        Returns:
            Generated username
        """
        if user_info.email:
            base_username = user_info.email.split("@")[0]
        elif user_info.name:
            base_username = user_info.name.lower().replace(" ", "_")
        else:
            base_username = f"user_{user_info.provider_user_id[:8]}"

        base_username = "".join(c for c in base_username if c.isalnum() or c == "_")
        base_username = base_username[:20]

        return base_username
