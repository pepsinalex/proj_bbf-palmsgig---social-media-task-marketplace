"""
Fee Service.

Provides fee calculation logic for task creation with 15% platform fee.
Handles all financial calculations with proper decimal precision.
"""

import logging
from decimal import Decimal

from src.task_management.schemas.task_creation import FeeBreakdown

logger = logging.getLogger(__name__)

# Platform service fee: 15% of budget
SERVICE_FEE_PERCENTAGE = Decimal("0.15")


class FeeService:
    """
    Service class for fee calculations.

    Handles all financial calculations related to task creation including
    service fees, total costs, and fee breakdowns with proper precision.
    """

    @staticmethod
    def calculate_service_fee(budget: Decimal) -> Decimal:
        """
        Calculate platform service fee (15% of budget).

        Args:
            budget: Task budget amount

        Returns:
            Service fee amount rounded to 2 decimal places

        Raises:
            ValueError: If budget is not positive

        Example:
            >>> FeeService.calculate_service_fee(Decimal("10.00"))
            Decimal('1.50')
        """
        if budget <= 0:
            logger.error(
                "Invalid budget for fee calculation",
                extra={"budget": str(budget)},
            )
            raise ValueError("Budget must be positive")

        service_fee = (budget * SERVICE_FEE_PERCENTAGE).quantize(
            Decimal("0.01")
        )

        logger.debug(
            "Service fee calculated",
            extra={
                "budget": str(budget),
                "service_fee": str(service_fee),
                "percentage": str(SERVICE_FEE_PERCENTAGE),
            },
        )

        return service_fee

    @staticmethod
    def calculate_total_cost(budget: Decimal, service_fee: Decimal) -> Decimal:
        """
        Calculate total cost per task (budget + service fee).

        Args:
            budget: Task budget amount
            service_fee: Platform service fee

        Returns:
            Total cost rounded to 2 decimal places

        Example:
            >>> FeeService.calculate_total_cost(
            ...     Decimal("10.00"),
            ...     Decimal("1.50")
            ... )
            Decimal('11.50')
        """
        total_cost = (budget + service_fee).quantize(Decimal("0.01"))

        logger.debug(
            "Total cost calculated",
            extra={
                "budget": str(budget),
                "service_fee": str(service_fee),
                "total_cost": str(total_cost),
            },
        )

        return total_cost

    @staticmethod
    def calculate_total_cost_all_performers(
        total_cost: Decimal, max_performers: int
    ) -> Decimal:
        """
        Calculate total cost for all performers.

        Args:
            total_cost: Total cost per task
            max_performers: Maximum number of performers

        Returns:
            Total cost for all performers rounded to 2 decimal places

        Raises:
            ValueError: If max_performers is not positive

        Example:
            >>> FeeService.calculate_total_cost_all_performers(
            ...     Decimal("11.50"),
            ...     100
            ... )
            Decimal('1150.00')
        """
        if max_performers <= 0:
            logger.error(
                "Invalid max_performers for cost calculation",
                extra={"max_performers": max_performers},
            )
            raise ValueError("Max performers must be positive")

        total = (total_cost * max_performers).quantize(Decimal("0.01"))

        logger.debug(
            "Total cost for all performers calculated",
            extra={
                "total_cost": str(total_cost),
                "max_performers": max_performers,
                "total": str(total),
            },
        )

        return total

    @classmethod
    def calculate_fee_breakdown(
        cls, budget: Decimal, max_performers: int
    ) -> FeeBreakdown:
        """
        Calculate comprehensive fee breakdown for task creation.

        Args:
            budget: Task budget amount per performer
            max_performers: Maximum number of performers

        Returns:
            FeeBreakdown with all calculated values

        Raises:
            ValueError: If budget or max_performers are invalid

        Example:
            >>> breakdown = FeeService.calculate_fee_breakdown(
            ...     Decimal("10.00"),
            ...     100
            ... )
            >>> breakdown.service_fee
            Decimal('1.50')
            >>> breakdown.total_cost
            Decimal('11.50')
            >>> breakdown.total_cost_all_performers
            Decimal('1150.00')
        """
        logger.info(
            "Calculating fee breakdown",
            extra={
                "budget": str(budget),
                "max_performers": max_performers,
            },
        )

        # Validate inputs
        if budget <= 0:
            raise ValueError("Budget must be positive")
        if max_performers <= 0:
            raise ValueError("Max performers must be positive")

        # Calculate fees
        service_fee = cls.calculate_service_fee(budget)
        total_cost = cls.calculate_total_cost(budget, service_fee)
        total_cost_all = cls.calculate_total_cost_all_performers(
            total_cost, max_performers
        )

        breakdown = FeeBreakdown(
            budget=budget,
            service_fee=service_fee,
            service_fee_percentage=SERVICE_FEE_PERCENTAGE,
            total_cost=total_cost,
            total_cost_all_performers=total_cost_all,
        )

        logger.info(
            "Fee breakdown calculated",
            extra={
                "budget": str(budget),
                "service_fee": str(service_fee),
                "total_cost": str(total_cost),
                "total_cost_all_performers": str(total_cost_all),
            },
        )

        return breakdown

    @classmethod
    def get_service_fee_percentage(cls) -> Decimal:
        """
        Get the current service fee percentage.

        Returns:
            Service fee percentage as decimal (0.15 for 15%)

        Example:
            >>> FeeService.get_service_fee_percentage()
            Decimal('0.15')
        """
        return SERVICE_FEE_PERCENTAGE
