import hashlib
import hmac
import json
import logging
import time
from typing import Any, Optional

from src.payment_service.gateways.base import WebhookError

logger = logging.getLogger(__name__)


class StripeWebhookHandler:
    """
    Stripe webhook event handler with signature verification and idempotency.

    Processes webhook events for payment confirmations, refunds, and disputes
    with proper signature verification and duplicate event detection.
    """

    SUPPORTED_EVENTS = {
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "payment_intent.canceled",
        "charge.succeeded",
        "charge.failed",
        "charge.refunded",
        "charge.dispute.created",
        "charge.dispute.updated",
        "charge.dispute.closed",
        "refund.created",
        "refund.updated",
    }

    def __init__(
        self,
        webhook_secret: str,
        tolerance: int = 300,
        idempotency_store: Optional[Any] = None,
    ):
        """
        Initialize Stripe webhook handler.

        Args:
            webhook_secret: Stripe webhook endpoint secret
            tolerance: Maximum age of webhook timestamp in seconds (default: 5 minutes)
            idempotency_store: Optional store for tracking processed events
        """
        if not webhook_secret:
            raise WebhookError(
                "Webhook secret is required",
                code="MISSING_WEBHOOK_SECRET",
            )

        self.webhook_secret = webhook_secret
        self.tolerance = tolerance
        self.idempotency_store = idempotency_store or {}
        self._processed_events = set()

    def verify_signature(
        self,
        payload: bytes,
        signature_header: str,
        timestamp: Optional[int] = None,
    ) -> bool:
        """
        Verify Stripe webhook signature using HMAC SHA256.

        Args:
            payload: Raw webhook payload bytes
            signature_header: Stripe-Signature header value
            timestamp: Optional timestamp override for testing

        Returns:
            True if signature is valid

        Raises:
            WebhookError: If signature verification fails
        """
        try:
            if not signature_header:
                raise WebhookError(
                    "Missing Stripe-Signature header",
                    code="MISSING_SIGNATURE",
                )

            signature_parts = self._parse_signature_header(signature_header)
            event_timestamp = signature_parts.get("t")
            signatures = signature_parts.get("signatures", [])

            if not event_timestamp or not signatures:
                raise WebhookError(
                    "Invalid signature header format",
                    code="INVALID_SIGNATURE_FORMAT",
                    signature_header=signature_header[:50],
                )

            current_timestamp = timestamp or int(time.time())
            timestamp_age = abs(current_timestamp - int(event_timestamp))

            if timestamp_age > self.tolerance:
                raise WebhookError(
                    "Webhook timestamp is outside the tolerance window",
                    code="TIMESTAMP_OUT_OF_RANGE",
                    timestamp=event_timestamp,
                    current_time=current_timestamp,
                    age=timestamp_age,
                    tolerance=self.tolerance,
                )

            signed_payload = f"{event_timestamp}.{payload.decode('utf-8')}"
            expected_signature = self._compute_signature(signed_payload)

            signature_valid = any(
                self._secure_compare(expected_signature, sig) for sig in signatures
            )

            if not signature_valid:
                logger.error(
                    "Webhook signature verification failed",
                    extra={
                        "timestamp": event_timestamp,
                        "expected_prefix": expected_signature[:10],
                        "provided_signatures": [sig[:10] for sig in signatures],
                    },
                )
                raise WebhookError(
                    "Webhook signature verification failed",
                    code="SIGNATURE_MISMATCH",
                )

            logger.info(
                "Webhook signature verified successfully",
                extra={
                    "timestamp": event_timestamp,
                    "age_seconds": timestamp_age,
                },
            )

            return True

        except WebhookError:
            raise
        except Exception as e:
            logger.exception("Error during webhook signature verification")
            raise WebhookError(
                f"Signature verification error: {str(e)}",
                code="VERIFICATION_ERROR",
                original_error=str(e),
            )

    def _parse_signature_header(self, signature_header: str) -> dict[str, Any]:
        """
        Parse Stripe-Signature header.

        Args:
            signature_header: Raw signature header value

        Returns:
            Dict with timestamp and signature list
        """
        parts = {}
        for item in signature_header.split(","):
            key_value = item.strip().split("=", 1)
            if len(key_value) == 2:
                key, value = key_value
                if key == "t":
                    parts["t"] = value
                elif key.startswith("v1"):
                    if "signatures" not in parts:
                        parts["signatures"] = []
                    parts["signatures"].append(value)

        return parts

    def _compute_signature(self, signed_payload: str) -> str:
        """
        Compute HMAC SHA256 signature.

        Args:
            signed_payload: Payload to sign

        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

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
            event_id: Stripe event ID

        Returns:
            True if event is new, False if already processed
        """
        if event_id in self._processed_events:
            logger.warning(
                "Duplicate webhook event detected",
                extra={"event_id": event_id},
            )
            return False

        if hasattr(self.idempotency_store, "get") and self.idempotency_store.get(event_id):
            logger.warning(
                "Event found in idempotency store",
                extra={"event_id": event_id},
            )
            return False

        return True

    def mark_processed(self, event_id: str) -> None:
        """
        Mark event as processed for idempotency.

        Args:
            event_id: Stripe event ID
        """
        self._processed_events.add(event_id)

        if hasattr(self.idempotency_store, "set"):
            try:
                self.idempotency_store.set(
                    event_id,
                    int(time.time()),
                    ex=86400,
                )
            except Exception as e:
                logger.error(
                    "Failed to store event in idempotency store",
                    extra={"event_id": event_id, "error": str(e)},
                )

    async def process_event(
        self,
        payload: bytes,
        signature_header: str,
    ) -> dict[str, Any]:
        """
        Process Stripe webhook event with signature verification and idempotency.

        Args:
            payload: Raw webhook payload bytes
            signature_header: Stripe-Signature header value

        Returns:
            Processing result dict

        Raises:
            WebhookError: If event processing fails
        """
        try:
            self.verify_signature(payload, signature_header)

            event_data = json.loads(payload.decode("utf-8"))
            event_id = event_data.get("id")
            event_type = event_data.get("type")
            event_object = event_data.get("data", {}).get("object", {})

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
                "Processing webhook event",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                },
            )

            result = await self._handle_event(event_type, event_object, event_data)

            self.mark_processed(event_id)

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
            logger.exception("Error processing webhook event")
            raise WebhookError(
                f"Event processing error: {str(e)}",
                code="PROCESSING_ERROR",
                original_error=str(e),
            )

    async def _handle_event(
        self,
        event_type: str,
        event_object: dict[str, Any],
        full_event: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle specific webhook event type.

        Args:
            event_type: Stripe event type
            event_object: Event object data
            full_event: Full event payload

        Returns:
            Event handling result
        """
        if event_type not in self.SUPPORTED_EVENTS:
            logger.warning(
                "Unsupported webhook event type",
                extra={"event_type": event_type},
            )
            return {
                "handled": False,
                "reason": "unsupported_event_type",
            }

        if event_type == "payment_intent.succeeded":
            return await self._handle_payment_succeeded(event_object)

        elif event_type == "payment_intent.payment_failed":
            return await self._handle_payment_failed(event_object)

        elif event_type == "payment_intent.canceled":
            return await self._handle_payment_canceled(event_object)

        elif event_type == "charge.refunded":
            return await self._handle_charge_refunded(event_object)

        elif event_type == "charge.dispute.created":
            return await self._handle_dispute_created(event_object)

        elif event_type == "charge.dispute.updated":
            return await self._handle_dispute_updated(event_object)

        elif event_type == "charge.dispute.closed":
            return await self._handle_dispute_closed(event_object)

        return {
            "handled": True,
            "event_type": event_type,
        }

    async def _handle_payment_succeeded(
        self,
        payment_intent: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle payment_intent.succeeded event.

        Args:
            payment_intent: Payment Intent object

        Returns:
            Processing result
        """
        payment_id = payment_intent.get("id")
        amount = payment_intent.get("amount", 0)
        currency = payment_intent.get("currency", "usd")

        logger.info(
            "Payment succeeded",
            extra={
                "payment_id": payment_id,
                "amount": amount,
                "currency": currency,
            },
        )

        return {
            "action": "payment_succeeded",
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": payment_intent.get("status"),
            "metadata": payment_intent.get("metadata", {}),
        }

    async def _handle_payment_failed(
        self,
        payment_intent: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle payment_intent.payment_failed event.

        Args:
            payment_intent: Payment Intent object

        Returns:
            Processing result
        """
        payment_id = payment_intent.get("id")
        last_error = payment_intent.get("last_payment_error", {})

        logger.warning(
            "Payment failed",
            extra={
                "payment_id": payment_id,
                "error_code": last_error.get("code"),
                "error_message": last_error.get("message"),
            },
        )

        return {
            "action": "payment_failed",
            "payment_id": payment_id,
            "error_code": last_error.get("code"),
            "error_message": last_error.get("message"),
            "decline_code": last_error.get("decline_code"),
        }

    async def _handle_payment_canceled(
        self,
        payment_intent: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle payment_intent.canceled event.

        Args:
            payment_intent: Payment Intent object

        Returns:
            Processing result
        """
        payment_id = payment_intent.get("id")
        cancellation_reason = payment_intent.get("cancellation_reason")

        logger.info(
            "Payment canceled",
            extra={
                "payment_id": payment_id,
                "reason": cancellation_reason,
            },
        )

        return {
            "action": "payment_canceled",
            "payment_id": payment_id,
            "cancellation_reason": cancellation_reason,
        }

    async def _handle_charge_refunded(
        self,
        charge: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle charge.refunded event.

        Args:
            charge: Charge object

        Returns:
            Processing result
        """
        charge_id = charge.get("id")
        payment_intent_id = charge.get("payment_intent")
        amount_refunded = charge.get("amount_refunded", 0)
        currency = charge.get("currency", "usd")

        logger.info(
            "Charge refunded",
            extra={
                "charge_id": charge_id,
                "payment_intent_id": payment_intent_id,
                "amount_refunded": amount_refunded,
                "currency": currency,
            },
        )

        return {
            "action": "charge_refunded",
            "charge_id": charge_id,
            "payment_intent_id": payment_intent_id,
            "amount_refunded": amount_refunded,
            "currency": currency,
            "refunded": charge.get("refunded", False),
        }

    async def _handle_dispute_created(
        self,
        dispute: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle charge.dispute.created event.

        Args:
            dispute: Dispute object

        Returns:
            Processing result
        """
        dispute_id = dispute.get("id")
        charge_id = dispute.get("charge")
        amount = dispute.get("amount", 0)
        currency = dispute.get("currency", "usd")
        reason = dispute.get("reason")

        logger.warning(
            "Dispute created",
            extra={
                "dispute_id": dispute_id,
                "charge_id": charge_id,
                "amount": amount,
                "reason": reason,
            },
        )

        return {
            "action": "dispute_created",
            "dispute_id": dispute_id,
            "charge_id": charge_id,
            "amount": amount,
            "currency": currency,
            "reason": reason,
            "status": dispute.get("status"),
            "evidence_details": dispute.get("evidence_details", {}),
        }

    async def _handle_dispute_updated(
        self,
        dispute: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle charge.dispute.updated event.

        Args:
            dispute: Dispute object

        Returns:
            Processing result
        """
        dispute_id = dispute.get("id")
        status = dispute.get("status")

        logger.info(
            "Dispute updated",
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

    async def _handle_dispute_closed(
        self,
        dispute: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle charge.dispute.closed event.

        Args:
            dispute: Dispute object

        Returns:
            Processing result
        """
        dispute_id = dispute.get("id")
        status = dispute.get("status")

        logger.info(
            "Dispute closed",
            extra={
                "dispute_id": dispute_id,
                "status": status,
            },
        )

        return {
            "action": "dispute_closed",
            "dispute_id": dispute_id,
            "status": status,
        }
