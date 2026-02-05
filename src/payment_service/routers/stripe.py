"""
Stripe Payment Router.

This module provides FastAPI endpoints for Stripe payment processing including
deposit creation, webhook event handling, and payment confirmation.
"""

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.gateways.stripe.client import StripeGateway
from src.payment_service.gateways.stripe.webhook import StripeWebhookHandler
from src.payment_service.models.transaction import Transaction, TransactionStatus, TransactionType
from src.payment_service.models.wallet import Wallet
from src.payment_service.schemas.stripe import (
    StripeDepositRequest,
    StripePaymentResponse,
)
from src.payment_service.services.transaction_service import TransactionService
from src.payment_service.services.wallet_service import WalletService
from src.shared.config import get_settings
from src.shared.database import get_db_session

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/payments/stripe",
    tags=["Stripe Payments"],
)


def get_stripe_gateway() -> StripeGateway:
    """
    Get Stripe gateway instance.

    Returns:
        StripeGateway: Configured Stripe gateway

    Raises:
        HTTPException: If Stripe is not configured
    """
    stripe_api_key = settings.STRIPE_SECRET_KEY if hasattr(settings, "STRIPE_SECRET_KEY") else None
    stripe_webhook_secret = settings.STRIPE_WEBHOOK_SECRET if hasattr(settings, "STRIPE_WEBHOOK_SECRET") else None

    if not stripe_api_key:
        logger.error("Stripe API key not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe payment gateway is not configured",
        )

    try:
        return StripeGateway(
            api_key=stripe_api_key,
            webhook_secret=stripe_webhook_secret,
        )
    except Exception as e:
        logger.error(
            "Failed to initialize Stripe gateway",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to initialize Stripe gateway",
        )


