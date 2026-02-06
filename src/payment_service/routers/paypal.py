"""
PayPal Payment Router.

This module provides FastAPI endpoints for PayPal payment processing including
deposit creation, withdrawal processing, webhook event handling, and OAuth integration.
"""

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.gateways.paypal.client import PayPalGateway
from src.payment_service.gateways.paypal.webhook import PayPalWebhookHandler
from src.payment_service.models.transaction import Transaction, TransactionStatus, TransactionType
from src.payment_service.models.wallet import Wallet
from src.payment_service.schemas.paypal import (
    PayPalDepositRequest,
    PayPalPaymentResponse,
    PayPalWithdrawRequest,
)
from src.payment_service.services.transaction_service import TransactionService
from src.payment_service.services.wallet_service import WalletService
from src.shared.config import get_settings
from src.shared.database import get_db_session

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/payments/paypal",
    tags=["PayPal Payments"],
)


def get_paypal_gateway() -> PayPalGateway:
    """
    Get PayPal gateway instance.

    Returns:
        PayPalGateway: Configured PayPal gateway

    Raises:
        HTTPException: If PayPal is not configured
    """
    paypal_client_id = (
        settings.PAYPAL_CLIENT_ID if hasattr(settings, "PAYPAL_CLIENT_ID") else None
    )
    paypal_client_secret = (
        settings.PAYPAL_CLIENT_SECRET if hasattr(settings, "PAYPAL_CLIENT_SECRET") else None
    )
    paypal_webhook_id = (
        settings.PAYPAL_WEBHOOK_ID if hasattr(settings, "PAYPAL_WEBHOOK_ID") else None
    )
    paypal_sandbox = (
        settings.PAYPAL_SANDBOX if hasattr(settings, "PAYPAL_SANDBOX") else True
    )

    if not paypal_client_id or not paypal_client_secret:
        logger.error("PayPal credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal payment gateway is not configured",
        )

    try:
        return PayPalGateway(
            api_key=paypal_client_id,
            api_secret=paypal_client_secret,
            webhook_id=paypal_webhook_id,
            sandbox=paypal_sandbox,
        )
    except Exception as e:
        logger.error(
            "Failed to initialize PayPal gateway",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to initialize PayPal gateway",
        )


def get_paypal_webhook_handler() -> PayPalWebhookHandler:
    """
    Get PayPal webhook handler instance.

    Returns:
        PayPalWebhookHandler: Configured webhook handler

    Raises:
        HTTPException: If PayPal webhook ID is not configured
    """
    webhook_id = (
        settings.PAYPAL_WEBHOOK_ID if hasattr(settings, "PAYPAL_WEBHOOK_ID") else None
    )

    if not webhook_id:
        logger.error("PayPal webhook ID not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal webhook handler is not configured",
        )

    try:
        return PayPalWebhookHandler(webhook_id=webhook_id)
    except Exception as e:
        logger.error(
            "Failed to initialize PayPal webhook handler",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to initialize PayPal webhook handler",
        )


