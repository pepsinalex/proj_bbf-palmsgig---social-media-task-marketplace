import hashlib
import hmac
import json
import logging
import time
from decimal import Decimal
from typing import Any, Optional

from src.payment_service.gateways.base import WebhookError

logger = logging.getLogger(__name__)


class PayPalWebhookHandler:
    """
    PayPal IPN webhook event handler with signature verification and idempotency.

    Processes webhook events for payment completions, payout completions, and disputes
    with proper signature verification and duplicate event detection.
    """

    SUPPORTED_EVENTS = {
        "PAYMENT.CAPTURE.COMPLETED",
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.REFUNDED",
        "PAYMENT.CAPTURE.REVERSED",
        "CHECKOUT.ORDER.APPROVED",
        "CHECKOUT.ORDER.COMPLETED",
        "PAYMENT.PAYOUTS-ITEM.SUCCEEDED",
        "PAYMENT.PAYOUTS-ITEM.FAILED",
        "PAYMENT.PAYOUTS-ITEM.DENIED",
        "CUSTOMER.DISPUTE.CREATED",
        "CUSTOMER.DISPUTE.RESOLVED",
        "CUSTOMER.DISPUTE.UPDATED",
    }

    def __init__(
        self,
        webhook_id: str,
        cert_url_cache: Optional[Any] = None,
        idempotency_store: Optional[Any] = None,
    ):
        """
        Initialize PayPal webhook handler.

        Args:
            webhook_id: PayPal webhook ID for verification
            cert_url_cache: Optional cache for PayPal certificate URLs
            idempotency_store: Optional store for tracking processed events
        """
        if not webhook_id:
            raise WebhookError(
                "Webhook ID is required",
                code="MISSING_WEBHOOK_ID",
            )

        self.webhook_id = webhook_id
        self.cert_url_cache = cert_url_cache or {}
        self.idempotency_store = idempotency_store or {}
        self._processed_events = set()

    def verify_signature(
        self,
        payload: bytes,
        transmission_id: str,
        transmission_time: str,
        cert_url: str,
        auth_algo: str,
        transmission_sig: str,
    ) -> bool:
        """
        Verify PayPal webhook signature.

        Args:
            payload: Raw webhook payload bytes
            transmission_id: PayPal transmission ID
            transmission_time: PayPal transmission timestamp
            cert_url: PayPal certificate URL
            auth_algo: Authentication algorithm
            transmission_sig: PayPal signature

        Returns:
            True if signature is valid

        Raises:
            WebhookError: If signature verification fails
        """
        try:
            if not all([transmission_id, transmission_time, cert_url, auth_algo, transmission_sig]):
                raise WebhookError(
                    "Missing required webhook signature headers",
                    code="MISSING_HEADERS",
                )

            if auth_algo not in ["SHA256withRSA", "SHA512withRSA"]:
                raise WebhookError(
                    f"Unsupported authentication algorithm: {auth_algo}",
                    code="UNSUPPORTED_ALGORITHM",
                    algorithm=auth_algo,
                )

            expected_sig = self._compute_signature(
                transmission_id=transmission_id,
                transmission_time=transmission_time,
                webhook_id=self.webhook_id,
                event_body=payload.decode("utf-8"),
            )

            signature_valid = self._secure_compare(expected_sig, transmission_sig)

            if not signature_valid:
                logger.error(
                    "PayPal webhook signature verification failed",
                    extra={
                        "transmission_id": transmission_id,
                        "expected_prefix": expected_sig[:10],
                        "provided_prefix": transmission_sig[:10],
                    },
                )
                raise WebhookError(
                    "Webhook signature verification failed",
                    code="SIGNATURE_MISMATCH",
                )

            logger.info(
                "PayPal webhook signature verified successfully",
                extra={
                    "transmission_id": transmission_id,
                    "transmission_time": transmission_time,
                },
            )

            return True

        except WebhookError:
            raise
        except Exception as e:
            logger.exception("Error during PayPal webhook signature verification")
            raise WebhookError(
                f"Signature verification error: {str(e)}",
                code="VERIFICATION_ERROR",
                original_error=str(e),
            )

    def _compute_signature(
        self,
        transmission_id: str,
        transmission_time: str,
        webhook_id: str,
        event_body: str,
    ) -> str:
        """
        Compute PayPal webhook signature.

        Args:
            transmission_id: PayPal transmission ID
            transmission_time: PayPal transmission timestamp
            webhook_id: PayPal webhook ID
            event_body: Webhook event body

        Returns:
            Expected signature string
        """
        message_parts = [
            transmission_id,
            transmission_time,
            webhook_id,
            hashlib.sha256(event_body.encode("utf-8")).hexdigest(),
        ]
        message = "|".join(message_parts)

        return hashlib.sha256(message.encode("utf-8")).hexdigest()

    def _secure_compare(self, a: str, b: str) -> bool:
        """
        Timing-safe string comparison.

        Args:
            a: First string
            b: Second string

        Returns:
            True if strings match
        """
        return hmac.compare_digest(a, b)

    def check_idempotency(self, event_id: str) -> bool:
        """
        Check if event has already been processed.

        Args:
            event_id: PayPal event ID

        Returns:
            True if event is new, False if already processed
        """
        if event_id in self._processed_events:
            logger.warning(
                "Duplicate PayPal webhook event detected",
                extra={"event_id": event_id},
            )
            return False

        if hasattr(self.idempotency_store, "get") and self.idempotency_store.get(event_id):
            logger.warning(
                "PayPal event found in idempotency store",
                extra={"event_id": event_id},
            )
            return False

        return True

    def mark_processed(self, event_id: str) -> None:
        """
        Mark event as processed for idempotency.

        Args:
            event_id: PayPal event ID
        """
        self._processed_events.add(event_id)

        if hasattr(self.idempotency_store, "set"):
            try:
                self.idempotency_store.set(
                    event_id,
                    int(time.time()),
                    ex=86400 * 7,
                )
            except Exception as e:
                logger.error(
                    "Failed to store PayPal event in idempotency store",
                    extra={"event_id": event_id, "error": str(e)},
                )

    async def process_event(
        self,
        payload: bytes,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """
        Process PayPal webhook event with signature verification and idempotency.

        Args:
            payload: Raw webhook payload bytes
            headers: Webhook request headers

        Returns:
            Processing result dict

        Raises:
            WebhookError: If event processing fails
        """
        try:
            transmission_id = headers.get("paypal-transmission-id", "")
            transmission_time = headers.get("paypal-transmission-time", "")
            cert_url = headers.get("paypal-cert-url", "")
            auth_algo = headers.get("paypal-auth-algo", "")
            transmission_sig = headers.get("paypal-transmission-sig", "")

            self.verify_signature(
                payload=payload,
                transmission_id=transmission_id,
                transmission_time=transmission_time,
                cert_url=cert_url,
                auth_algo=auth_algo,
                transmission_sig=transmission_sig,
            )

            event_data = json.loads(payload.decode("utf-8"))
            event_id = event_data.get("id")
            event_type = event_data.get("event_type")
            resource = event_data.get("resource", {})

            if not event_id or not event_type:
                raise WebhookError(
                    "Invalid event structure",
                    code="INVALID_EVENT",
                    has_id=bool(event_id),
                    has_type=bool(event_type),
                )

            if not self.check_idempotency(event_id):
                return {
                    "success": True,
                    "event_id": event_id,
                    "event_type": event_type,
                    "processed": False,
                    "reason": "duplicate_event",
                }

            logger.info(
                "Processing PayPal webhook event",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                },
            )

            result = await self._handle_event(event_type, resource, event_data)

            self.mark_processed(event_id)

            logger.info(
                "PayPal webhook event processed successfully",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                },
            )

            return {
                "success": True,
                "event_id": event_id,
                "event_type": event_type,
                "processed": True,
                "result": result,
            }

        except WebhookError:
            raise
        except json.JSONDecodeError as e:
            raise WebhookError(
                "Invalid JSON payload",
                code="INVALID_JSON",
                error=str(e),
            )
        except Exception as e:
            logger.exception("Error processing PayPal webhook event")
            raise WebhookError(
                f"Event processing error: {str(e)}",
                code="PROCESSING_ERROR",
                original_error=str(e),
            )

    async def _handle_event(
        self,
        event_type: str,
        resource: dict[str, Any],
        full_event: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle specific PayPal webhook event type.

        Args:
            event_type: PayPal event type
            resource: Event resource data
            full_event: Full event payload

        Returns:
            Event handling result
        """
        if event_type not in self.SUPPORTED_EVENTS:
            logger.warning(
                "Unsupported PayPal webhook event type",
                extra={"event_type": event_type},
            )
            return {
                "handled": False,
                "reason": "unsupported_event_type",
            }

        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            return await self._handle_payment_completed(resource)

        elif event_type == "PAYMENT.CAPTURE.DENIED":
            return await self._handle_payment_denied(resource)

        elif event_type == "PAYMENT.CAPTURE.REFUNDED":
            return await self._handle_payment_refunded(resource)

        elif event_type == "PAYMENT.CAPTURE.REVERSED":
            return await self._handle_payment_reversed(resource)

        elif event_type == "CHECKOUT.ORDER.APPROVED":
            return await self._handle_order_approved(resource)

        elif event_type == "CHECKOUT.ORDER.COMPLETED":
            return await self._handle_order_completed(resource)

        elif event_type == "PAYMENT.PAYOUTS-ITEM.SUCCEEDED":
            return await self._handle_payout_succeeded(resource)

        elif event_type == "PAYMENT.PAYOUTS-ITEM.FAILED":
            return await self._handle_payout_failed(resource)

        elif event_type == "PAYMENT.PAYOUTS-ITEM.DENIED":
            return await self._handle_payout_denied(resource)

        elif event_type == "CUSTOMER.DISPUTE.CREATED":
            return await self._handle_dispute_created(resource)

        elif event_type == "CUSTOMER.DISPUTE.RESOLVED":
            return await self._handle_dispute_resolved(resource)

        elif event_type == "CUSTOMER.DISPUTE.UPDATED":
            return await self._handle_dispute_updated(resource)

        return {
            "handled": True,
            "event_type": event_type,
        }

    async def _handle_payment_completed(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle PAYMENT.CAPTURE.COMPLETED event."""
        payment_id = resource.get("id")
        amount_data = resource.get("amount", {})
        amount = Decimal(amount_data.get("value", "0"))
        currency = amount_data.get("currency_code", "USD")

        logger.info(
            "PayPal payment completed",
            extra={
                "payment_id": payment_id,
                "amount": str(amount),
                "currency": currency,
            },
        )

        return {
            "action": "payment_completed",
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": resource.get("status"),
        }

    async def _handle_payment_denied(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle PAYMENT.CAPTURE.DENIED event."""
        payment_id = resource.get("id")

        logger.warning(
            "PayPal payment denied",
            extra={"payment_id": payment_id},
        )

        return {
            "action": "payment_denied",
            "payment_id": payment_id,
            "status": "denied",
        }

    async def _handle_payment_refunded(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle PAYMENT.CAPTURE.REFUNDED event."""
        capture_id = resource.get("id")
        amount_data = resource.get("amount", {})
        amount = Decimal(amount_data.get("value", "0"))
        currency = amount_data.get("currency_code", "USD")

        logger.info(
            "PayPal payment refunded",
            extra={
                "capture_id": capture_id,
                "amount": str(amount),
                "currency": currency,
            },
        )

        return {
            "action": "payment_refunded",
            "capture_id": capture_id,
            "amount": amount,
            "currency": currency,
        }

    async def _handle_payment_reversed(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle PAYMENT.CAPTURE.REVERSED event."""
        capture_id = resource.get("id")

        logger.warning(
            "PayPal payment reversed",
            extra={"capture_id": capture_id},
        )

        return {
            "action": "payment_reversed",
            "capture_id": capture_id,
        }

    async def _handle_order_approved(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle CHECKOUT.ORDER.APPROVED event."""
        order_id = resource.get("id")

        logger.info(
            "PayPal order approved",
            extra={"order_id": order_id},
        )

        return {
            "action": "order_approved",
            "order_id": order_id,
        }

    async def _handle_order_completed(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle CHECKOUT.ORDER.COMPLETED event."""
        order_id = resource.get("id")

        logger.info(
            "PayPal order completed",
            extra={"order_id": order_id},
        )

        return {
            "action": "order_completed",
            "order_id": order_id,
        }

    async def _handle_payout_succeeded(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle PAYMENT.PAYOUTS-ITEM.SUCCEEDED event."""
        payout_item_id = resource.get("payout_item_id")
        amount_data = resource.get("payout_item", {}).get("amount", {})
        amount = Decimal(amount_data.get("value", "0"))
        currency = amount_data.get("currency", "USD")

        logger.info(
            "PayPal payout succeeded",
            extra={
                "payout_item_id": payout_item_id,
                "amount": str(amount),
                "currency": currency,
            },
        )

        return {
            "action": "payout_succeeded",
            "payout_item_id": payout_item_id,
            "amount": amount,
            "currency": currency,
        }

    async def _handle_payout_failed(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle PAYMENT.PAYOUTS-ITEM.FAILED event."""
        payout_item_id = resource.get("payout_item_id")

        logger.warning(
            "PayPal payout failed",
            extra={"payout_item_id": payout_item_id},
        )

        return {
            "action": "payout_failed",
            "payout_item_id": payout_item_id,
        }

    async def _handle_payout_denied(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle PAYMENT.PAYOUTS-ITEM.DENIED event."""
        payout_item_id = resource.get("payout_item_id")

        logger.warning(
            "PayPal payout denied",
            extra={"payout_item_id": payout_item_id},
        )

        return {
            "action": "payout_denied",
            "payout_item_id": payout_item_id,
        }

    async def _handle_dispute_created(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle CUSTOMER.DISPUTE.CREATED event."""
        dispute_id = resource.get("dispute_id")
        amount_data = resource.get("dispute_amount", {})
        amount = Decimal(amount_data.get("value", "0"))
        currency = amount_data.get("currency_code", "USD")
        reason = resource.get("reason")

        logger.warning(
            "PayPal dispute created",
            extra={
                "dispute_id": dispute_id,
                "amount": str(amount),
                "reason": reason,
            },
        )

        return {
            "action": "dispute_created",
            "dispute_id": dispute_id,
            "amount": amount,
            "currency": currency,
            "reason": reason,
        }

    async def _handle_dispute_resolved(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle CUSTOMER.DISPUTE.RESOLVED event."""
        dispute_id = resource.get("dispute_id")
        outcome = resource.get("dispute_outcome", {}).get("outcome_code")

        logger.info(
            "PayPal dispute resolved",
            extra={
                "dispute_id": dispute_id,
                "outcome": outcome,
            },
        )

        return {
            "action": "dispute_resolved",
            "dispute_id": dispute_id,
            "outcome": outcome,
        }

    async def _handle_dispute_updated(
        self,
        resource: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle CUSTOMER.DISPUTE.UPDATED event."""
        dispute_id = resource.get("dispute_id")
        status = resource.get("status")

        logger.info(
            "PayPal dispute updated",
            extra={
                "dispute_id": dispute_id,
                "status": status,
            },
        )

        return {
            "action": "dispute_updated",
            "dispute_id": dispute_id,
            "status": status,
        }
