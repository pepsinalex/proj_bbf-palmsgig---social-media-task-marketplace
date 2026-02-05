"""
Wallet Management API Endpoints.

Provides comprehensive REST API for wallet CRUD operations, balance management,
and escrow operations with proper authentication, validation, and error handling.
"""

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import get_current_user_id, get_database_session
from src.payment_service.schemas.wallet import (
    WalletBalance,
    WalletCreate,
    WalletResponse,
    WalletUpdate,
)
from src.payment_service.services.wallet_service import WalletService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallets", tags=["wallets"])


async def get_wallet_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> WalletService:
    """
    Dependency to get WalletService instance.

    Args:
        session: Database session from dependency

    Returns:
        WalletService instance
    """
    return WalletService(session)


@router.post(
    "",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new wallet",
    description="Create a new wallet for a user with optional initial balance",
)
async def create_wallet(
    wallet_data: WalletCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """
    Create a new wallet.

    - **user_id**: User ID (UUID format)
    - **currency**: Currency code (USD, NGN, GHS)
    - **initial_balance**: Initial balance (default: 0.0000)

    Returns:
        Created wallet with all fields
    """
    logger.info(
        "Creating wallet",
        extra={
            "user_id": wallet_data.user_id,
            "currency": wallet_data.currency.value,
            "initial_balance": str(wallet_data.initial_balance),
        },
    )

    try:
        wallet = await service.create_wallet(wallet_data)

        logger.info(
            "Wallet created successfully",
            extra={"wallet_id": wallet.id, "user_id": wallet.user_id},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Wallet creation validation failed",
            extra={"user_id": wallet_data.user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Wallet creation failed",
            extra={"user_id": wallet_data.user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create wallet",
        )


@router.get(
    "/{wallet_id}",
    response_model=WalletResponse,
    summary="Get wallet by ID",
    description="Retrieve wallet details by wallet ID",
)
async def get_wallet(
    wallet_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """
    Get wallet by ID.

    Args:
        wallet_id: Wallet ID (UUID)

    Returns:
        Wallet details
    """
    logger.info(
        "Fetching wallet",
        extra={"wallet_id": wallet_id, "user_id": user_id},
    )

    wallet = await service.get_wallet(wallet_id)
    if not wallet:
        logger.warning(
            "Wallet not found",
            extra={"wallet_id": wallet_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet {wallet_id} not found",
        )

    return WalletResponse.model_validate(wallet)


@router.get(
    "/user/{user_id}",
    response_model=WalletResponse,
    summary="Get wallet by user ID",
    description="Retrieve wallet details by user ID",
)
async def get_wallet_by_user(
    user_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """
    Get wallet by user ID.

    Args:
        user_id: User ID (UUID)

    Returns:
        Wallet details
    """
    logger.info(
        "Fetching wallet by user ID",
        extra={"user_id": user_id, "current_user_id": current_user_id},
    )

    wallet = await service.get_wallet_by_user_id(user_id)
    if not wallet:
        logger.warning(
            "Wallet not found for user",
            extra={"user_id": user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet not found for user {user_id}",
        )

    return WalletResponse.model_validate(wallet)


@router.patch(
    "/{wallet_id}",
    response_model=WalletResponse,
    summary="Update wallet",
    description="Update wallet status",
)
async def update_wallet(
    wallet_id: str,
    wallet_data: WalletUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """
    Update wallet status.

    Args:
        wallet_id: Wallet ID (UUID)
        wallet_data: Updated wallet data

    Returns:
        Updated wallet details
    """
    logger.info(
        "Updating wallet",
        extra={"wallet_id": wallet_id, "user_id": user_id},
    )

    try:
        wallet = await service.update_wallet(wallet_id, wallet_data)
        if not wallet:
            logger.warning(
                "Wallet not found for update",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.info(
            "Wallet updated successfully",
            extra={"wallet_id": wallet_id},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Wallet update validation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Wallet update failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update wallet",
        )


@router.get(
    "/{wallet_id}/balance",
    response_model=WalletBalance,
    summary="Get wallet balance",
    description="Get wallet balance information including available and escrow balances",
)
async def get_wallet_balance(
    wallet_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletBalance:
    """
    Get wallet balance.

    Args:
        wallet_id: Wallet ID (UUID)

    Returns:
        Wallet balance information
    """
    logger.info(
        "Fetching wallet balance",
        extra={"wallet_id": wallet_id, "user_id": user_id},
    )

    balance = await service.get_wallet_balance(wallet_id)
    if not balance:
        logger.warning(
            "Wallet not found for balance query",
            extra={"wallet_id": wallet_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet {wallet_id} not found",
        )

    return balance


@router.post(
    "/{wallet_id}/add-balance",
    response_model=WalletResponse,
    summary="Add balance to wallet",
    description="Add funds to wallet available balance",
)
async def add_balance(
    wallet_id: str,
    amount: Annotated[Decimal, Query(gt=0, description="Amount to add")],
    description: Annotated[str | None, Query(description="Optional description")] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[WalletService, Depends(get_wallet_service)] = None,
) -> WalletResponse:
    """
    Add balance to wallet.

    Args:
        wallet_id: Wallet ID (UUID)
        amount: Amount to add (must be positive)
        description: Optional description

    Returns:
        Updated wallet details
    """
    logger.info(
        "Adding balance to wallet",
        extra={
            "wallet_id": wallet_id,
            "amount": str(amount),
            "user_id": user_id,
        },
    )

    try:
        wallet = await service.add_balance(wallet_id, amount, description)
        if not wallet:
            logger.warning(
                "Wallet not found for adding balance",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.info(
            "Balance added successfully",
            extra={"wallet_id": wallet_id, "amount": str(amount)},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Add balance validation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Add balance failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add balance",
        )


@router.post(
    "/{wallet_id}/deduct-balance",
    response_model=WalletResponse,
    summary="Deduct balance from wallet",
    description="Deduct funds from wallet available balance",
)
async def deduct_balance(
    wallet_id: str,
    amount: Annotated[Decimal, Query(gt=0, description="Amount to deduct")],
    description: Annotated[str | None, Query(description="Optional description")] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[WalletService, Depends(get_wallet_service)] = None,
) -> WalletResponse:
    """
    Deduct balance from wallet.

    Args:
        wallet_id: Wallet ID (UUID)
        amount: Amount to deduct (must be positive)
        description: Optional description

    Returns:
        Updated wallet details
    """
    logger.info(
        "Deducting balance from wallet",
        extra={
            "wallet_id": wallet_id,
            "amount": str(amount),
            "user_id": user_id,
        },
    )

    try:
        wallet = await service.deduct_balance(wallet_id, amount, description)
        if not wallet:
            logger.warning(
                "Wallet not found for deducting balance",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.info(
            "Balance deducted successfully",
            extra={"wallet_id": wallet_id, "amount": str(amount)},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Deduct balance validation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Deduct balance failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deduct balance",
        )


@router.post(
    "/{wallet_id}/move-to-escrow",
    response_model=WalletResponse,
    summary="Move funds to escrow",
    description="Move funds from available balance to escrow",
)
async def move_to_escrow(
    wallet_id: str,
    amount: Annotated[Decimal, Query(gt=0, description="Amount to move to escrow")],
    description: Annotated[str | None, Query(description="Optional description")] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[WalletService, Depends(get_wallet_service)] = None,
) -> WalletResponse:
    """
    Move funds to escrow.

    Args:
        wallet_id: Wallet ID (UUID)
        amount: Amount to move (must be positive)
        description: Optional description

    Returns:
        Updated wallet details
    """
    logger.info(
        "Moving funds to escrow",
        extra={
            "wallet_id": wallet_id,
            "amount": str(amount),
            "user_id": user_id,
        },
    )

    try:
        wallet = await service.move_to_escrow(wallet_id, amount, description)
        if not wallet:
            logger.warning(
                "Wallet not found for escrow operation",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.info(
            "Funds moved to escrow successfully",
            extra={"wallet_id": wallet_id, "amount": str(amount)},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Move to escrow validation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Move to escrow failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move funds to escrow",
        )


@router.post(
    "/{wallet_id}/release-from-escrow",
    response_model=WalletResponse,
    summary="Release funds from escrow",
    description="Release funds from escrow to available balance",
)
async def release_from_escrow(
    wallet_id: str,
    amount: Annotated[Decimal, Query(gt=0, description="Amount to release from escrow")],
    description: Annotated[str | None, Query(description="Optional description")] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[WalletService, Depends(get_wallet_service)] = None,
) -> WalletResponse:
    """
    Release funds from escrow.

    Args:
        wallet_id: Wallet ID (UUID)
        amount: Amount to release (must be positive)
        description: Optional description

    Returns:
        Updated wallet details
    """
    logger.info(
        "Releasing funds from escrow",
        extra={
            "wallet_id": wallet_id,
            "amount": str(amount),
            "user_id": user_id,
        },
    )

    try:
        wallet = await service.release_from_escrow(wallet_id, amount, description)
        if not wallet:
            logger.warning(
                "Wallet not found for escrow release",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.info(
            "Funds released from escrow successfully",
            extra={"wallet_id": wallet_id, "amount": str(amount)},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Release from escrow validation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Release from escrow failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release funds from escrow",
        )


@router.post(
    "/{wallet_id}/suspend",
    response_model=WalletResponse,
    summary="Suspend wallet",
    description="Suspend a wallet to prevent transactions",
)
async def suspend_wallet(
    wallet_id: str,
    reason: Annotated[str | None, Query(description="Reason for suspension")] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[WalletService, Depends(get_wallet_service)] = None,
) -> WalletResponse:
    """
    Suspend wallet.

    Args:
        wallet_id: Wallet ID (UUID)
        reason: Optional reason for suspension

    Returns:
        Updated wallet details
    """
    logger.warning(
        "Suspending wallet",
        extra={"wallet_id": wallet_id, "reason": reason, "user_id": user_id},
    )

    try:
        wallet = await service.suspend_wallet(wallet_id, reason)
        if not wallet:
            logger.warning(
                "Wallet not found for suspension",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.warning(
            "Wallet suspended successfully",
            extra={"wallet_id": wallet_id},
        )

        return WalletResponse.model_validate(wallet)

    except Exception as e:
        logger.error(
            "Wallet suspension failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to suspend wallet",
        )


@router.post(
    "/{wallet_id}/activate",
    response_model=WalletResponse,
    summary="Activate wallet",
    description="Activate a suspended wallet",
)
async def activate_wallet(
    wallet_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletResponse:
    """
    Activate wallet.

    Args:
        wallet_id: Wallet ID (UUID)

    Returns:
        Updated wallet details
    """
    logger.info(
        "Activating wallet",
        extra={"wallet_id": wallet_id, "user_id": user_id},
    )

    try:
        wallet = await service.activate_wallet(wallet_id)
        if not wallet:
            logger.warning(
                "Wallet not found for activation",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.info(
            "Wallet activated successfully",
            extra={"wallet_id": wallet_id},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Wallet activation validation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Wallet activation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate wallet",
        )


@router.post(
    "/{wallet_id}/close",
    response_model=WalletResponse,
    summary="Close wallet",
    description="Permanently close a wallet (must have zero balance)",
)
async def close_wallet(
    wallet_id: str,
    reason: Annotated[str | None, Query(description="Reason for closure")] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    service: Annotated[WalletService, Depends(get_wallet_service)] = None,
) -> WalletResponse:
    """
    Close wallet.

    Args:
        wallet_id: Wallet ID (UUID)
        reason: Optional reason for closure

    Returns:
        Updated wallet details
    """
    logger.warning(
        "Closing wallet",
        extra={"wallet_id": wallet_id, "reason": reason, "user_id": user_id},
    )

    try:
        wallet = await service.close_wallet(wallet_id, reason)
        if not wallet:
            logger.warning(
                "Wallet not found for closure",
                extra={"wallet_id": wallet_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found",
            )

        logger.warning(
            "Wallet closed successfully",
            extra={"wallet_id": wallet_id},
        )

        return WalletResponse.model_validate(wallet)

    except ValueError as e:
        logger.warning(
            "Wallet closure validation failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Wallet closure failed",
            extra={"wallet_id": wallet_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to close wallet",
        )
