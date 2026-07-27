import asyncio
from datetime import date
from decimal import Decimal

from app.clients.real_estate import RentTransaction
from app.models.housing_plan import HousingPlan
from app.services.market_price import MarketPriceService


class FakeLegalDongClient:
    async def search(self, address_name: str) -> list:
        raise AssertionError("stored legal dong code should be used")


class FakeRentClient:
    async def fetch(
        self,
        property_type: str,
        district_code: str,
        deal_year_month: str,
    ) -> list[RentTransaction]:
        if deal_year_month != "202607":
            return []
        return [
            RentTransaction(
                deposit=0,
                monthly_rent=800_000,
                exclusive_area_m2=58,
                contract_date=date(2026, 7, 1),
            ),
            RentTransaction(
                deposit=0,
                monthly_rent=1_000_000,
                exclusive_area_m2=62,
                contract_date=date(2026, 7, 2),
            ),
            RentTransaction(
                deposit=0,
                monthly_rent=2_000_000,
                exclusive_area_m2=90,
                contract_date=date(2026, 7, 3),
            ),
        ]


class FakeROneClient:
    async def conversion_rate(
        self,
        property_type: str,
        district_name: str,
        year_month: str,
    ) -> Decimal | None:
        return Decimal("5") if year_month == "202607" else None


def test_market_price_filters_similar_area_and_returns_metrics() -> None:
    service = MarketPriceService(
        FakeLegalDongClient(),
        FakeRentClient(),
        FakeROneClient(),
        lookback_months=1,
        area_tolerance_percent=10,
    )
    plan = HousingPlan(
        name="역삼 매물",
        address="서울특별시 강남구 역삼동",
        property_type="apartment",
        legal_dong_code="1168010100",
        exclusive_area_m2=60,
        deposit=0,
        monthly_rent=900_000,
    )

    result = asyncio.run(service.evaluate(plan))

    assert result.status == "available"
    assert result.median_equivalent_monthly_cost == 900_000
    assert result.difference_from_median == 0
    assert result.difference_rate_from_median == 0
    assert result.price_percentile == 50


def test_market_price_missing_fields_is_unavailable() -> None:
    service = MarketPriceService(
        FakeLegalDongClient(),
        FakeRentClient(),
        FakeROneClient(),
    )

    result = asyncio.run(service.evaluate(HousingPlan(name="초안")))

    assert result.status == "unavailable"
    assert result.reason == "missing_comparison_fields"
