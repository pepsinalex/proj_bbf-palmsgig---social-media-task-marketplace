"""
Transaction Management API Endpoints.

Provides comprehensive REST API for transaction CRUD operations with proper
authentication, validation, pagination, and error handling.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import get_current_user_id, get_database_session
from src.payment_service.models.transaction import TransactionStatus, TransactionType
from src.payment_service.schemas.transaction import (
    TransactionCreate,
    TransactionList,
    TransactionResponse,
    TransactionUpdate,
)
from src.payment_service.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def get_transaction_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TransactionService:
    """
    Dependency to get TransactionService instance.

    Args:
        session: Database session from dependency

    Returns:
        TransactionService instance
    """
    return TransactionService(session)


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new transaction",
    description="Create a new transaction with automatic reference generation",
)
async def create_transaction(
    transaction_data: TransactionCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """
    Create a new transaction.

    - **wallet_id**: Wallet ID (UUID format)
    - **type**: Transaction type (deposit, withdrawal, transfer, payment, refund)
    - **amount**: Transaction amount (must be positive, max 4 decimals)
    - **currency**: Currency code (USD, NGN, GHS)
    - **reference**: Optional unique reference (auto-generated if not provided)
    - **gateway_reference**: Optional external gateway reference
    - **metadata**: Optional additional data (JSON)
    - **description**: Optional description

    Returns:
        Created transaction with pending status
    """
    logger.info(
        "Creating transaction",
        extra={
            "user_id": user_id,
            "wallet_id": transaction_data.wallet_id,
            "type": transaction_data.type.value,
            "amount": str(transaction_data.amount),
        },
    )

    try:
        transaction = await service.create_transaction(transaction_data)

        logger.info(
            "Transaction created successfully",
            extra={
                "transaction_id": transaction.id,
                "wallet_id": transaction.wallet_id,
                "reference": transaction.reference,
            },
        )

        return TransactionResponse.model_validate(transaction)

    except ValueError as e:
        logger.warning(
            "Transaction creation validation failed",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Transaction creation failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transaction",
        )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction by ID",
    description="Retrieve transaction details by transaction ID",
)
async def get_transaction(
    transaction_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """
    Get transaction by ID.

    Args:
        transaction_id: Transaction ID (UUID)

    Returns:
        Transaction details
    """
    logger.info(
        "Fetching transaction",
        extra={"transaction_id": transaction_id, "user_id": user_id},
    )

    transaction = await service.get_transaction(transaction_id)
    if not transaction:
        logger.warning(
            "Transaction not found",
            extra={"transaction_id": transaction_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    return TransactionResponse.model_validate(transaction)


@router.get(
    "/reference/{reference}",
    response_model=TransactionResponse,
    summary="Get transaction by reference",
    description="Retrieve transaction details by unique reference",
)
async def get_transaction_by_reference(
    reference: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """
    Get transaction by reference.

    Args:
        reference: Transaction reference

    Returns:
        Transaction details
    """
    logger.info(
        "Fetching transaction by reference",
        extra={"reference": reference, "user_id": user_id},
    )

    transaction = await service.get_transaction_by_reference(reference)
    if not transaction:
        logger.warning(
            "Transaction not found by reference",
            extra={"reference": reference},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with reference {reference} not found",
        )

    return TransactionResponse.model_validate(transaction)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update transaction",
    description="Update transaction status and metadata",
)
async def update_transaction(
    transaction_id: str,
    transaction_data: TransactionUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """
    Update transaction.

    Args:
        transaction_id: Transaction ID (UUID)
        transaction_data: Updated transaction data

    Returns:
        Updated transaction details
    """
    logger.info(
        "Updating transaction",
        extra={"transaction_id": transaction_id, "user_id": user_id},
    )

    try:
        transaction = await service.update_transaction(transaction_id, transaction_data)
        if not transaction:
            logger.warning(
                "Transaction not found for update",
                extra={"transaction_id": transaction_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        logger.info(
            "Transaction updated successfully",
            extra={"transaction_id": transaction_id},
        )

        return TransactionResponse.model_validate(transaction)

    except ValueError as e:
        logger.warning(
            "Transaction update validation failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Transaction update failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transaction",
        )


@router.get(
    "",
    response_model=TransactionList,
    summary="List transactions with filtering and pagination",
    description="Get a paginated list of transactions with optional filtering",
)
async def list_transactions(
    service: Annotated[TransactionService, Depends(get_transaction_service)],
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Items per page (max 100)")
    ] = 20,
    wallet_id: Annotated[
        str | None, Query(description="Filter by wallet ID")
    ] = None,
    transaction_type: Annotated[
        TransactionType | None, Query(description="Filter by transaction type")
    ] = None,
    status: Annotated[
        TransactionStatus | None, Query(description="Filter by status")
    ] = None,
) -> TransactionList:
    """
    List transactions with pagination and filtering.

    Query parameters:
    - **page**: Page number (1-indexed, default: 1)
    - **page_size**: Items per page (1-100, default: 20)
    - **wallet_id**: Filter by wallet ID (UUID)
    - **transaction_type**: Filter by type (deposit, withdrawal, etc.)
    - **status**: Filter by status (pending, completed, etc.)

    Returns:
        Paginated list of transactions with metadata
    """
    logger.info(
        "Listing transactions",
        extra={
            "user_id": user_id,
            "page": page,
            "page_size": page_size,
            "wallet_id": wallet_id,
            "transaction_type": transaction_type.value if transaction_type else None,
            "status": status.value if status else None,
        },
    )

    try:
        result = await service.list_transactions(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            status=status,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "Transactions listed successfully",
            extra={
                "total": result.total,
                "page": page,
                "returned": len(result.transactions),
            },
        )

        return result

    except Exception as e:
        logger.error(
            "Transaction listing failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list transactions",
        )


@router.get(
    "/wallet/{wallet_id}",
    response_model=TransactionList,
    summary="Get wallet transactions",
    description="Get all transactions for a specific wallet with pagination",
)
async def get_wallet_transactions(
    wallet_id: str,
    service: Annotated[TransactionService, Depends(get_transaction_service)],
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Items per page (max 100)")
    ] = 20,
) -> TransactionList:
    """
    Get wallet transactions.

    Args:
        wallet_id: Wallet ID (UUID)
        page: Page number (1-indexed, default: 1)
        page_size: Items per page (1-100, default: 20)

    Returns:
        Paginated list of wallet transactions
    """
    logger.info(
        "Fetching wallet transactions",
        extra={
            "wallet_id": wallet_id,
            "user_id": user_id,
            "page": page,
            "page_size": page_size,
        },
    )

    try:
        result = await service.get_wallet_transactions(
            wallet_id=wallet_id,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "Wallet transactions retrieved successfully",
            extra={
                "wallet_id": wallet_id,
                "total": result.total,
                "returned": len(result.transactions),
            },
        )

        return result

    except Exception as e:
        logger.error(
            "Wallet transactions retrieval failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve wallet transactions",
        )


@router.post(
    "/{transaction_id}/mark-processing",
    response_model=TransactionResponse,
    summary="Mark transaction as processing",
    description="Update transaction status to processing",
)
async def mark_transaction_as_processing(
    transaction_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """
    Mark transaction as processing.

    Args:
        transaction_id: Transaction ID (UUID)

    Returns:
        Updated transaction details
    """
    logger.info(
        "Marking transaction as processing",
        extra={"transaction_id": transaction_id, "user_id": user_id},
    )

    try:
        transaction = await service.mark_as_processing(transaction_id)
        if not transaction:
            logger.warning(
                "Transaction not found",
                extra={"transaction_id": transaction_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        logger.info(
            "Transaction marked as processing",
            extra={"transaction_id": transaction_id},
        )

        return TransactionResponse.model_validate(transaction)

    except ValueError as e:
        logger.warning(
            "Mark as processing validation failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Mark as processing failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark transaction as processing",
        )


@router.post(
    "/{transaction_id}/mark-completed",
    response_model=TransactionResponse,
    summary="Mark transaction as completed",
    description="Update transaction status to completed",
)
async def mark_transaction_as_completed(
    transaction_id: str,
    gateway_reference: Annotated[
        str | None, Query(description="Optional gateway reference")
    ] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[TransactionService, Depends(get_transaction_service)] = None,
) -> TransactionResponse:
    """
    Mark transaction as completed.

    Args:
        transaction_id: Transaction ID (UUID)
        gateway_reference: Optional external gateway reference

    Returns:
        Updated transaction details
    """
    logger.info(
        "Marking transaction as completed",
        extra={
            "transaction_id": transaction_id,
            "gateway_reference": gateway_reference,
            "user_id": user_id,
        },
    )

    try:
        transaction = await service.mark_as_completed(transaction_id, gateway_reference)
        if not transaction:
            logger.warning(
                "Transaction not found",
                extra={"transaction_id": transaction_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        logger.info(
            "Transaction marked as completed",
            extra={"transaction_id": transaction_id},
        )

        return TransactionResponse.model_validate(transaction)

    except ValueError as e:
        logger.warning(
            "Mark as completed validation failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Mark as completed failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark transaction as completed",
        )


@router.post(
    "/{transaction_id}/mark-failed",
    response_model=TransactionResponse,
    summary="Mark transaction as failed",
    description="Update transaction status to failed",
)
async def mark_transaction_as_failed(
    transaction_id: str,
    error_message: Annotated[
        str | None, Query(description="Optional error message")
    ] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[TransactionService, Depends(get_transaction_service)] = None,
) -> TransactionResponse:
    """
    Mark transaction as failed.

    Args:
        transaction_id: Transaction ID (UUID)
        error_message: Optional error description

    Returns:
        Updated transaction details
    """
    logger.error(
        "Marking transaction as failed",
        extra={
            "transaction_id": transaction_id,
            "error_message": error_message,
            "user_id": user_id,
        },
    )

    try:
        transaction = await service.mark_as_failed(transaction_id, error_message)
        if not transaction:
            logger.warning(
                "Transaction not found",
                extra={"transaction_id": transaction_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        logger.error(
            "Transaction marked as failed",
            extra={"transaction_id": transaction_id},
        )

        return TransactionResponse.model_validate(transaction)

    except ValueError as e:
        logger.warning(
            "Mark as failed validation failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Mark as failed operation failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark transaction as failed",
        )


@router.post(
    "/{transaction_id}/cancel",
    response_model=TransactionResponse,
    summary="Cancel transaction",
    description="Cancel a pending transaction",
)
async def cancel_transaction(
    transaction_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """
    Cancel transaction.

    Args:
        transaction_id: Transaction ID (UUID)

    Returns:
        Updated transaction details
    """
    logger.info(
        "Cancelling transaction",
        extra={"transaction_id": transaction_id, "user_id": user_id},
    )

    try:
        transaction = await service.cancel_transaction(transaction_id)
        if not transaction:
            logger.warning(
                "Transaction not found",
                extra={"transaction_id": transaction_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        logger.info(
            "Transaction cancelled successfully",
            extra={"transaction_id": transaction_id},
        )

        return TransactionResponse.model_validate(transaction)

    except ValueError as e:
        logger.warning(
            "Cancel transaction validation failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Cancel transaction failed",
            extra={"transaction_id": transaction_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel transaction",
        )
