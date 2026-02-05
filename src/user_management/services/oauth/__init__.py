"""OAuth services for social media authentication."""

from src.user_management.services.oauth.base import BaseOAuthProvider
from src.user_management.services.oauth.facebook import FacebookOAuthProvider
from src.user_management.services.oauth.google import GoogleOAuthProvider
from src.user_management.services.oauth.manager import OAuthManager
from src.user_management.services.oauth.twitter import TwitterOAuthProvider

__all__ = [
    "BaseOAuthProvider",
    "GoogleOAuthProvider",
    "FacebookOAuthProvider",
    "TwitterOAuthProvider",
    "OAuthManager",
]
