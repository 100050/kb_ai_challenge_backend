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
                monthly_rent=700_000 + index * 50_000,
                exclusive_area_m2=60,
                contract_date=date(2026, 7, index + 1),
            )
            for index in range(10)
        ] + [
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
        *,
        parent_region_name: str | None = None,
    ) -> Decimal | None:
        return Decimal("5") if year_month == "202607" else None


def test_market_price_uses_twenty_four_months_and_fifteen_percent_area_by_default(
) -> None:
    service = MarketPriceService(
        FakeLegalDongClient(),
        FakeRentClient(),
        FakeROneClient(),
    )

    assert service.lookback_months == 24
    assert service.area_tolerance_percent == 15
    assert len(service._recent_months(date(2026, 7, 1), 24)) == 24


def test_market_price_extracts_r_one_parent_region_name() -> None:
    assert MarketPriceService._parent_region_name(
        "서울시 종로구 명륜3가",
    ) == "서울"
    assert MarketPriceService._parent_region_name(
        "부산광역시 동구 수정동",
    ) == "부산"
    assert MarketPriceService._parent_region_name(
        "경기도 성남시 분당구 정자동",
    ) == "경기"


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
    assert result.sample_count == 10
    assert result.comparison_mode == "median"
    assert result.median_equivalent_monthly_cost == 925_000
    assert result.difference_from_median == -25_000
    assert result.difference_rate_from_median == -2.7
    assert result.price_percentile == 50
    assert result.samples == []


class SmallFakeRentClient:
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
                deposit=10_000_000,
                monthly_rent=700_000,
                exclusive_area_m2=58,
                contract_date=date(2026, 7, 1),
                property_name="비교 아파트 A",
                legal_dong_name="역삼동",
                jibun="123-4",
            ),
            RentTransaction(
                deposit=20_000_000,
                monthly_rent=800_000,
                exclusive_area_m2=62,
                contract_date=date(2026, 7, 2),
                property_name="비교 아파트 B",
                legal_dong_name="도곡동",
                jibun="55",
            ),
        ]


def test_market_price_returns_all_values_when_samples_are_under_ten() -> None:
    service = MarketPriceService(
        FakeLegalDongClient(),
        SmallFakeRentClient(),
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
    assert result.sample_count == 2
    assert result.comparison_mode == "individual_samples"
    assert result.median_equivalent_monthly_cost is None
    assert result.difference_from_median is None
    assert result.difference_rate_from_median is None
    assert result.price_percentile is None
    assert result.candidate_equivalent_monthly_cost == 900_000
    assert [sample.model_dump() for sample in result.samples] == [
        {
            "name": "비교 아파트 A",
            "address": "서울특별시 강남구 역삼동 123-4",
            "deposit": 10_000_000,
            "monthly_rent": 700_000,
            "exclusive_area_m2": 58.0,
            "contract_date": date(2026, 7, 1),
            "equivalent_monthly_cost": 741_667,
        },
        {
            "name": "비교 아파트 B",
            "address": "서울특별시 강남구 도곡동 55",
            "deposit": 20_000_000,
            "monthly_rent": 800_000,
            "exclusive_area_m2": 62.0,
            "contract_date": date(2026, 7, 2),
            "equivalent_monthly_cost": 883_333,
        },
    ]


def test_market_price_missing_fields_is_unavailable() -> None:
    service = MarketPriceService(
        FakeLegalDongClient(),
        FakeRentClient(),
        FakeROneClient(),
    )

    result = asyncio.run(service.evaluate(HousingPlan(name="초안")))

    assert result.status == "unavailable"
    assert result.reason == "missing_comparison_fields"
    assert result.sample_count == 0
