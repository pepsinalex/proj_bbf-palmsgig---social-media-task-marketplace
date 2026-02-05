"""
Unit tests for FeeService.

Tests all fee calculation logic including service fee, total cost,
and comprehensive fee breakdown calculations.
"""

import pytest
from decimal import Decimal

from src.task_management.services.fee_service import FeeService


class TestFeeService:
    """Test suite for FeeService."""

    def test_calculate_service_fee_basic(self) -> None:
        """Test basic service fee calculation (15% of budget)."""
        budget = Decimal("10.00")
        service_fee = FeeService.calculate_service_fee(budget)

        assert service_fee == Decimal("1.50")
        assert isinstance(service_fee, Decimal)

    def test_calculate_service_fee_with_cents(self) -> None:
        """Test service fee calculation with decimal budget."""
        budget = Decimal("12.50")
        service_fee = FeeService.calculate_service_fee(budget)

        assert service_fee == Decimal("1.88")

    def test_calculate_service_fee_rounds_properly(self) -> None:
        """Test service fee rounding to 2 decimal places."""
        budget = Decimal("10.33")
        service_fee = FeeService.calculate_service_fee(budget)

        # 10.33 * 0.15 = 1.5495, rounds to 1.55
        assert service_fee == Decimal("1.55")

    def test_calculate_service_fee_small_amount(self) -> None:
        """Test service fee calculation for small amounts."""
        budget = Decimal("0.50")
        service_fee = FeeService.calculate_service_fee(budget)

        # 0.50 * 0.15 = 0.075, rounds to 0.08
        assert service_fee == Decimal("0.08")

    def test_calculate_service_fee_large_amount(self) -> None:
        """Test service fee calculation for large amounts."""
        budget = Decimal("1000.00")
        service_fee = FeeService.calculate_service_fee(budget)

        assert service_fee == Decimal("150.00")

    def test_calculate_service_fee_invalid_budget(self) -> None:
        """Test service fee calculation with invalid budget."""
        with pytest.raises(ValueError, match="Budget must be positive"):
            FeeService.calculate_service_fee(Decimal("0.00"))

        with pytest.raises(ValueError, match="Budget must be positive"):
            FeeService.calculate_service_fee(Decimal("-10.00"))

    def test_calculate_total_cost_basic(self) -> None:
        """Test basic total cost calculation."""
        budget = Decimal("10.00")
        service_fee = Decimal("1.50")
        total_cost = FeeService.calculate_total_cost(budget, service_fee)

        assert total_cost == Decimal("11.50")

    def test_calculate_total_cost_with_decimals(self) -> None:
        """Test total cost calculation with decimal values."""
        budget = Decimal("12.99")
        service_fee = Decimal("1.95")
        total_cost = FeeService.calculate_total_cost(budget, service_fee)

        assert total_cost == Decimal("14.94")

    def test_calculate_total_cost_rounds_properly(self) -> None:
        """Test total cost rounding to 2 decimal places."""
        budget = Decimal("10.335")
        service_fee = Decimal("1.551")
        total_cost = FeeService.calculate_total_cost(budget, service_fee)

        # Should round to 2 decimal places
        assert total_cost == Decimal("11.89")

    def test_calculate_total_cost_all_performers_basic(self) -> None:
        """Test total cost for all performers calculation."""
        total_cost = Decimal("11.50")
        max_performers = 100
        total = FeeService.calculate_total_cost_all_performers(
            total_cost, max_performers
        )

        assert total == Decimal("1150.00")

    def test_calculate_total_cost_all_performers_single(self) -> None:
        """Test total cost for single performer."""
        total_cost = Decimal("11.50")
        max_performers = 1
        total = FeeService.calculate_total_cost_all_performers(
            total_cost, max_performers
        )

        assert total == Decimal("11.50")

    def test_calculate_total_cost_all_performers_large(self) -> None:
        """Test total cost for large number of performers."""
        total_cost = Decimal("5.75")
        max_performers = 10000
        total = FeeService.calculate_total_cost_all_performers(
            total_cost, max_performers
        )

        assert total == Decimal("57500.00")

    def test_calculate_total_cost_all_performers_invalid(self) -> None:
        """Test total cost with invalid max_performers."""
        total_cost = Decimal("11.50")

        with pytest.raises(ValueError, match="Max performers must be positive"):
            FeeService.calculate_total_cost_all_performers(total_cost, 0)

        with pytest.raises(ValueError, match="Max performers must be positive"):
            FeeService.calculate_total_cost_all_performers(total_cost, -10)

    def test_calculate_fee_breakdown_basic(self) -> None:
        """Test comprehensive fee breakdown calculation."""
        budget = Decimal("10.00")
        max_performers = 100

        breakdown = FeeService.calculate_fee_breakdown(budget, max_performers)

        assert breakdown.budget == Decimal("10.00")
        assert breakdown.service_fee == Decimal("1.50")
        assert breakdown.service_fee_percentage == Decimal("0.15")
        assert breakdown.total_cost == Decimal("11.50")
        assert breakdown.total_cost_all_performers == Decimal("1150.00")

    def test_calculate_fee_breakdown_with_decimals(self) -> None:
        """Test fee breakdown with decimal budget."""
        budget = Decimal("12.50")
        max_performers = 50

        breakdown = FeeService.calculate_fee_breakdown(budget, max_performers)

        assert breakdown.budget == Decimal("12.50")
        assert breakdown.service_fee == Decimal("1.88")
        assert breakdown.total_cost == Decimal("14.38")
        assert breakdown.total_cost_all_performers == Decimal("719.00")

    def test_calculate_fee_breakdown_small_budget(self) -> None:
        """Test fee breakdown with small budget."""
        budget = Decimal("0.50")
        max_performers = 10

        breakdown = FeeService.calculate_fee_breakdown(budget, max_performers)

        assert breakdown.budget == Decimal("0.50")
        assert breakdown.service_fee == Decimal("0.08")
        assert breakdown.total_cost == Decimal("0.58")
        assert breakdown.total_cost_all_performers == Decimal("5.80")

    def test_calculate_fee_breakdown_large_scale(self) -> None:
        """Test fee breakdown for large scale task."""
        budget = Decimal("25.00")
        max_performers = 5000

        breakdown = FeeService.calculate_fee_breakdown(budget, max_performers)

        assert breakdown.budget == Decimal("25.00")
        assert breakdown.service_fee == Decimal("3.75")
        assert breakdown.total_cost == Decimal("28.75")
        assert breakdown.total_cost_all_performers == Decimal("143750.00")

    def test_calculate_fee_breakdown_invalid_budget(self) -> None:
        """Test fee breakdown with invalid budget."""
        with pytest.raises(ValueError, match="Budget must be positive"):
            FeeService.calculate_fee_breakdown(Decimal("0.00"), 100)

        with pytest.raises(ValueError, match="Budget must be positive"):
            FeeService.calculate_fee_breakdown(Decimal("-10.00"), 100)

    def test_calculate_fee_breakdown_invalid_performers(self) -> None:
        """Test fee breakdown with invalid max_performers."""
        with pytest.raises(ValueError, match="Max performers must be positive"):
            FeeService.calculate_fee_breakdown(Decimal("10.00"), 0)

        with pytest.raises(ValueError, match="Max performers must be positive"):
            FeeService.calculate_fee_breakdown(Decimal("10.00"), -50)

    def test_get_service_fee_percentage(self) -> None:
        """Test getting service fee percentage."""
        percentage = FeeService.get_service_fee_percentage()

        assert percentage == Decimal("0.15")
        assert isinstance(percentage, Decimal)

    def test_fee_calculations_are_consistent(self) -> None:
        """Test that fee calculations are consistent across methods."""
        budget = Decimal("20.00")
        max_performers = 200

        # Calculate using individual methods
        service_fee = FeeService.calculate_service_fee(budget)
        total_cost = FeeService.calculate_total_cost(budget, service_fee)
        total_all = FeeService.calculate_total_cost_all_performers(
            total_cost, max_performers
        )

        # Calculate using breakdown
        breakdown = FeeService.calculate_fee_breakdown(budget, max_performers)

        # Should match
        assert breakdown.service_fee == service_fee
        assert breakdown.total_cost == total_cost
        assert breakdown.total_cost_all_performers == total_all

    def test_decimal_precision_maintained(self) -> None:
        """Test that decimal precision is maintained throughout calculations."""
        budget = Decimal("10.99")
        max_performers = 333

        breakdown = FeeService.calculate_fee_breakdown(budget, max_performers)

        # All values should be Decimal with 2 decimal places
        assert breakdown.budget.as_tuple().exponent == -2
        assert breakdown.service_fee.as_tuple().exponent == -2
        assert breakdown.total_cost.as_tuple().exponent == -2
        assert breakdown.total_cost_all_performers.as_tuple().exponent == -2

    def test_fee_breakdown_model_validation(self) -> None:
        """Test that FeeBreakdown model validates correctly."""
        budget = Decimal("15.00")
        max_performers = 75

        breakdown = FeeService.calculate_fee_breakdown(budget, max_performers)

        # Should be a valid Pydantic model
        assert breakdown.model_dump() == {
            "budget": Decimal("15.00"),
            "service_fee": Decimal("2.25"),
            "service_fee_percentage": Decimal("0.15"),
            "total_cost": Decimal("17.25"),
            "total_cost_all_performers": Decimal("1293.75"),
        }
