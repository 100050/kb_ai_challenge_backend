import asyncio
from decimal import Decimal

from app.clients.r_one import ROneClient


class RecordingROneClient(ROneClient):
    def __init__(self, values: dict[tuple[str, str], Decimal | None]) -> None:
        super().__init__("test-key")
        self.values = values
        self.calls: list[tuple[str, str]] = []

    async def _query(
        self,
        table_id: str,
        district_name: str,
        year_month: str,
    ) -> Decimal | None:
        self.calls.append((table_id, district_name))
        return self.values.get((table_id, district_name))


def test_conversion_rate_falls_back_to_parent_region_for_same_property_type(
) -> None:
    client = RecordingROneClient(
        {("A_2024_00157", "서울"): Decimal("4.9")},
    )

    result = asyncio.run(
        client.conversion_rate(
            "row_house",
            "종로구",
            "202605",
            parent_region_name="서울",
        ),
    )

    assert result == Decimal("4.9")
    assert client.calls == [
        ("A_2024_00157", "종로구"),
        ("A_2024_00157", "서울"),
    ]


def test_conversion_rate_uses_comprehensive_table_after_type_fallbacks(
) -> None:
    client = RecordingROneClient(
        {("A_2024_00155", "서울"): Decimal("5.8")},
    )

    result = asyncio.run(
        client.conversion_rate(
            "row_house",
            "종로구",
            "202605",
            parent_region_name="서울",
        ),
    )

    assert result == Decimal("5.8")
    assert client.calls == [
        ("A_2024_00157", "종로구"),
        ("A_2024_00157", "서울"),
        ("A_2024_00155", "종로구"),
        ("A_2024_00155", "서울"),
    ]
