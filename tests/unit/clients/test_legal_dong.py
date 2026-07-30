from app.clients.legal_dong import normalize_legal_dong_address


def test_normalize_legal_dong_address_expands_busan_abbreviation() -> None:
    assert (
        normalize_legal_dong_address("부산시 동구 수정동")
        == "부산광역시 동구 수정동"
    )


def test_normalize_legal_dong_address_expands_sejong_abbreviation() -> None:
    assert (
        normalize_legal_dong_address("세종시 조치원읍")
        == "세종특별자치시 조치원읍"
    )


def test_normalize_legal_dong_address_preserves_official_name() -> None:
    assert (
        normalize_legal_dong_address("부산광역시 동구 수정동")
        == "부산광역시 동구 수정동"
    )
