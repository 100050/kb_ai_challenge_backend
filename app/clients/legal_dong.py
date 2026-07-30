from dataclasses import dataclass

import httpx


ENDPOINT = (
    "https://apis.data.go.kr/1741000/"
    "StanReginCd/getStanReginCdList"
)

REGION_NAME_ALIASES = {
    "서울시": "서울특별시",
    "부산시": "부산광역시",
    "대구시": "대구광역시",
    "인천시": "인천광역시",
    "광주시": "광주광역시",
    "대전시": "대전광역시",
    "울산시": "울산광역시",
    "세종시": "세종특별자치시",
}


def normalize_legal_dong_address(address_name: str) -> str:
    parts = address_name.split()
    if not parts:
        return address_name
    parts[0] = REGION_NAME_ALIASES.get(parts[0], parts[0])
    return " ".join(parts)


@dataclass(frozen=True)
class LegalDong:
    code: str
    address_name: str

    @property
    def district_code(self) -> str:
        return self.code[:5]


class LegalDongClient:
    def __init__(self, api_key: str, *, timeout_seconds: float = 5.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def search(self, address_name: str) -> list[LegalDong]:
        params = {
            "ServiceKey": self.api_key,
            "pageNo": 1,
            "numOfRows": 100,
            "type": "json",
            "locatadd_nm": normalize_legal_dong_address(address_name),
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(ENDPOINT, params=params)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("StanReginCd", [])
        if len(rows) < 2:
            return []
        items = rows[1].get("row", [])
        return [
            LegalDong(
                code=str(item["region_cd"]),
                address_name=str(item["locatadd_nm"]),
            )
            for item in items
            if item.get("region_cd") and item.get("locatadd_nm")
        ]
