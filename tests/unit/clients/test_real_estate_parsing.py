from app.clients.real_estate import parse_rent_transactions


def test_parse_apartment_rent_transactions_normalizes_xml() -> None:
    xml = """
    <response>
      <header><resultCode>000</resultCode></header>
      <body><items><item>
        <보증금액> 10,000 </보증금액>
        <월세금액> 70 </월세금액>
        <전용면적>59.8</전용면적>
        <계약년월>202506</계약년월>
        <계약일>15</계약일>
      </item></items></body>
    </response>
    """

    result = parse_rent_transactions(xml)

    assert len(result) == 1
    assert result[0].deposit == 100_000_000
    assert result[0].monthly_rent == 700_000
    assert result[0].exclusive_area_m2 == 59.8
    assert result[0].contract_date.isoformat() == "2025-06-15"

