from dataclasses import dataclass

import httpx


ENDPOINT = (
    "https://apis.data.go.kr/1741000/"
    "StanReginCd/getStanReginCdList"
)


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
            "locatadd_nm": address_name,
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
