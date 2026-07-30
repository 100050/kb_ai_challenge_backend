from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal
from xml.etree import ElementTree

import httpx


PropertyType = Literal[
    "apartment",
    "row_house",
    "multi_family",
    "officetel",
    "detached_house",
    "multi_household",
]


@dataclass(frozen=True)
class RentTransaction:
    deposit: int
    monthly_rent: int
    exclusive_area_m2: float | None
    contract_date: date
    property_name: str | None = None
    legal_dong_name: str | None = None
    jibun: str | None = None


ENDPOINTS: dict[str, str] = {
    "apartment": (
        "https://apis.data.go.kr/1613000/"
        "RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
    ),
    "row_house": (
        "https://apis.data.go.kr/1613000/"
        "RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
    ),
    "multi_family": (
        "https://apis.data.go.kr/1613000/"
        "RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
    ),
    "officetel": (
        "https://apis.data.go.kr/1613000/"
        "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    ),
    "detached_house": (
        "https://apis.data.go.kr/1613000/"
        "RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
    ),
    "multi_household": (
        "https://apis.data.go.kr/1613000/"
        "RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
    ),
}


class PublicDataApiError(RuntimeError):
    pass


class RentTransactionClient:
    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def fetch(
        self,
        property_type: PropertyType,
        district_code: str,
        deal_year_month: str,
    ) -> list[RentTransaction]:
        endpoint = ENDPOINTS[property_type]
        params = {
            "serviceKey": self.api_key,
            "LAWD_CD": district_code,
            "DEAL_YMD": deal_year_month,
            "pageNo": 1,
            "numOfRows": 9999,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(endpoint, params=params)
        response.raise_for_status()
        return parse_rent_transactions(response.text)


def parse_rent_transactions(xml: str) -> list[RentTransaction]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise PublicDataApiError("실거래가 API XML 응답이 올바르지 않습니다.") from exc

    result_code = _find_text(root, ("resultCode",))
    if result_code and result_code not in {"000", "00", "INFO-0"}:
        message = _find_text(root, ("resultMsg",)) or "unknown error"
        raise PublicDataApiError(f"{result_code}: {message}")

    transactions: list[RentTransaction] = []
    for item in root.findall(".//item"):
        deposit = _money_from_ten_thousand_won(
            _child_text(item, ("보증금액", "deposit")),
        )
        monthly_rent = _money_from_ten_thousand_won(
            _child_text(item, ("월세금액", "monthlyRent")),
        )
        year_month = _child_text(
            item,
            ("계약년월", "dealYearMonth", "contractYearMonth"),
        )
        if not year_month:
            year = _child_text(item, ("dealYear", "계약년도"))
            month = _child_text(item, ("dealMonth", "계약월"))
            if year and month:
                year_month = f"{int(year):04d}{int(month):02d}"
        day = _child_text(item, ("계약일", "dealDay", "contractDay"))
        if deposit is None or monthly_rent is None or not year_month or not day:
            continue

        area_text = _child_text(
            item,
            ("전용면적", "excluUseAr", "전용면적(㎡)", "totalFloorAr"),
        )
        property_name = _child_text(
            item,
            (
                "aptNm",
                "아파트",
                "단지명",
                "offiNm",
                "mhouseNm",
                "houseNm",
                "buildingName",
            ),
        )
        legal_dong_name = _child_text(
            item,
            ("umdNm", "법정동", "legalDongName"),
        )
        jibun = _child_text(item, ("jibun", "지번"))
        try:
            contract_date = date(
                int(year_month[:4]),
                int(year_month[4:6]),
                int(day),
            )
            area = float(area_text) if area_text else None
        except (TypeError, ValueError):
            continue

        transactions.append(
            RentTransaction(
                deposit=deposit,
                monthly_rent=monthly_rent,
                exclusive_area_m2=area,
                contract_date=contract_date,
                property_name=property_name,
                legal_dong_name=legal_dong_name,
                jibun=jibun,
            ),
        )
    return transactions


def _find_text(root: ElementTree.Element, names: tuple[str, ...]) -> str | None:
    for name in names:
        node = root.find(f".//{name}")
        if node is not None and node.text:
            return node.text.strip()
    return None


def _child_text(
    item: ElementTree.Element,
    names: tuple[str, ...],
) -> str | None:
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return node.text.strip()
    return None


def _money_from_ten_thousand_won(value: str | None) -> int | None:
    if value is None:
        return None
    normalized = value.replace(",", "").replace(" ", "")
    try:
        return int(Decimal(normalized) * Decimal("10000"))
    except (ValueError, ArithmeticError):
        return None
