"""
PayPal Payment Gateway.

This module provides PayPal payment gateway integration with OAuth 2.0
authentication and IPN webhook handling.
"""

from src.payment_service.gateways.paypal.client import PayPalGateway
from src.payment_service.gateways.paypal.oauth import PayPalOAuth
from src.payment_service.gateways.paypal.webhook import PayPalWebhookHandler

__all__ = [
    "PayPalGateway",
    "PayPalOAuth",
    "PayPalWebhookHandler",
]
