from decimal import Decimal, InvalidOperation

import httpx


ENDPOINT = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"
TABLE_IDS = {
    "apartment": "A_2024_00156",
    "row_house": "A_2024_00157",
    "multi_family": "A_2024_00157",
    "detached_house": "A_2024_00158",
    "multi_household": "A_2024_00158",
    "officetel": "T241163133546529",
}


class ROneClient:
    def __init__(self, api_key: str, *, timeout_seconds: float = 5.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def conversion_rate(
        self,
        property_type: str,
        district_name: str,
        year_month: str,
    ) -> Decimal | None:
        rate = await self._query(
            TABLE_IDS[property_type],
            district_name,
            year_month,
        )
        if rate is not None:
            return rate
        return await self._query(
            "A_2024_00155",
            district_name,
            year_month,
        )

    async def _query(
        self,
        table_id: str,
        district_name: str,
        year_month: str,
    ) -> Decimal | None:
        params = {
            "KEY": self.api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 1000,
            "STATBL_ID": table_id,
            "DTACYCLE_CD": "MM",
            "WRTTIME_IDTFR_ID": year_month,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(ENDPOINT, params=params)
        response.raise_for_status()
        payload = response.json().get("SttsApiTblData", [])
        if len(payload) < 2:
            return None
        rows = payload[1].get("row", [])
        for row in rows:
            names = (
                str(row.get("CLS_NM") or ""),
                str(row.get("CLS_FULLNM") or ""),
            )
            if not any(district_name in name for name in names):
                continue
            try:
                return Decimal(str(row["DTA_VAL"]))
            except (KeyError, InvalidOperation):
                continue
        return None
