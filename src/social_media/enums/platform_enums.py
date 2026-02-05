"""
Social media platform enumerations and configurations.

This module defines platform types, OAuth scopes, API endpoints, and rate limits
for supported social media platforms.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Self

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    """
    Supported social media platforms.

    Each platform has associated configuration for OAuth authentication,
    API endpoints, and rate limits.
    """

    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"

    @classmethod
    def from_string(cls, value: str) -> Self:
        """
        Create Platform enum from string value.

        Args:
            value: Platform name as string (case-insensitive)

        Returns:
            Platform enum value

        Raises:
            ValueError: If platform name is not recognized

        Example:
            >>> Platform.from_string("facebook")
            <Platform.FACEBOOK: 'facebook'>
        """
        try:
            return cls[value.upper()]
        except KeyError as exc:
            valid_platforms = ", ".join([p.value for p in cls])
            logger.error(
                "Invalid platform requested",
                extra={"platform": value, "valid_platforms": valid_platforms},
            )
            raise ValueError(
                f"Invalid platform: {value}. Valid platforms: {valid_platforms}"
            ) from exc

    @classmethod
    def validate(cls, value: str) -> bool:
        """
        Validate if platform name is supported.

        Args:
            value: Platform name to validate

        Returns:
            True if platform is supported, False otherwise

        Example:
            >>> Platform.validate("facebook")
            True
            >>> Platform.validate("invalid")
            False
        """
        try:
            cls.from_string(value)
            return True
        except ValueError:
            return False

    @property
    def display_name(self) -> str:
        """
        Get user-friendly display name for platform.

        Returns:
            Capitalized platform name

        Example:
            >>> Platform.FACEBOOK.display_name
            'Facebook'
        """
        return self.value.capitalize()


@dataclass(frozen=True)
class PlatformConfig:
    """
    Platform-specific configuration for OAuth and API integration.

    Attributes:
        platform: Social media platform identifier
        oauth_authorize_url: URL for OAuth authorization
        oauth_token_url: URL for OAuth token exchange
        api_base_url: Base URL for platform API
        default_scopes: Default OAuth scopes for platform
        rate_limit_requests: Number of API requests allowed per window
        rate_limit_window_seconds: Rate limit window duration in seconds
        supports_refresh_token: Whether platform supports refresh tokens
    """

    platform: Platform
    oauth_authorize_url: str
    oauth_token_url: str
    api_base_url: str
    default_scopes: list[str]
    rate_limit_requests: int
    rate_limit_window_seconds: int
    supports_refresh_token: bool = True

    def validate_scopes(self, requested_scopes: list[str]) -> bool:
        """
        Validate if requested scopes are available for this platform.

        Args:
            requested_scopes: List of OAuth scopes to validate

        Returns:
            True if all requested scopes are available

        Example:
            >>> config = PLATFORM_CONFIGS[Platform.FACEBOOK]
            >>> config.validate_scopes(["email", "public_profile"])
            True
        """
        return all(scope in self.default_scopes for scope in requested_scopes)

    def get_rate_limit_key(self, user_id: str) -> str:
        """
        Generate Redis key for rate limiting.

        Args:
            user_id: User identifier

        Returns:
            Redis key for rate limit tracking

        Example:
            >>> config.get_rate_limit_key("user123")
            'rate_limit:facebook:user123'
        """
        return f"rate_limit:{self.platform.value}:{user_id}"


# Platform-specific configurations
PLATFORM_CONFIGS: dict[Platform, PlatformConfig] = {
    Platform.FACEBOOK: PlatformConfig(
        platform=Platform.FACEBOOK,
        oauth_authorize_url="https://www.facebook.com/v18.0/dialog/oauth",
        oauth_token_url="https://graph.facebook.com/v18.0/oauth/access_token",
        api_base_url="https://graph.facebook.com/v18.0",
        default_scopes=[
            "email",
            "public_profile",
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
            "pages_read_user_content",
        ],
        rate_limit_requests=200,
        rate_limit_window_seconds=3600,
        supports_refresh_token=True,
    ),
    Platform.INSTAGRAM: PlatformConfig(
        platform=Platform.INSTAGRAM,
        oauth_authorize_url="https://api.instagram.com/oauth/authorize",
        oauth_token_url="https://api.instagram.com/oauth/access_token",
        api_base_url="https://graph.instagram.com",
        default_scopes=[
            "user_profile",
            "user_media",
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
        ],
        rate_limit_requests=200,
        rate_limit_window_seconds=3600,
        supports_refresh_token=True,
    ),
    Platform.TWITTER: PlatformConfig(
        platform=Platform.TWITTER,
        oauth_authorize_url="https://twitter.com/i/oauth2/authorize",
        oauth_token_url="https://api.twitter.com/2/oauth2/token",
        api_base_url="https://api.twitter.com/2",
        default_scopes=[
            "tweet.read",
            "tweet.write",
            "users.read",
            "follows.read",
            "follows.write",
            "offline.access",
        ],
        rate_limit_requests=300,
        rate_limit_window_seconds=900,
        supports_refresh_token=True,
    ),
    Platform.TIKTOK: PlatformConfig(
        platform=Platform.TIKTOK,
        oauth_authorize_url="https://www.tiktok.com/v2/auth/authorize",
        oauth_token_url="https://open.tiktokapis.com/v2/oauth/token",
        api_base_url="https://open.tiktokapis.com/v2",
        default_scopes=[
            "user.info.basic",
            "user.info.profile",
            "user.info.stats",
            "video.list",
            "video.publish",
        ],
        rate_limit_requests=100,
        rate_limit_window_seconds=86400,
        supports_refresh_token=True,
    ),
    Platform.LINKEDIN: PlatformConfig(
        platform=Platform.LINKEDIN,
        oauth_authorize_url="https://www.linkedin.com/oauth/v2/authorization",
        oauth_token_url="https://www.linkedin.com/oauth/v2/accessToken",
        api_base_url="https://api.linkedin.com/v2",
        default_scopes=[
            "r_liteprofile",
            "r_emailaddress",
            "w_member_social",
            "r_organization_social",
            "w_organization_social",
        ],
        rate_limit_requests=500,
        rate_limit_window_seconds=86400,
        supports_refresh_token=True,
    ),
    Platform.YOUTUBE: PlatformConfig(
        platform=Platform.YOUTUBE,
        oauth_authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        oauth_token_url="https://oauth2.googleapis.com/token",
        api_base_url="https://www.googleapis.com/youtube/v3",
        default_scopes=[
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        rate_limit_requests=10000,
        rate_limit_window_seconds=86400,
        supports_refresh_token=True,
    ),
}


def get_platform_config(platform: Platform) -> PlatformConfig:
    """
    Get configuration for specified platform.

    Args:
        platform: Platform enum value

    Returns:
        Platform configuration

    Raises:
        ValueError: If platform is not configured

    Example:
        >>> config = get_platform_config(Platform.FACEBOOK)
        >>> config.api_base_url
        'https://graph.facebook.com/v18.0'
    """
    if platform not in PLATFORM_CONFIGS:
        logger.error("Platform configuration not found", extra={"platform": platform.value})
        raise ValueError(f"Configuration not found for platform: {platform.value}")

    return PLATFORM_CONFIGS[platform]


def get_all_platforms() -> list[Platform]:
    """
    Get list of all supported platforms.

    Returns:
        List of supported platform enums

    Example:
        >>> platforms = get_all_platforms()
        >>> len(platforms)
        6
    """
    return list(Platform)


def validate_platform_and_scopes(platform: str, scopes: list[str]) -> tuple[bool, str]:
    """
    Validate platform and requested OAuth scopes.

    Args:
        platform: Platform name as string
        scopes: List of OAuth scopes to validate

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> valid, msg = validate_platform_and_scopes("facebook", ["email"])
        >>> valid
        True
    """
    if not Platform.validate(platform):
        return False, f"Invalid platform: {platform}"

    try:
        platform_enum = Platform.from_string(platform)
        config = get_platform_config(platform_enum)

        invalid_scopes = [scope for scope in scopes if scope not in config.default_scopes]
        if invalid_scopes:
            return False, f"Invalid scopes for {platform}: {', '.join(invalid_scopes)}"

        return True, ""
    except Exception as exc:
        logger.error(
            "Error validating platform and scopes",
            extra={"platform": platform, "scopes": scopes, "error": str(exc)},
        )
        return False, f"Validation error: {str(exc)}"