def get_stripe_webhook_handler() -> StripeWebhookHandler:
    """
    Get Stripe webhook handler instance.

    Returns:
        StripeWebhookHandler: Configured webhook handler

    Raises:
        HTTPException: If Stripe webhook secret is not configured
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET if hasattr(settings, "STRIPE_WEBHOOK_SECRET") else None

    if not webhook_secret:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook handler is not configured",
        )

    try:
        return StripeWebhookHandler(webhook_secret=webhook_secret)
    except Exception as e:
        logger.error(
            "Failed to initialize Stripe webhook handler",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to initialize Stripe webhook handler",
        )


@router.post(
    "/deposit",
    response_model=StripePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Stripe deposit payment",
    description="Create a new Stripe Payment Intent for depositing funds into a wallet",
)
async def create_stripe_deposit(
    request: StripeDepositRequest,
    session: AsyncSession = Depends(get_db_session),
    stripe_gateway: StripeGateway = Depends(get_stripe_gateway),
) -> StripePaymentResponse:
    """
    Create a Stripe Payment Intent for wallet deposit.

    This endpoint creates a Payment Intent with Stripe and a pending transaction
    in the database. The client must complete payment confirmation using the
    returned client_secret.

    Args:
        request: Deposit request parameters
        session: Database session
        stripe_gateway: Stripe gateway instance

    Returns:
        Payment response with client secret for confirmation

    Raises:
        HTTPException: If wallet not found or payment creation fails
    """
    try:
        wallet_service = WalletService(session)
        transaction_service = TransactionService(session)

        logger.info(
            "Processing Stripe deposit request",
            extra={
                "wallet_id": request.wallet_id,
                "amount": str(request.amount),
                "currency": request.currency,
            },
        )

        wallet = await wallet_service.get_wallet(request.wallet_id)
        if not wallet:
            logger.warning(
                "Wallet not found for deposit",
                extra={"wallet_id": request.wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {request.wallet_id} not found",
            )

        if not wallet.can_transact():
            logger.warning(
                "Wallet cannot accept deposits",
                extra={
                    "wallet_id": request.wallet_id,
                    "wallet_status": wallet.status.value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet is not active and cannot accept deposits",
            )

        payment_metadata = {
            "wallet_id": request.wallet_id,
            "user_id": str(wallet.user_id),
            "service": "palmsgig",
            "transaction_type": "deposit",
        }

        if request.metadata:
            payment_metadata.update(request.metadata)

        payment_result = await stripe_gateway.create_payment(
            amount=request.amount,
            currency=request.currency,
            metadata=payment_metadata,
            payment_method=request.payment_method,
            description=request.description or f"Deposit to wallet {request.wallet_id}",
            confirm=request.confirm,
        )

        if not payment_result.get("success"):
            error_info = payment_result.get("error", {})
            logger.error(
                "Stripe payment creation failed",
                extra={
                    "wallet_id": request.wallet_id,
                    "error": error_info.get("message"),
                    "error_code": error_info.get("code"),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_info.get("message", "Payment creation failed"),
            )

        payment_data = payment_result.get("data", {})
        payment_id = payment_data.get("payment_id")
        payment_status = payment_data.get("status")

        transaction = await transaction_service.create_transaction(
            wallet_id=request.wallet_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=request.amount,
            currency=request.currency,
            description=request.description or f"Stripe deposit - {payment_id}",
            metadata={
                "payment_gateway": "stripe",
                "payment_id": payment_id,
                "payment_status": payment_status,
                **(request.metadata or {}),
            },
        )

        logger.info(
            "Stripe deposit payment created successfully",
            extra={
                "transaction_id": str(transaction.id),
                "payment_id": payment_id,
                "wallet_id": request.wallet_id,
                "amount": str(request.amount),
                "status": payment_status,
            },
        )

        return StripePaymentResponse(
            success=True,
            payment_id=payment_id,
            client_secret=payment_data.get("client_secret"),
            status=payment_status,
            amount=request.amount,
            currency=request.currency.upper(),
            transaction_id=str(transaction.id),
            metadata=payment_data.get("metadata", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error creating Stripe deposit",
            extra={
                "wallet_id": request.wallet_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment",
        )
    finally:
        await stripe_gateway.close()


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Handle Stripe webhook events",
    description="Process Stripe webhook events for payment confirmations, refunds, and disputes",
)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    session: AsyncSession = Depends(get_db_session),
    webhook_handler: StripeWebhookHandler = Depends(get_stripe_webhook_handler),
) -> JSONResponse:
    """
    Handle Stripe webhook events.

    Processes webhook events from Stripe including payment confirmations,
    failures, refunds, and disputes. Updates transaction status accordingly.

    Args:
        request: FastAPI request containing webhook payload
        stripe_signature: Stripe signature header for verification
        session: Database session
        webhook_handler: Stripe webhook handler instance

    Returns:
        JSON response confirming event receipt

    Raises:
        HTTPException: If signature verification fails or event processing fails
    """
    try:
        payload = await request.body()

        logger.info(
            "Received Stripe webhook",
            extra={
                "signature_present": bool(stripe_signature),
                "payload_size": len(payload),
            },
        )

        event_result = await webhook_handler.process_event(
            payload=payload,
            signature_header=stripe_signature,
        )

        if not event_result.get("success"):
            logger.error(
                "Webhook event processing failed",
                extra={"result": event_result},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event processing failed",
            )

        event_id = event_result.get("event_id")
        event_type = event_result.get("event_type")
        processed = event_result.get("processed", False)

        if not processed:
            logger.info(
                "Webhook event skipped (duplicate or unsupported)",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "reason": event_result.get("reason"),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"received": True, "processed": False},
            )

        event_data = event_result.get("result", {})
        action = event_data.get("action")

        transaction_service = TransactionService(session)

        if action == "payment_succeeded":
            payment_id = event_data.get("payment_id")
            metadata = event_data.get("metadata", {})
            wallet_id = metadata.get("wallet_id")

            if wallet_id:
                wallet_service = WalletService(session)

                transactions = await transaction_service.list_transactions(
                    wallet_id=wallet_id,
                    transaction_type=TransactionType.DEPOSIT,
                )

                matching_transaction = None
                for txn in transactions.get("transactions", []):
                    txn_metadata = txn.get("metadata", {})
                    if txn_metadata.get("payment_id") == payment_id:
                        matching_transaction = txn
                        break

                if matching_transaction:
                    transaction_id = matching_transaction["id"]
                    await transaction_service.mark_as_completed(transaction_id)

                    amount = Decimal(str(event_data.get("amount", 0)))
                    currency = event_data.get("currency", "usd")

                    await wallet_service.add_balance(wallet_id, amount)

                    logger.info(
                        "Payment succeeded - wallet updated",
                        extra={
                            "payment_id": payment_id,
                            "wallet_id": wallet_id,
                            "transaction_id": transaction_id,
                            "amount": str(amount),
                        },
                    )
                else:
                    logger.warning(
                        "No matching transaction found for payment",
                        extra={"payment_id": payment_id, "wallet_id": wallet_id},
                    )
            else:
                logger.warning(
                    "Payment succeeded but no wallet_id in metadata",
                    extra={"payment_id": payment_id},
                )

        elif action == "payment_failed":
            payment_id = event_data.get("payment_id")

            transactions = await transaction_service.list_transactions(
                transaction_type=TransactionType.DEPOSIT,
            )

            for txn in transactions.get("transactions", []):
                txn_metadata = txn.get("metadata", {})
                if txn_metadata.get("payment_id") == payment_id:
                    await transaction_service.mark_as_failed(txn["id"])
                    logger.info(
                        "Payment failed - transaction marked as failed",
                        extra={"payment_id": payment_id, "transaction_id": txn["id"]},
                    )
                    break

        elif action == "charge_refunded":
            payment_intent_id = event_data.get("payment_intent_id")
            amount_refunded = event_data.get("amount_refunded", 0)

            logger.info(
                "Charge refunded",
                extra={
                    "payment_intent_id": payment_intent_id,
                    "amount_refunded": amount_refunded,
                },
            )

        elif action == "dispute_created":
            dispute_id = event_data.get("dispute_id")
            charge_id = event_data.get("charge_id")

            logger.warning(
                "Dispute created",
                extra={
                    "dispute_id": dispute_id,
                    "charge_id": charge_id,
                    "amount": event_data.get("amount"),
                    "reason": event_data.get("reason"),
                },
            )

        logger.info(
            "Webhook event processed successfully",
            extra={
                "event_id": event_id,
                "event_type": event_type,
                "action": action,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"received": True, "processed": True},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error processing webhook",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )
