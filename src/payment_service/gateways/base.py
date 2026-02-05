import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    """Base exception for payment gateway errors."""

    def __init__(self, message: str, code: str, **context: Any):
        super().__init__(message)
        self.code = code
        self.context = context


class PaymentError(GatewayError):
    """Payment processing error."""

    pass


class ValidationError(GatewayError):
    """Input validation error."""

    pass


class WebhookError(GatewayError):
    """Webhook processing error."""

    pass


class BaseGateway(ABC):
    """
    Abstract base class for payment gateways.

    Provides common interface for payment processing, webhook handling,
    error management, and response formatting.
    """

    def __init__(self, api_key: str, **config: Any):
        """
        Initialize payment gateway.

        Args:
            api_key: Gateway API key
            **config: Additional gateway configuration
        """
        self.api_key = api_key
        self.config = config
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate gateway configuration."""
        if not self.api_key:
            raise ValidationError(
                "API key is required",
                code="MISSING_API_KEY",
            )

    @abstractmethod
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a payment.

        Args:
            amount: Payment amount
            currency: Currency code (USD, EUR, etc.)
            metadata: Additional payment metadata
            **kwargs: Gateway-specific parameters

        Returns:
            Payment response dict with gateway-specific data

        Raises:
            PaymentError: If payment creation fails
            ValidationError: If input validation fails
        """
        pass

    @abstractmethod
    async def confirm_payment(
        self, payment_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Confirm a payment.

        Args:
            payment_id: Gateway payment identifier
            **kwargs: Gateway-specific parameters

        Returns:
            Confirmation response dict

        Raises:
            PaymentError: If payment confirmation fails
        """
        pass

    @abstractmethod
    async def process_refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Process a refund.

        Args:
            payment_id: Gateway payment identifier
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Gateway-specific parameters

        Returns:
            Refund response dict

        Raises:
            PaymentError: If refund processing fails
        """
        pass

    @abstractmethod
    async def verify_webhook_signature(
        self, payload: bytes, signature: str, **kwargs: Any
    ) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Webhook payload bytes
            signature: Webhook signature to verify
            **kwargs: Gateway-specific parameters

        Returns:
            True if signature is valid

        Raises:
            WebhookError: If signature verification fails
        """
        pass

    @abstractmethod
    async def handle_webhook(
        self, event_type: str, event_data: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        """
        Handle webhook event.

        Args:
            event_type: Event type identifier
            event_data: Event payload data
            **kwargs: Gateway-specific parameters

        Returns:
            Processing result dict

        Raises:
            WebhookError: If webhook handling fails
        """
        pass

    def format_amount(self, amount: Decimal, currency: str) -> int:
        """
        Format amount for gateway API.

        Most gateways use smallest currency unit (cents, etc.).

        Args:
            amount: Decimal amount
            currency: Currency code

        Returns:
            Amount in smallest currency unit
        """
        zero_decimal_currencies = {"JPY", "KRW", "VND"}
        if currency.upper() in zero_decimal_currencies:
            return int(amount)
        return int(amount * 100)

    def parse_amount(self, amount: int, currency: str) -> Decimal:
        """
        Parse amount from gateway API response.

        Args:
            amount: Amount in smallest currency unit
            currency: Currency code

        Returns:
            Decimal amount
        """
        zero_decimal_currencies = {"JPY", "KRW", "VND"}
        if currency.upper() in zero_decimal_currencies:
            return Decimal(amount)
        return Decimal(amount) / Decimal(100)

    def format_response(
        self,
        success: bool,
        data: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Format standardized gateway response.

        Args:
            success: Operation success status
            data: Response data
            error: Error message
            error_code: Error code

        Returns:
            Standardized response dict
        """
        response: dict[str, Any] = {
            "success": success,
            "data": data or {},
        }

        if not success:
            response["error"] = {
                "message": error or "Unknown error",
                "code": error_code or "UNKNOWN_ERROR",
            }

        return response

    def _log_operation(
        self,
        operation: str,
        success: bool,
        **context: Any,
    ) -> None:
        """
        Log gateway operation with context.

        Args:
            operation: Operation name
            success: Operation success status
            **context: Additional context to log
        """
        log_data = {
            "gateway": self.__class__.__name__,
            "operation": operation,
            "success": success,
            **context,
        }

        if success:
            logger.info(
                f"Gateway operation succeeded: {operation}",
                extra=log_data,
            )
        else:
            logger.error(
                f"Gateway operation failed: {operation}",
                extra=log_data,
            )

    def _handle_error(
        self,
        error: Exception,
        operation: str,
        **context: Any,
    ) -> GatewayError:
        """
        Handle and transform gateway errors.

        Args:
            error: Original exception
            operation: Operation that failed
            **context: Additional error context

        Returns:
            Transformed GatewayError
        """
        error_message = str(error)
        error_code = getattr(error, "code", "GATEWAY_ERROR")

        self._log_operation(
            operation=operation,
            success=False,
            error=error_message,
            error_code=error_code,
            **context,
        )

        if isinstance(error, GatewayError):
            return error

        return GatewayError(
            message=error_message,
            code=error_code,
            operation=operation,
            **context,
        )
