from agentic_nomina.utils import normalize_document, round_money


def test_normalize_document_handles_excel_numbers_and_punctuation() -> None:
    assert normalize_document(1_001_234_567.0) == "1001234567"
    assert normalize_document("1.001.234.567") == "1001234567"


def test_round_money_uses_half_up_to_configured_unit() -> None:
    assert round_money(70_049, 100) == 70_000
    assert round_money(70_050, 100) == 70_100
