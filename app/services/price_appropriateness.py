from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from statistics import median


WON = Decimal("1")
PERCENT = Decimal("100")
MONTHS_PER_YEAR = Decimal("12")


@dataclass(frozen=True)
class ComparableRent:
    deposit: int
    monthly_rent: int


@dataclass(frozen=True)
class PriceComparison:
    median_equivalent_monthly_cost: int
    difference_from_median: int
    difference_rate_from_median: float
    price_percentile: float


def equivalent_monthly_cost(
    *,
    deposit: int,
    monthly_rent: int,
    annual_conversion_rate: Decimal,
) -> int:
    value = (
        Decimal(monthly_rent)
        + Decimal(deposit)
        * annual_conversion_rate
        / PERCENT
        / MONTHS_PER_YEAR
    )
    return int(value.quantize(WON, rounding=ROUND_HALF_UP))


def calculate_price_comparison(
    *,
    candidate_deposit: int,
    candidate_monthly_rent: int,
    comparables: list[ComparableRent],
    annual_conversion_rate: Decimal,
) -> PriceComparison:
    if not comparables:
        raise ValueError("at least one comparison sample is required")

    candidate_cost = equivalent_monthly_cost(
        deposit=candidate_deposit,
        monthly_rent=candidate_monthly_rent,
        annual_conversion_rate=annual_conversion_rate,
    )
    comparable_costs = [
        equivalent_monthly_cost(
            deposit=item.deposit,
            monthly_rent=item.monthly_rent,
            annual_conversion_rate=annual_conversion_rate,
        )
        for item in comparables
    ]
    median_cost = int(
        Decimal(str(median(comparable_costs))).quantize(
            WON,
            rounding=ROUND_HALF_UP,
        ),
    )
    difference = candidate_cost - median_cost
    difference_rate = (
        Decimal(difference) / Decimal(median_cost) * PERCENT
        if median_cost
        else Decimal("0")
    )
    count_at_or_below = sum(
        cost <= candidate_cost for cost in comparable_costs
    )
    percentile = (
        Decimal(count_at_or_below)
        / Decimal(len(comparable_costs))
        * PERCENT
    )

    return PriceComparison(
        median_equivalent_monthly_cost=median_cost,
        difference_from_median=difference,
        difference_rate_from_median=float(
            difference_rate.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            ),
        ),
        price_percentile=float(
            percentile.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            ),
        ),
    )
