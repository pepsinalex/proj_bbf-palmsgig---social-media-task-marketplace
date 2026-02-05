import hashlib
import hmac
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


class StripeGateway(BaseGateway):
    """
    Stripe payment gateway implementation.

    Implements Stripe Payment Intents API with SCA compliance, refund processing,
    webhook signature verification, and comprehensive error handling.
    """

    STRIPE_API_URL = "https://api.stripe.com/v1"
    STRIPE_API_VERSION = "2023-10-16"

    def __init__(
        self,
        api_key: str,
        webhook_secret: Optional[str] = None,
        **config: Any,
    ):
        """
        Initialize Stripe gateway.

        Args:
            api_key: Stripe secret API key
            webhook_secret: Stripe webhook endpoint secret for signature verification
            **config: Additional configuration options
        """
        super().__init__(api_key, **config)
        self.webhook_secret = webhook_secret
        self._client = httpx.AsyncClient(
            base_url=self.STRIPE_API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Stripe-Version": self.STRIPE_API_VERSION,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30.0,
        )
        self._rate_limit_remaining = 100
        self._rate_limit_reset = time.time()

    def _validate_configuration(self) -> None:
        """Validate Stripe gateway configuration."""
        super()._validate_configuration()

        if not self.api_key.startswith(("sk_test_", "sk_live_")):
            raise ValidationError(
                "Invalid Stripe API key format",
                code="INVALID_API_KEY",
                api_key_prefix=self.api_key[:7] if len(self.api_key) > 7 else None,
            )

    def _generate_idempotency_key(self, **kwargs: Any) -> str:
        """
        Generate idempotency key for Stripe API request.

        Args:
            **kwargs: Request parameters to hash

        Returns:
            UUID-based idempotency key
        """
        data_str = str(sorted(kwargs.items()))
        hash_digest = hashlib.sha256(data_str.encode()).hexdigest()
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, hash_digest))

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to Stripe API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload
            idempotency_key: Optional idempotency key for POST requests

        Returns:
            API response data

        Raises:
            PaymentError: If API request fails
        """
        headers = {}
        if idempotency_key and method == "POST":
            headers["Idempotency-Key"] = idempotency_key

        try:
            if self._rate_limit_remaining <= 5 and time.time() < self._rate_limit_reset:
                wait_time = self._rate_limit_reset - time.time()
                logger.warning(
                    "Approaching rate limit, waiting",
                    extra={
                        "wait_time": wait_time,
                        "remaining": self._rate_limit_remaining,
                    },
                )
                await self._client.aclose()
                await self._client.__aenter__()

            response = await self._client.request(
                method=method,
                url=endpoint,
                data=data,
                headers=headers,
            )

            self._rate_limit_remaining = int(
                response.headers.get("X-RateLimit-Remaining", 100)
            )
            reset_timestamp = response.headers.get("X-RateLimit-Reset")
            if reset_timestamp:
                self._rate_limit_reset = float(reset_timestamp)

            if response.status_code == 200:
                return response.json()

            error_data = response.json() if response.text else {}
            error_info = error_data.get("error", {})

            raise PaymentError(
                message=error_info.get("message", "Stripe API request failed"),
                code=error_info.get("code", "STRIPE_ERROR"),
                status_code=response.status_code,
                stripe_error_type=error_info.get("type"),
                request_id=response.headers.get("Request-Id"),
            )

        except httpx.HTTPError as e:
            raise PaymentError(
                message=f"HTTP error during Stripe request: {str(e)}",
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
        Create a Stripe Payment Intent.

        Args:
            amount: Payment amount
            currency: Currency code (USD, EUR, etc.)
            metadata: Additional payment metadata
            **kwargs: Additional Stripe parameters (customer, payment_method, etc.)

        Returns:
            Payment Intent response dict

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

            formatted_amount = self.format_amount(amount, currency)

            request_data = {
                "amount": formatted_amount,
                "currency": currency.lower(),
                "automatic_payment_methods[enabled]": "true",
            }

            if metadata:
                for key, value in metadata.items():
                    request_data[f"metadata[{key}]"] = str(value)

            for key in ["customer", "payment_method", "description", "receipt_email"]:
                if key in kwargs:
                    request_data[key] = kwargs[key]

            if "confirm" in kwargs and kwargs["confirm"]:
                request_data["confirm"] = "true"

            idempotency_key = kwargs.get("idempotency_key") or self._generate_idempotency_key(
                amount=formatted_amount,
                currency=currency,
                metadata=metadata,
            )

            self._log_operation(
                operation="create_payment",
                success=False,
                amount=str(amount),
                currency=currency,
                idempotency_key=idempotency_key,
            )

            response = await self._make_request(
                method="POST",
                endpoint="/payment_intents",
                data=request_data,
                idempotency_key=idempotency_key,
            )

            self._log_operation(
                operation="create_payment",
                success=True,
                payment_intent_id=response.get("id"),
                status=response.get("status"),
                amount=str(amount),
                currency=currency,
            )

            return self.format_response(
                success=True,
                data={
                    "payment_id": response.get("id"),
                    "client_secret": response.get("client_secret"),
                    "status": response.get("status"),
                    "amount": amount,
                    "currency": currency.upper(),
                    "created": response.get("created"),
                    "metadata": response.get("metadata", {}),
                },
            )

        except (ValidationError, PaymentError):
            raise
        except Exception as e:
            raise self._handle_error(e, "create_payment", amount=str(amount), currency=currency)

    async def confirm_payment(self, payment_id: str, **kwargs: Any) -> dict[str, Any]:
        """
        Confirm a Stripe Payment Intent.

        Args:
            payment_id: Stripe Payment Intent ID
            **kwargs: Additional confirmation parameters

        Returns:
            Confirmation response dict

        Raises:
            PaymentError: If payment confirmation fails
        """
        try:
            if not payment_id or not payment_id.startswith("pi_"):
                raise ValidationError(
                    "Invalid payment intent ID",
                    code="INVALID_PAYMENT_ID",
                    payment_id=payment_id,
                )

            request_data = {}
            if "payment_method" in kwargs:
                request_data["payment_method"] = kwargs["payment_method"]

            idempotency_key = kwargs.get("idempotency_key") or self._generate_idempotency_key(
                payment_id=payment_id,
                operation="confirm",
            )

            self._log_operation(
                operation="confirm_payment",
                success=False,
                payment_id=payment_id,
            )

            response = await self._make_request(
                method="POST",
                endpoint=f"/payment_intents/{payment_id}/confirm",
                data=request_data,
                idempotency_key=idempotency_key,
            )

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
                    "amount": self.parse_amount(
                        response.get("amount", 0),
                        response.get("currency", "usd"),
                    ),
                    "currency": response.get("currency", "").upper(),
                    "confirmation_method": response.get("confirmation_method"),
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
        Process a refund for a Stripe payment.

        Args:
            payment_id: Stripe Payment Intent ID or Charge ID
            amount: Refund amount (None for full refund)
            reason: Refund reason (requested_by_customer, duplicate, fraudulent)
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

            request_data = {}

            if payment_id.startswith("pi_"):
                request_data["payment_intent"] = payment_id
            elif payment_id.startswith("ch_"):
                request_data["charge"] = payment_id
            else:
                raise ValidationError(
                    "Invalid payment ID format",
                    code="INVALID_PAYMENT_ID",
                    payment_id=payment_id,
                )

            if amount is not None:
                if amount <= 0:
                    raise ValidationError(
                        "Refund amount must be positive",
                        code="INVALID_AMOUNT",
                        amount=str(amount),
                    )
                currency = kwargs.get("currency", "usd")
                request_data["amount"] = self.format_amount(amount, currency)

            if reason:
                valid_reasons = ["requested_by_customer", "duplicate", "fraudulent"]
                if reason not in valid_reasons:
                    raise ValidationError(
                        f"Invalid refund reason. Must be one of: {', '.join(valid_reasons)}",
                        code="INVALID_REASON",
                        reason=reason,
                    )
                request_data["reason"] = reason

            if "metadata" in kwargs:
                for key, value in kwargs["metadata"].items():
                    request_data[f"metadata[{key}]"] = str(value)

            idempotency_key = kwargs.get("idempotency_key") or self._generate_idempotency_key(
                payment_id=payment_id,
                amount=amount,
                reason=reason,
            )

            self._log_operation(
                operation="process_refund",
                success=False,
                payment_id=payment_id,
                amount=str(amount) if amount else "full",
                reason=reason,
            )

            response = await self._make_request(
                method="POST",
                endpoint="/refunds",
                data=request_data,
                idempotency_key=idempotency_key,
            )

            self._log_operation(
                operation="process_refund",
                success=True,
                refund_id=response.get("id"),
                status=response.get("status"),
                payment_id=payment_id,
            )

            refund_amount = self.parse_amount(
                response.get("amount", 0),
                response.get("currency", "usd"),
            )

            return self.format_response(
                success=True,
                data={
                    "refund_id": response.get("id"),
                    "payment_id": payment_id,
                    "status": response.get("status"),
                    "amount": refund_amount,
                    "currency": response.get("currency", "").upper(),
                    "reason": response.get("reason"),
                    "created": response.get("created"),
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
        Verify Stripe webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature: Stripe-Signature header value
            **kwargs: Additional parameters (timestamp, tolerance)

        Returns:
            True if signature is valid

        Raises:
            WebhookError: If signature verification fails
        """
        try:
            if not self.webhook_secret:
                raise WebhookError(
                    "Webhook secret not configured",
                    code="MISSING_WEBHOOK_SECRET",
                )

            if not signature:
                raise WebhookError(
                    "Missing webhook signature",
                    code="MISSING_SIGNATURE",
                )

            signature_parts = {}
            for part in signature.split(","):
                key, value = part.split("=", 1)
                signature_parts[key] = value

            timestamp = signature_parts.get("t")
            signatures = [
                v for k, v in signature_parts.items() if k.startswith("v1")
            ]

            if not timestamp or not signatures:
                raise WebhookError(
                    "Invalid signature format",
                    code="INVALID_SIGNATURE_FORMAT",
                    signature=signature[:20],
                )

            tolerance = kwargs.get("tolerance", 300)
            current_time = int(time.time())
            timestamp_int = int(timestamp)

            if abs(current_time - timestamp_int) > tolerance:
                raise WebhookError(
                    "Webhook timestamp outside tolerance window",
                    code="TIMESTAMP_OUT_OF_RANGE",
                    timestamp=timestamp,
                    current_time=current_time,
                    tolerance=tolerance,
                )

            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected_signature = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            signature_valid = any(
                hmac.compare_digest(expected_signature, sig)
                for sig in signatures
            )

            if not signature_valid:
                raise WebhookError(
                    "Webhook signature verification failed",
                    code="SIGNATURE_MISMATCH",
                )

            logger.info(
                "Webhook signature verified successfully",
                extra={"timestamp": timestamp},
            )

            return True

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
        Handle Stripe webhook event.

        Args:
            event_type: Stripe event type (e.g., payment_intent.succeeded)
            event_data: Event payload data
            **kwargs: Additional context

        Returns:
            Processing result dict

        Raises:
            WebhookError: If webhook handling fails
        """
        try:
            event_id = event_data.get("id")
            event_object = event_data.get("object")

            logger.info(
                "Processing webhook event",
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

            if event_type == "payment_intent.succeeded":
                payment_intent = event_object
                result_data.update({
                    "payment_id": payment_intent.get("id"),
                    "amount": self.parse_amount(
                        payment_intent.get("amount", 0),
                        payment_intent.get("currency", "usd"),
                    ),
                    "currency": payment_intent.get("currency", "").upper(),
                    "status": "succeeded",
                })

            elif event_type == "payment_intent.payment_failed":
                payment_intent = event_object
                last_error = payment_intent.get("last_payment_error", {})
                result_data.update({
                    "payment_id": payment_intent.get("id"),
                    "status": "failed",
                    "error_code": last_error.get("code"),
                    "error_message": last_error.get("message"),
                })

            elif event_type == "charge.refunded":
                charge = event_object
                result_data.update({
                    "charge_id": charge.get("id"),
                    "payment_id": charge.get("payment_intent"),
                    "amount_refunded": self.parse_amount(
                        charge.get("amount_refunded", 0),
                        charge.get("currency", "usd"),
                    ),
                    "status": "refunded",
                })

            elif event_type == "charge.dispute.created":
                dispute = event_object
                result_data.update({
                    "dispute_id": dispute.get("id"),
                    "charge_id": dispute.get("charge"),
                    "amount": self.parse_amount(
                        dispute.get("amount", 0),
                        dispute.get("currency", "usd"),
                    ),
                    "reason": dispute.get("reason"),
                    "status": dispute.get("status"),
                })

            else:
                logger.warning(
                    "Unhandled webhook event type",
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
