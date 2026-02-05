import base64
import hashlib
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.payment_service.gateways.base import (
    BaseGateway,
    PaymentError,
    ValidationError,
    WebhookError,
)

logger = logging.getLogger(__name__)


class PayPalGateway(BaseGateway):
    """
    PayPal payment gateway implementation.

    Implements PayPal Orders API v2 and Payouts API with OAuth 2.0 authentication,
    payment processing, payout processing, IPN webhook handling, and comprehensive
    error handling.
    """

    PAYPAL_API_URL_SANDBOX = "https://api-m.sandbox.paypal.com"
    PAYPAL_API_URL_LIVE = "https://api-m.paypal.com"
    PAYPAL_API_VERSION = "v2"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        webhook_id: Optional[str] = None,
        sandbox: bool = True,
        **config: Any,
    ):
        """
        Initialize PayPal gateway.

        Args:
            api_key: PayPal client ID
            api_secret: PayPal client secret
            webhook_id: PayPal webhook ID for signature verification
            sandbox: Use sandbox environment (default: True)
            **config: Additional configuration options
        """
        super().__init__(api_key, **config)
        self.api_secret = api_secret
        self.webhook_id = webhook_id
        self.sandbox = sandbox
        self.base_url = self.PAYPAL_API_URL_SANDBOX if sandbox else self.PAYPAL_API_URL_LIVE
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
        )

    def _validate_configuration(self) -> None:
        """Validate PayPal gateway configuration."""
        super()._validate_configuration()

        if not self.api_secret:
            raise ValidationError(
                "API secret is required",
                code="MISSING_API_SECRET",
            )

    async def _get_access_token(self) -> str:
        """
        Get OAuth 2.0 access token with caching.

        Returns:
            Access token string

        Raises:
            PaymentError: If token generation fails
        """
        current_time = time.time()

        if self._access_token and current_time < self._token_expires_at:
            return self._access_token

        try:
            auth_string = f"{self.api_key}:{self.api_secret}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            response = await self._client.post(
                "/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )

            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = current_time + expires_in - 60

                logger.info("PayPal access token obtained successfully")
                return self._access_token

            error_data = response.json() if response.text else {}
            raise PaymentError(
                message=f"Failed to obtain PayPal access token: {error_data.get('error_description', 'Unknown error')}",
                code="AUTH_ERROR",
                status_code=response.status_code,
            )

        except httpx.HTTPError as e:
            raise PaymentError(
                message=f"HTTP error during PayPal authentication: {str(e)}",
                code="HTTP_ERROR",
                original_error=str(e),
            )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to PayPal API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload
            headers: Additional headers

        Returns:
            API response data

        Raises:
            PaymentError: If API request fails
        """
        access_token = await self._get_access_token()

        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if headers:
            request_headers.update(headers)

        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                json=data,
                headers=request_headers,
            )

            if response.status_code in (200, 201, 204):
                return response.json() if response.text else {}

            error_data = response.json() if response.text else {}
            error_details = error_data.get("details", [{}])[0] if error_data.get("details") else {}

            raise PaymentError(
                message=error_data.get("message", "PayPal API request failed"),
                code=error_data.get("name", "PAYPAL_ERROR"),
                status_code=response.status_code,
                paypal_debug_id=response.headers.get("PayPal-Debug-Id"),
                issue=error_details.get("issue"),
            )

        except httpx.HTTPError as e:
            raise PaymentError(
                message=f"HTTP error during PayPal request: {str(e)}",
                code="HTTP_ERROR",
                original_error=str(e),
            )

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a PayPal order for payment.

        Args:
            amount: Payment amount
            currency: Currency code (USD, EUR, etc.)
            metadata: Additional payment metadata
            **kwargs: Additional PayPal parameters (return_url, cancel_url, etc.)

        Returns:
            Payment order response dict

        Raises:
            PaymentError: If payment creation fails
            ValidationError: If input validation fails
        """
        try:
            if amount <= 0:
                raise ValidationError(
                    "Amount must be positive",
                    code="INVALID_AMOUNT",
                    amount=str(amount),
                )

            if not currency or len(currency) != 3:
                raise ValidationError(
                    "Invalid currency code",
                    code="INVALID_CURRENCY",
                    currency=currency,
                )

            purchase_units = [{
                "amount": {
                    "currency_code": currency.upper(),
                    "value": str(amount),
                },
            }]

            if metadata:
                purchase_units[0]["custom_id"] = metadata.get("wallet_id", str(uuid.uuid4()))
                purchase_units[0]["description"] = kwargs.get("description", "Payment")

            order_data = {
                "intent": "CAPTURE",
                "purchase_units": purchase_units,
            }

            if "return_url" in kwargs or "cancel_url" in kwargs:
                order_data["application_context"] = {
                    "return_url": kwargs.get("return_url", "https://example.com/return"),
                    "cancel_url": kwargs.get("cancel_url", "https://example.com/cancel"),
                }

            self._log_operation(
                operation="create_payment",
                success=False,
                amount=str(amount),
                currency=currency,
            )

            response = await self._make_request(
                method="POST",
                endpoint="/v2/checkout/orders",
                data=order_data,
            )

            self._log_operation(
                operation="create_payment",
                success=True,
                order_id=response.get("id"),
                status=response.get("status"),
                amount=str(amount),
                currency=currency,
            )

            approval_link = None
            for link in response.get("links", []):
                if link.get("rel") == "approve":
                    approval_link = link.get("href")
                    break

            return self.format_response(
                success=True,
                data={
                    "payment_id": response.get("id"),
                    "status": response.get("status"),
                    "amount": amount,
                    "currency": currency.upper(),
                    "approval_url": approval_link,
                    "created": response.get("create_time"),
                    "metadata": metadata or {},
                },
            )

        except (ValidationError, PaymentError):
            raise
        except Exception as e:
            raise self._handle_error(e, "create_payment", amount=str(amount), currency=currency)

    async def confirm_payment(self, payment_id: str, **kwargs: Any) -> dict[str, Any]:
        """
        Capture a PayPal order (confirm payment).

        Args:
            payment_id: PayPal order ID
            **kwargs: Additional confirmation parameters

        Returns:
            Confirmation response dict

        Raises:
            PaymentError: If payment confirmation fails
        """
        try:
            if not payment_id:
                raise ValidationError(
                    "Invalid payment ID",
                    code="INVALID_PAYMENT_ID",
                    payment_id=payment_id,
                )

            self._log_operation(
                operation="confirm_payment",
                success=False,
                payment_id=payment_id,
            )

            response = await self._make_request(
                method="POST",
                endpoint=f"/v2/checkout/orders/{payment_id}/capture",
                data={},
            )

            purchase_unit = response.get("purchase_units", [{}])[0]
            capture = purchase_unit.get("payments", {}).get("captures", [{}])[0]
            amount_data = capture.get("amount", {})

            self._log_operation(
                operation="confirm_payment",
                success=True,
                payment_id=payment_id,
                status=response.get("status"),
            )

            return self.format_response(
                success=True,
                data={
                    "payment_id": response.get("id"),
                    "status": response.get("status"),
                    "amount": Decimal(amount_data.get("value", "0")),
                    "currency": amount_data.get("currency_code", "USD"),
                    "capture_id": capture.get("id"),
                },
            )

        except (ValidationError, PaymentError):
            raise
        except Exception as e:
            raise self._handle_error(e, "confirm_payment", payment_id=payment_id)

    async def process_refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Process a refund for a PayPal capture.

        Args:
            payment_id: PayPal capture ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Additional refund parameters

        Returns:
            Refund response dict

        Raises:
            PaymentError: If refund processing fails
        """
        try:
            if not payment_id:
                raise ValidationError(
                    "Payment ID is required",
                    code="MISSING_PAYMENT_ID",
                )

            refund_data = {}

            if amount is not None:
                if amount <= 0:
                    raise ValidationError(
                        "Refund amount must be positive",
                        code="INVALID_AMOUNT",
                        amount=str(amount),
                    )
                currency = kwargs.get("currency", "USD")
                refund_data["amount"] = {
                    "currency_code": currency.upper(),
                    "value": str(amount),
                }

            if reason:
                refund_data["note_to_payer"] = reason

            self._log_operation(
                operation="process_refund",
                success=False,
                payment_id=payment_id,
                amount=str(amount) if amount else "full",
                reason=reason,
            )

            response = await self._make_request(
                method="POST",
                endpoint=f"/v2/payments/captures/{payment_id}/refund",
                data=refund_data,
            )

            refund_amount_data = response.get("amount", {})
            refund_amount = Decimal(refund_amount_data.get("value", "0"))

            self._log_operation(
                operation="process_refund",
                success=True,
                refund_id=response.get("id"),
                status=response.get("status"),
                payment_id=payment_id,
            )

            return self.format_response(
                success=True,
                data={
                    "refund_id": response.get("id"),
                    "payment_id": payment_id,
                    "status": response.get("status"),
                    "amount": refund_amount,
                    "currency": refund_amount_data.get("currency_code", "USD"),
                    "created": response.get("create_time"),
                },
            )

        except (ValidationError, PaymentError):
            raise
        except Exception as e:
            raise self._handle_error(
                e,
                "process_refund",
                payment_id=payment_id,
                amount=str(amount) if amount else None,
            )

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        **kwargs: Any,
    ) -> bool:
        """
        Verify PayPal webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature: PayPal webhook signature headers
            **kwargs: Additional parameters (cert_url, auth_algo, transmission_id, transmission_time)

        Returns:
            True if signature is valid

        Raises:
            WebhookError: If signature verification fails
        """
        try:
            if not self.webhook_id:
                raise WebhookError(
                    "Webhook ID not configured",
                    code="MISSING_WEBHOOK_ID",
                )

            cert_url = kwargs.get("cert_url")
            auth_algo = kwargs.get("auth_algo")
            transmission_id = kwargs.get("transmission_id")
            transmission_time = kwargs.get("transmission_time")

            if not all([cert_url, auth_algo, transmission_id, transmission_time]):
                raise WebhookError(
                    "Missing required webhook headers",
                    code="MISSING_HEADERS",
                )

            verification_data = {
                "transmission_id": transmission_id,
                "transmission_time": transmission_time,
                "cert_url": cert_url,
                "auth_algo": auth_algo,
                "transmission_sig": signature,
                "webhook_id": self.webhook_id,
                "webhook_event": payload.decode("utf-8"),
            }

            response = await self._make_request(
                method="POST",
                endpoint="/v1/notifications/verify-webhook-signature",
                data=verification_data,
            )

            verification_status = response.get("verification_status")

            if verification_status == "SUCCESS":
                logger.info("PayPal webhook signature verified successfully")
                return True

            raise WebhookError(
                "Webhook signature verification failed",
                code="SIGNATURE_MISMATCH",
                verification_status=verification_status,
            )

        except WebhookError:
            raise
        except Exception as e:
            raise WebhookError(
                f"Error verifying webhook signature: {str(e)}",
                code="VERIFICATION_ERROR",
                original_error=str(e),
            )

    async def handle_webhook(
        self,
        event_type: str,
        event_data: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Handle PayPal webhook event.

        Args:
            event_type: PayPal event type (e.g., PAYMENT.CAPTURE.COMPLETED)
            event_data: Event payload data
            **kwargs: Additional context

        Returns:
            Processing result dict

        Raises:
            WebhookError: If webhook handling fails
        """
        try:
            event_id = event_data.get("id")
            resource = event_data.get("resource", {})

            logger.info(
                "Processing PayPal webhook event",
                extra={
                    "event_type": event_type,
                    "event_id": event_id,
                },
            )

            result_data = {
                "event_id": event_id,
                "event_type": event_type,
                "processed": True,
            }

            if event_type == "PAYMENT.CAPTURE.COMPLETED":
                result_data.update({
                    "payment_id": resource.get("id"),
                    "amount": Decimal(resource.get("amount", {}).get("value", "0")),
                    "currency": resource.get("amount", {}).get("currency_code", "USD"),
                    "status": "completed",
                })

            elif event_type == "PAYMENT.CAPTURE.DENIED":
                result_data.update({
                    "payment_id": resource.get("id"),
                    "status": "denied",
                })

            elif event_type == "PAYMENT.CAPTURE.REFUNDED":
                result_data.update({
                    "payment_id": resource.get("id"),
                    "refund_id": resource.get("id"),
                    "amount": Decimal(resource.get("amount", {}).get("value", "0")),
                    "currency": resource.get("amount", {}).get("currency_code", "USD"),
                    "status": "refunded",
                })

            else:
                logger.warning(
                    "Unhandled PayPal webhook event type",
                    extra={"event_type": event_type, "event_id": event_id},
                )
                result_data["processed"] = False

            self._log_operation(
                operation="handle_webhook",
                success=True,
                event_type=event_type,
                event_id=event_id,
            )

            return self.format_response(success=True, data=result_data)

        except Exception as e:
            raise self._handle_error(
                e,
                "handle_webhook",
                event_type=event_type,
                event_id=event_data.get("id"),
            )

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self._client.aclose()
