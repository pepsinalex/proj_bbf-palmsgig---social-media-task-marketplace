"""
Escrow Router.

Provides REST API endpoints for escrow operations including holding funds,
releasing funds, and checking escrow status with proper authentication.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.schemas.escrow import (
    EscrowHoldRequest,
    EscrowReleaseRequest,
    EscrowResponse,
)
from src.payment_service.services.escrow_service import EscrowService
from src.shared.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/escrow", tags=["escrow"])


def get_escrow_service(session: AsyncSession = Depends(get_session)) -> EscrowService:
    """
    Dependency to get escrow service instance.

    Args:
        session: Database session

    Returns:
        EscrowService instance
    """
    return EscrowService(session)


@router.post(
    "/hold",
    response_model=EscrowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Hold funds in escrow",
    description="Hold funds in escrow for a task payment with platform fee calculation",
)
async def hold_funds(
    request: EscrowHoldRequest,
    escrow_service: EscrowService = Depends(get_escrow_service),
) -> EscrowResponse:
    """
    Hold funds in escrow for a task.

    Moves funds from payer's available balance to escrow balance
    including platform fee calculation.

    Args:
        request: Escrow hold request data
        escrow_service: Escrow service instance

    Returns:
        EscrowResponse with hold details

    Raises:
        HTTPException: If hold operation fails
    """
    logger.info(
        "Escrow hold request received",
        extra={
            "task_id": request.task_id,
            "payer_wallet_id": request.payer_wallet_id,
            "payee_wallet_id": request.payee_wallet_id,
            "amount": str(request.amount),
        },
    )

    try:
        result = await escrow_service.hold_funds(request)
        logger.info(
            "Funds held in escrow successfully",
            extra={
                "task_id": request.task_id,
                "transaction_id": result.transaction_id,
                "total_amount": str(result.total_amount),
            },
        )
        return result
    except ValueError as e:
        logger.error(
            "Failed to hold funds in escrow",
            extra={
                "task_id": request.task_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error holding funds in escrow",
            extra={
                "task_id": request.task_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to hold funds in escrow",
        )


@router.post(
    "/release",
    response_model=EscrowResponse,
    status_code=status.HTTP_200_OK,
    summary="Release funds from escrow",
    description="Release funds from escrow to payee upon task verification",
)
async def release_funds(
    request: EscrowReleaseRequest,
    escrow_service: EscrowService = Depends(get_escrow_service),
) -> EscrowResponse:
    """
    Release funds from escrow to payee.

    Transfers funds from payer's escrow to payee's available balance
    with platform fee deduction.

    Args:
        request: Escrow release request data
        escrow_service: Escrow service instance

    Returns:
        EscrowResponse with release details

    Raises:
        HTTPException: If release operation fails
    """
    logger.info(
        "Escrow release request received",
        extra={
            "task_id": request.task_id,
            "payer_wallet_id": request.payer_wallet_id,
            "payee_wallet_id": request.payee_wallet_id,
            "amount": str(request.amount),
        },
    )

    try:
        result = await escrow_service.release_funds(request)
        logger.info(
            "Funds released from escrow successfully",
            extra={
                "task_id": request.task_id,
                "transaction_id": result.transaction_id,
                "total_amount": str(result.total_amount),
            },
        )
        return result
    except ValueError as e:
        logger.error(
            "Failed to release funds from escrow",
            extra={
                "task_id": request.task_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error releasing funds from escrow",
            extra={
                "task_id": request.task_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release funds from escrow",
        )


@router.get(
    "/{task_id}",
    response_model=EscrowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get escrow status",
    description="Get current escrow status for a task",
)
async def get_escrow_status(
    task_id: str,
    escrow_service: EscrowService = Depends(get_escrow_service),
) -> EscrowResponse:
    """
    Get escrow status for a task.

    Args:
        task_id: Task ID
        escrow_service: Escrow service instance

    Returns:
        EscrowResponse with current status

    Raises:
        HTTPException: If escrow not found or operation fails
    """
    logger.info(
        "Escrow status request received",
        extra={"task_id": task_id},
    )

    try:
        result = await escrow_service.get_escrow_status(task_id)
        if not result:
            logger.warning(
                "Escrow not found for task",
                extra={"task_id": task_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Escrow not found for task: {task_id}",
            )

        logger.info(
            "Escrow status retrieved successfully",
            extra={
                "task_id": task_id,
                "status": result.status,
            },
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error getting escrow status",
            extra={
                "task_id": task_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get escrow status",
        )