@router.post(
    "/deposit",
    response_model=PayPalPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create PayPal deposit",
    description="Create a PayPal order for depositing funds into wallet",
)
async def create_paypal_deposit(
    request: PayPalDepositRequest,
    db: AsyncSession = Depends(get_db_session),
    paypal_gateway: PayPalGateway = Depends(get_paypal_gateway),
) -> PayPalPaymentResponse:
    """
    Create a PayPal deposit order.

    Args:
        request: Deposit request with wallet_id, amount, and currency
        db: Database session
        paypal_gateway: PayPal gateway instance

    Returns:
        PayPal payment response with approval URL

    Raises:
        HTTPException: If wallet not found or payment creation fails
    """
    try:
        wallet_service = WalletService(db)
        transaction_service = TransactionService(db)

        wallet = await wallet_service.get_wallet(request.wallet_id)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {request.wallet_id} not found",
            )

        metadata = request.metadata or {}
        metadata["wallet_id"] = request.wallet_id

        payment_result = await paypal_gateway.create_payment(
            amount=request.amount,
            currency=request.currency,
            metadata=metadata,
            description=request.description or "Wallet deposit",
            return_url=request.return_url,
            cancel_url=request.cancel_url,
        )

        if not payment_result.get("success"):
            error_info = payment_result.get("error", {})
            logger.error(
                "PayPal payment creation failed",
                extra={
                    "wallet_id": request.wallet_id,
                    "amount": str(request.amount),
                    "error": error_info,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_info.get("message", "Failed to create PayPal order"),
            )

        payment_data = payment_result.get("data", {})
        payment_id = payment_data.get("payment_id")

        txn_metadata = {
            "gateway": "paypal",
            "payment_id": payment_id,
            "approval_url": payment_data.get("approval_url"),
            **metadata,
        }

        transaction = await transaction_service.create_transaction(
            wallet_id=request.wallet_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=request.amount,
            currency=request.currency,
            status=TransactionStatus.PENDING,
            gateway_reference=payment_id,
            metadata=txn_metadata,
        )

        logger.info(
            "PayPal deposit order created",
            extra={
                "wallet_id": request.wallet_id,
                "amount": str(request.amount),
                "payment_id": payment_id,
                "transaction_id": str(transaction.id),
            },
        )

        return PayPalPaymentResponse(
            success=True,
            payment_id=payment_id,
            approval_url=payment_data.get("approval_url"),
            status=payment_data.get("status"),
            amount=request.amount,
            currency=request.currency,
            transaction_id=str(transaction.id),
            metadata=payment_data.get("metadata", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error creating PayPal deposit",
            extra={
                "wallet_id": request.wallet_id,
                "amount": str(request.amount),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create PayPal deposit",
        )


@router.post(
    "/webhooks",
    status_code=status.HTTP_200_OK,
    summary="Handle PayPal webhook",
    description="Process PayPal IPN webhook events",
)
async def handle_paypal_webhook(
    request: Request,
    paypal_transmission_id: str = Header(None, alias="paypal-transmission-id"),
    paypal_transmission_time: str = Header(None, alias="paypal-transmission-time"),
    paypal_cert_url: str = Header(None, alias="paypal-cert-url"),
    paypal_auth_algo: str = Header(None, alias="paypal-auth-algo"),
    paypal_transmission_sig: str = Header(None, alias="paypal-transmission-sig"),
    db: AsyncSession = Depends(get_db_session),
    webhook_handler: PayPalWebhookHandler = Depends(get_paypal_webhook_handler),
) -> JSONResponse:
    """
    Handle PayPal webhook events.

    Args:
        request: FastAPI request object
        paypal_transmission_id: PayPal transmission ID header
        paypal_transmission_time: PayPal transmission time header
        paypal_cert_url: PayPal certificate URL header
        paypal_auth_algo: PayPal auth algorithm header
        paypal_transmission_sig: PayPal transmission signature header
        db: Database session
        webhook_handler: PayPal webhook handler

    Returns:
        JSON response with processing status

    Raises:
        HTTPException: If webhook processing fails
    """
    try:
        payload = await request.body()

        headers = {
            "paypal-transmission-id": paypal_transmission_id or "",
            "paypal-transmission-time": paypal_transmission_time or "",
            "paypal-cert-url": paypal_cert_url or "",
            "paypal-auth-algo": paypal_auth_algo or "",
            "paypal-transmission-sig": paypal_transmission_sig or "",
        }

        event_result = await webhook_handler.process_event(
            payload=payload,
            headers=headers,
        )

        if not event_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook verification failed",
            )

        event_id = event_result.get("event_id")
        event_type = event_result.get("event_type")
        processed = event_result.get("processed", False)

        if not processed:
            logger.info(
                "Duplicate PayPal webhook event",
                extra={"event_id": event_id, "event_type": event_type},
            )
            return JSONResponse(
                content={
                    "status": "ok",
                    "message": "Duplicate event",
                    "event_id": event_id,
                }
            )

        result = event_result.get("result", {})
        action = result.get("action")

        wallet_service = WalletService(db)
        transaction_service = TransactionService(db)

        if action == "payment_completed":
            payment_id = result.get("payment_id")
            amount = result.get("amount", Decimal("0"))
            currency = result.get("currency", "USD")

            transactions = await transaction_service.list_transactions(
                gateway_reference=payment_id,
                transaction_type=TransactionType.DEPOSIT,
            )

            if transactions.get("transactions"):
                transaction = transactions["transactions"][0]
                wallet_id = transaction.get("wallet_id")

                await wallet_service.add_balance(wallet_id, amount)
                await transaction_service.mark_as_completed(str(transaction.get("id")))

                logger.info(
                    "PayPal payment completed",
                    extra={
                        "payment_id": payment_id,
                        "wallet_id": wallet_id,
                        "amount": str(amount),
                    },
                )

        elif action == "payment_denied":
            payment_id = result.get("payment_id")

            transactions = await transaction_service.list_transactions(
                gateway_reference=payment_id,
                transaction_type=TransactionType.DEPOSIT,
            )

            if transactions.get("transactions"):
                transaction = transactions["transactions"][0]
                await transaction_service.mark_as_failed(str(transaction.get("id")))

                logger.warning(
                    "PayPal payment denied",
                    extra={"payment_id": payment_id},
                )

        logger.info(
            "PayPal webhook processed",
            extra={
                "event_id": event_id,
                "event_type": event_type,
                "action": action,
            },
        )

        return JSONResponse(
            content={
                "status": "ok",
                "message": "Webhook processed successfully",
                "event_id": event_id,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error processing PayPal webhook",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )
