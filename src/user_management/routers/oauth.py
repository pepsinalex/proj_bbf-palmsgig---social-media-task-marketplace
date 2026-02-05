"""
OAuth 2.0 Router for social media authentication.

Provides endpoints for OAuth authentication with Google, Facebook, and Twitter,
including authorization, callback handling, account linking, and account management.
"""

import logging
import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import (
    get_app_settings,
    get_database_session,
    require_authentication,
)
from src.shared.config import Settings
from src.shared.models.auth import AuthenticationMethod, OAuthToken
from src.shared.models.user import User
from src.user_management.schemas.oauth import (
    AccountLinkRequest,
    AccountLinkResponse,
    AccountUnlinkRequest,
    AccountUnlinkResponse,
    OAuthAuthorizationRequest,
    OAuthAuthorizationResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    OAuthProviderInfo,
    OAuthProvidersListResponse,
    SocialAccountInfo,
    SocialAccountResponse,
)
from src.user_management.services.oauth.manager import OAuthManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])


async def get_oauth_manager(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> OAuthManager:
    """
    Dependency for OAuth manager.

    Initializes OAuthManager with provider credentials from environment variables.
    """
    return OAuthManager(
        db_session=session,
        google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        facebook_client_id=os.getenv("FACEBOOK_CLIENT_ID"),
        facebook_client_secret=os.getenv("FACEBOOK_CLIENT_SECRET"),
        twitter_client_id=os.getenv("TWITTER_CLIENT_ID"),
        twitter_client_secret=os.getenv("TWITTER_CLIENT_SECRET"),
        redirect_uri=os.getenv(
            "OAUTH_REDIRECT_URI", "http://localhost:8000/api/v1/oauth/callback"
        ),
    )


@router.get(
    "/providers",
    response_model=OAuthProvidersListResponse,
    summary="List available OAuth providers",
    description="Get list of configured and available OAuth providers",
)
async def list_oauth_providers(
    oauth_manager: Annotated[OAuthManager, Depends(get_oauth_manager)]
) -> OAuthProvidersListResponse:
    """
    List available OAuth providers.

    Returns information about which OAuth providers are configured and available
    for authentication.

    Args:
        oauth_manager: OAuth manager dependency

    Returns:
        List of OAuth provider information
    """
    try:
        providers_info = []
        
        provider_display_names = {
            "google": "Google",
            "facebook": "Facebook",
            "twitter": "Twitter (X)",
        }

        for provider_name in ["google", "facebook", "twitter"]:
            try:
                provider = oauth_manager.get_provider(provider_name)
                is_configured = True
            except ValueError:
                is_configured = False

            providers_info.append(
                OAuthProviderInfo(
                    provider=provider_name,
                    display_name=provider_display_names.get(provider_name, provider_name.title()),
                    is_configured=is_configured,
                    is_available=is_configured,
                    authorization_url_template=None,
                )
            )

        logger.info(
            f"Listed {len(providers_info)} OAuth providers",
            extra={"configured_count": sum(1 for p in providers_info if p.is_configured)},
        )

        return OAuthProvidersListResponse(
            providers=providers_info,
            total=len(providers_info),
        )

    except Exception as e:
        logger.error(
            "Failed to list OAuth providers",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OAuth providers information",
        )


@router.get(
    "/authorize/{provider}",
    response_model=OAuthAuthorizationResponse,
    summary="Get OAuth authorization URL",
    description="Generate OAuth authorization URL for specified provider",
)
async def get_authorization_url(
    provider: str,
    oauth_manager: Annotated[OAuthManager, Depends(get_oauth_manager)],
    redirect_uri: Optional[str] = Query(None, description="Custom redirect URI"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
) -> OAuthAuthorizationResponse:
    """
    Generate OAuth authorization URL.

    Creates an authorization URL that users should be redirected to for
    OAuth authentication with the specified provider.

    Args:
        provider: OAuth provider name (google, facebook, twitter)
        oauth_manager: OAuth manager dependency
        redirect_uri: Custom redirect URI (optional)
        state: State parameter for CSRF protection (optional)

    Returns:
        Authorization URL and state parameter

    Raises:
        HTTPException 400: If provider is not supported or configured
        HTTPException 500: If authorization URL generation fails
    """
    try:
        logger.info(f"Generating authorization URL for provider: {provider}")

        oauth_provider = oauth_manager.get_provider(provider)
        
        auth_url = oauth_provider.get_authorization_url(state=state)

        logger.info(
            f"Authorization URL generated for {provider}",
            extra={"provider": provider, "has_state": state is not None},
        )

        return OAuthAuthorizationResponse(
            authorization_url=auth_url,
            state=state,
            provider=provider,
        )

    except ValueError as e:
        logger.warning(
            f"Invalid or unconfigured provider: {provider}",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' is not supported or configured",
        )
    except Exception as e:
        logger.error(
            f"Failed to generate authorization URL for {provider}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL",
        )


@router.get(
    "/callback/{provider}",
    response_model=OAuthCallbackResponse,
    summary="OAuth callback endpoint",
    description="Handle OAuth callback after user authorization",
)
async def oauth_callback(
    provider: str,
    oauth_manager: Annotated[OAuthManager, Depends(get_oauth_manager)],
    code: str = Query(..., description="Authorization code from provider"),
    state: Optional[str] = Query(None, description="State parameter for CSRF verification"),
) -> OAuthCallbackResponse:
    """
    Handle OAuth callback.

    Processes the OAuth callback after user authorization, exchanges code for tokens,
    retrieves user information, and either creates a new account or logs in existing user.

    Args:
        provider: OAuth provider name
        code: Authorization code from provider
        state: State parameter for CSRF verification
        oauth_manager: OAuth manager dependency

    Returns:
        OAuth callback response with user data and JWT tokens

    Raises:
        HTTPException 400: If provider is invalid or callback data is invalid
        HTTPException 500: If callback processing fails
    """
    try:
        logger.info(
            f"Processing OAuth callback for {provider}",
            extra={"provider": provider, "has_state": state is not None},
        )

        # Authenticate or create user via OAuth
        user, is_new_user, auth_method = await oauth_manager.authenticate_or_create_user(
            provider=provider,
            authorization_code=code,
        )

        # In a production system, you would generate JWT tokens here
        # For now, we'll return user info and indicate success
        logger.info(
            f"OAuth authentication successful for {provider}",
            extra={
                "provider": provider,
                "user_id": str(user.id),
                "is_new_user": is_new_user,
            },
        )

        return OAuthCallbackResponse(
            success=True,
            message="OAuth authentication successful",
            user_id=str(user.id),
            is_new_user=is_new_user,
            access_token=None,  # TODO: Generate JWT access token
            refresh_token=None,  # TODO: Generate JWT refresh token
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user={
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.profile_data.get("full_name") if user.profile_data else None,
                "email_verified": user.email_verified,
                "phone_verified": user.phone_verified,
            },
            social_account=SocialAccountInfo(
                provider=auth_method.provider,
                provider_user_id=auth_method.provider_user_id,
                email=user.email,
                name=user.profile_data.get("full_name") if user.profile_data else None,
                avatar_url=user.profile_data.get("avatar_url") if user.profile_data else None,
                profile_url=user.profile_data.get("profile_url") if user.profile_data else None,
                is_active=auth_method.is_active,
                last_used_at=auth_method.last_used_at,
                linked_at=auth_method.created_at,
            ),
        )

    except ValueError as e:
        logger.warning(
            f"Invalid OAuth callback for {provider}",
            extra={"error": str(e), "provider": provider},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"OAuth callback failed for {provider}",
            extra={"error": str(e), "error_type": type(e).__name__, "provider": provider},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed",
        )


@router.post(
    "/link",
    response_model=AccountLinkResponse,
    summary="Link social account to authenticated user",
    description="Link an additional OAuth provider account to the current user",
)
async def link_social_account(
    link_request: AccountLinkRequest,
    current_user: Annotated[dict, Depends(require_authentication)],
    oauth_manager: Annotated[OAuthManager, Depends(get_oauth_manager)],
) -> AccountLinkResponse:
    """
    Link social account to authenticated user.

    Allows an authenticated user to link an additional OAuth provider account
    to their existing account for multi-provider authentication.

    Args:
        link_request: Account link request with provider and authorization code
        current_user: Current authenticated user from JWT
        oauth_manager: OAuth manager dependency

    Returns:
        Account link response with linked account info

    Raises:
        HTTPException 400: If provider is invalid or account is already linked
        HTTPException 401: If user is not authenticated
        HTTPException 500: If account linking fails
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in authentication token",
            )

        logger.info(
            f"Linking {link_request.provider} account for user {user_id}",
            extra={"provider": link_request.provider, "user_id": user_id},
        )

        # Link the OAuth account to existing user
        auth_method = await oauth_manager.link_oauth_account(
            user_id=user_id,
            provider=link_request.provider,
            authorization_code=link_request.code,
        )

        logger.info(
            f"Successfully linked {link_request.provider} account",
            extra={
                "provider": link_request.provider,
                "user_id": user_id,
                "provider_user_id": auth_method.provider_user_id,
            },
        )

        return AccountLinkResponse(
            success=True,
            message=f"Successfully linked {link_request.provider} account",
            social_account=SocialAccountInfo(
                provider=auth_method.provider,
                provider_user_id=auth_method.provider_user_id,
                email=auth_method.provider_data.get("email") if auth_method.provider_data else None,
                name=auth_method.provider_data.get("name") if auth_method.provider_data else None,
                avatar_url=auth_method.provider_data.get("avatar_url")
                if auth_method.provider_data
                else None,
                profile_url=auth_method.provider_data.get("profile_url")
                if auth_method.provider_data
                else None,
                is_active=auth_method.is_active,
                last_used_at=auth_method.last_used_at,
                linked_at=auth_method.created_at,
            ),
        )

    except ValueError as e:
        logger.warning(
            f"Failed to link {link_request.provider} account",
            extra={"error": str(e), "provider": link_request.provider},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Account linking failed for {link_request.provider}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link social account",
        )


@router.delete(
    "/unlink/{provider}",
    response_model=AccountUnlinkResponse,
    summary="Unlink social account",
    description="Remove OAuth provider account link from current user",
)
async def unlink_social_account(
    provider: str,
    current_user: Annotated[dict, Depends(require_authentication)],
    oauth_manager: Annotated[OAuthManager, Depends(get_oauth_manager)],
) -> AccountUnlinkResponse:
    """
    Unlink social account from authenticated user.

    Removes the link between the user's account and the specified OAuth provider.

    Args:
        provider: OAuth provider name to unlink
        current_user: Current authenticated user from JWT
        oauth_manager: OAuth manager dependency

    Returns:
        Account unlink response

    Raises:
        HTTPException 400: If provider is invalid or not linked
        HTTPException 401: If user is not authenticated
        HTTPException 500: If account unlinking fails
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in authentication token",
            )

        logger.info(
            f"Unlinking {provider} account for user {user_id}",
            extra={"provider": provider, "user_id": user_id},
        )

        # Unlink the OAuth account
        success = await oauth_manager.unlink_oauth_account(
            user_id=user_id,
            provider=provider,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{provider} account is not linked to this user",
            )

        logger.info(
            f"Successfully unlinked {provider} account",
            extra={"provider": provider, "user_id": user_id},
        )

        return AccountUnlinkResponse(
            success=True,
            message=f"Successfully unlinked {provider} account",
            provider=provider,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Account unlinking failed for {provider}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink social account",
        )


@router.get(
    "/accounts",
    response_model=SocialAccountResponse,
    summary="List linked social accounts",
    description="Get list of OAuth provider accounts linked to authenticated user",
)
async def list_linked_accounts(
    current_user: Annotated[dict, Depends(require_authentication)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SocialAccountResponse:
    """
    List linked social accounts.

    Returns all OAuth provider accounts linked to the authenticated user.

    Args:
        current_user: Current authenticated user from JWT
        session: Database session

    Returns:
        List of linked social accounts

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 500: If listing accounts fails
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in authentication token",
            )

        logger.info(
            f"Listing linked accounts for user {user_id}",
            extra={"user_id": user_id},
        )

        # Query authentication methods for the user
        stmt = select(AuthenticationMethod).where(
            AuthenticationMethod.user_id == user_id,
            AuthenticationMethod.is_active == True,
        )
        result = await session.execute(stmt)
        auth_methods = result.scalars().all()

        accounts = [
            SocialAccountInfo(
                provider=method.provider,
                provider_user_id=method.provider_user_id,
                email=method.provider_data.get("email") if method.provider_data else None,
                name=method.provider_data.get("name") if method.provider_data else None,
                avatar_url=method.provider_data.get("avatar_url")
                if method.provider_data
                else None,
                profile_url=method.provider_data.get("profile_url")
                if method.provider_data
                else None,
                is_active=method.is_active,
                last_used_at=method.last_used_at,
                linked_at=method.created_at,
            )
            for method in auth_methods
        ]

        logger.info(
            f"Found {len(accounts)} linked accounts for user {user_id}",
            extra={"user_id": user_id, "account_count": len(accounts)},
        )

        return SocialAccountResponse(
            accounts=accounts,
            total=len(accounts),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to list linked accounts",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve linked accounts",
        )
