from decimal import Decimal

import pytest

from app.services.price_appropriateness import (
    ComparableRent,
    calculate_price_comparison,
    equivalent_monthly_cost,
)


def test_equivalent_monthly_cost_uses_conversion_rate() -> None:
    result = equivalent_monthly_cost(
        deposit=100_000_000,
        monthly_rent=500_000,
        annual_conversion_rate=Decimal("5"),
    )

    assert result == 916_667


def test_price_comparison_returns_requested_four_values() -> None:
    comparables = [
        ComparableRent(deposit=0, monthly_rent=700_000),
        ComparableRent(deposit=0, monthly_rent=800_000),
        ComparableRent(deposit=0, monthly_rent=900_000),
        ComparableRent(deposit=0, monthly_rent=1_000_000),
    ]

    result = calculate_price_comparison(
        candidate_deposit=0,
        candidate_monthly_rent=900_000,
        comparables=comparables,
        annual_conversion_rate=Decimal("5"),
    )

    assert result.median_equivalent_monthly_cost == 850_000
    assert result.difference_from_median == 50_000
    assert result.difference_rate_from_median == 5.88
    assert result.price_percentile == 75.0


def test_price_comparison_requires_at_least_one_comparable() -> None:
    with pytest.raises(ValueError, match="comparison sample"):
        calculate_price_comparison(
            candidate_deposit=0,
            candidate_monthly_rent=900_000,
            comparables=[],
            annual_conversion_rate=Decimal("5"),
        )

