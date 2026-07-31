import asyncio
from datetime import date
from decimal import Decimal

from app.clients.legal_dong import (
    LegalDongClient,
    normalize_legal_dong_address,
)
from app.clients.r_one import ROneClient
from app.clients.real_estate import RentTransactionClient
from app.models.housing_plan import HousingPlan
from app.schemas.evaluation import (
    PriceAppropriatenessResult,
    PriceComparableSample,
)
from app.services.price_appropriateness import (
    ComparableRent,
    calculate_price_comparison,
    equivalent_monthly_cost,
)


MINIMUM_MEDIAN_SAMPLE_COUNT = 10

R_ONE_PARENT_REGION_NAMES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


class MarketPriceService:
    def __init__(
        self,
        legal_dong_client: LegalDongClient,
        rent_client: RentTransactionClient,
        r_one_client: ROneClient,
        *,
        lookback_months: int = 24,
        area_tolerance_percent: float = 15,
    ) -> None:
        self.legal_dong_client = legal_dong_client
        self.rent_client = rent_client
        self.r_one_client = r_one_client
        self.lookback_months = lookback_months
        self.area_tolerance_percent = area_tolerance_percent

    async def evaluate(
        self,
        plan: HousingPlan,
    ) -> PriceAppropriatenessResult:
        missing = [
            name
            for name in (
                "property_type",
                "exclusive_area_m2",
                "deposit",
                "monthly_rent",
                "address",
            )
            if getattr(plan, name) is None
        ]
        if missing:
            return self._unavailable("missing_comparison_fields")

        legal_dong_code = plan.legal_dong_code
        if legal_dong_code is None:
            legal_dongs = await self.legal_dong_client.search(plan.address)
            if not legal_dongs:
                return self._unavailable("legal_dong_not_found")
            legal_dong_code = legal_dongs[0].code

        district_name = self._district_name(plan.address)
        parent_region_name = self._parent_region_name(plan.address)
        months = self._recent_months(date.today(), self.lookback_months)
        transactions_by_month = await asyncio.gather(
            *[
                self.rent_client.fetch(
                    plan.property_type,
                    legal_dong_code[:5],
                    month,
                )
                for month in months
            ],
        )
        transactions = [
            transaction
            for monthly_transactions in transactions_by_month
            for transaction in monthly_transactions
        ]
        tolerance = self.area_tolerance_percent / 100
        minimum_area = plan.exclusive_area_m2 * (1 - tolerance)
        maximum_area = plan.exclusive_area_m2 * (1 + tolerance)
        comparable_transactions = [
            item
            for item in transactions
            if item.exclusive_area_m2 is not None
            and minimum_area <= item.exclusive_area_m2 <= maximum_area
        ]
        if not comparable_transactions:
            return self._unavailable("insufficient_comparables")

        conversion_rate = None
        for month in months:
            conversion_rate = await self.r_one_client.conversion_rate(
                plan.property_type,
                district_name,
                month,
                parent_region_name=parent_region_name,
            )
            if conversion_rate is not None:
                break
        if conversion_rate is None:
            return self._unavailable(
                "conversion_rate_not_found",
                sample_count=len(comparable_transactions),
            )

        sample_count = len(comparable_transactions)
        if sample_count < MINIMUM_MEDIAN_SAMPLE_COUNT:
            annual_conversion_rate = Decimal(conversion_rate)
            district_address = self._district_address(plan.address)
            return PriceAppropriatenessResult(
                status="available",
                sample_count=sample_count,
                comparison_mode="individual_samples",
                candidate_equivalent_monthly_cost=equivalent_monthly_cost(
                    deposit=plan.deposit,
                    monthly_rent=plan.monthly_rent,
                    annual_conversion_rate=annual_conversion_rate,
                ),
                samples=[
                    PriceComparableSample(
                        name=item.property_name,
                        address=self._sample_address(
                            district_address,
                            item.legal_dong_name,
                            item.jibun,
                        ),
                        deposit=item.deposit,
                        monthly_rent=item.monthly_rent,
                        exclusive_area_m2=item.exclusive_area_m2,
                        contract_date=item.contract_date,
                        equivalent_monthly_cost=equivalent_monthly_cost(
                            deposit=item.deposit,
                            monthly_rent=item.monthly_rent,
                            annual_conversion_rate=annual_conversion_rate,
                        ),
                    )
                    for item in comparable_transactions
                ],
            )

        comparison = calculate_price_comparison(
            candidate_deposit=plan.deposit,
            candidate_monthly_rent=plan.monthly_rent,
            comparables=[
                ComparableRent(
                    deposit=item.deposit,
                    monthly_rent=item.monthly_rent,
                )
                for item in comparable_transactions
            ],
            annual_conversion_rate=Decimal(conversion_rate),
        )
        return PriceAppropriatenessResult(
            status="available",
            sample_count=sample_count,
            comparison_mode="median",
            median_equivalent_monthly_cost=(
                comparison.median_equivalent_monthly_cost
            ),
            difference_from_median=comparison.difference_from_median,
            difference_rate_from_median=(
                comparison.difference_rate_from_median
            ),
            price_percentile=comparison.price_percentile,
        )

    async def evaluate_safely(
        self,
        plan: HousingPlan,
    ) -> PriceAppropriatenessResult:
        try:
            return await self.evaluate(plan)
        except Exception:
            return self._unavailable("external_api_unavailable")

    @staticmethod
    def _district_name(address: str) -> str:
        parts = address.split()
        for part in reversed(parts):
            if part.endswith(("시", "군", "구")) and not part.endswith(
                ("특별시", "광역시"),
            ):
                return part
        return parts[0]

    @staticmethod
    def _parent_region_name(address: str) -> str:
        normalized_address = normalize_legal_dong_address(address)
        first_part = normalized_address.split()[0]
        return R_ONE_PARENT_REGION_NAMES.get(first_part, first_part)

    @staticmethod
    def _district_address(address: str) -> str:
        parts = normalize_legal_dong_address(address).split()
        for index, part in enumerate(parts):
            if part.endswith(("시", "군", "구")) and not part.endswith(
                ("특별시", "광역시", "특별자치시"),
            ):
                return " ".join(parts[: index + 1])
        return parts[0] if parts else ""

    @staticmethod
    def _sample_address(
        district_address: str,
        legal_dong_name: str | None,
        jibun: str | None,
    ) -> str | None:
        address = " ".join(
            part
            for part in (district_address, legal_dong_name, jibun)
            if part
        )
        return address or None

    @staticmethod
    def _recent_months(today: date, count: int) -> list[str]:
        months: list[str] = []
        year = today.year
        month = today.month
        for _ in range(count):
            months.append(f"{year:04d}{month:02d}")
            month -= 1
            if month == 0:
                year -= 1
                month = 12
        return months

    @staticmethod
    def _unavailable(
        reason: str,
        *,
        sample_count: int = 0,
    ) -> PriceAppropriatenessResult:
        return PriceAppropriatenessResult(
            status="unavailable",
            sample_count=sample_count,
            reason=reason,
        )
