import pandas as pd

from agentic_nomina.adapters.external_deductions import (
    parse_comfatolima_text,
    parse_los_olivos_text,
)
from agentic_nomina.reconciliation.external_deductions import (
    reconcile_external_deduction,
)


def _payroll(employee_id: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "employee_id": employee_id,
        "employee_name": "Employee",
        "los_olivos_value": 0.0,
        "comfatolima_value": 0.0,
        "source_file": "payroll.xlsx",
        "source_sheet": "Hoja1",
        "source_row": 10,
    }
    row.update(overrides)
    return row


def _rules() -> dict[str, object]:
    return {
        "rule_version": "1.0",
        "rule_status": "provisional",
        "monetary_tolerance": 0,
    }


def test_los_olivos_parser_reads_primary_affiliate_total() -> None:
    pages = [
        "ACOSTA MOLINA EFRAIN93085376CCT -  28/02/2026  18.500  "
        "21.60001/02/2026   COBRO  0  0"
    ]

    result = parse_los_olivos_text(pages, source_file="olivos.pdf").iloc[0]

    assert result["employee_id"] == "93085376"
    assert result["employee_name"] == "ACOSTA MOLINA EFRAIN"
    assert result["expected_value"] == 21_600
    assert result["base_value"] == 18_500
    assert result["source_page"] == 1


def test_comfatolima_parser_reads_february_expected_value() -> None:
    pages = [
        "14377 93085383 AYALA GUZMAN RUBIEL $ 4.000.000 30/04/2025 "
        "31/03/2026 $355.395 $ 355.395 $ 355.395 $ 355.395 $ 355.395 $ 1.421.580"
    ]

    result = parse_comfatolima_text(pages, source_file="comfatolima.pdf").iloc[0]

    assert result["employee_id"] == "93085383"
    assert result["expected_value"] == 355_395
    assert result["installment"] == 355_395
    assert result["arrears"] == 1_421_580


def test_external_deduction_matches_and_classifies_exceptions() -> None:
    source = pd.DataFrame(
        [
            {
                "provider": "COMFATOLIMA",
                "period_label": "MONTH",
                "employee_id": "1",
                "employee_name": "Exact",
                "expected_value": 188_294.0,
                "source_file": "credits.pdf",
                "source_page": 1,
                "source_row": 10,
                "source_reference": "101",
            },
            {
                "provider": "COMFATOLIMA",
                "period_label": "MONTH",
                "employee_id": "2",
                "employee_name": "Missing payroll",
                "expected_value": 177_698.0,
                "source_file": "credits.pdf",
                "source_page": 1,
                "source_row": 11,
                "source_reference": "102",
            },
            {
                "provider": "COMFATOLIMA",
                "period_label": "MONTH",
                "employee_id": "3",
                "employee_name": "Mismatch",
                "expected_value": 188_294.0,
                "source_file": "credits.pdf",
                "source_page": 1,
                "source_row": 12,
                "source_reference": "103",
            },
        ]
    )
    payroll = pd.DataFrame(
        [
            _payroll("1", comfatolima_value=188_294.0),
            _payroll("3", comfatolima_value=0.0),
        ]
    )
    provider_config = {
        "provider": "COMFATOLIMA",
        "payroll_field": "comfatolima_value",
        "rule_id": "comfatolima_expected_installment",
        "period_label": "MONTH",
    }

    result = reconcile_external_deduction(
        source, payroll, provider_config, _rules()
    ).set_index("employee_id")

    assert result.at["1", "severity"] == "OK"
    assert result.at["2", "severity"] == "BLOCKING"
    assert result.at["3", "severity"] == "REVIEW"


def test_external_deduction_marks_value_difference_for_matched_employee() -> None:
    source = pd.DataFrame(
        [
            {
                "provider": "LOS_OLIVOS",
                "period_label": "MONTH",
                "employee_id": "1",
                "employee_name": "Mismatch",
                "expected_value": 24_400.0,
                "source_file": "olivos.pdf",
                "source_page": 1,
                "source_row": 15,
                "source_reference": None,
            }
        ]
    )
    payroll = pd.DataFrame([_payroll("1", los_olivos_value=18_500.0)])
    provider_config = {
        "provider": "LOS_OLIVOS",
        "payroll_field": "los_olivos_value",
        "rule_id": "los_olivos_monthly_invoice",
        "period_label": "MONTH",
    }

    result = reconcile_external_deduction(
        source, payroll, provider_config, _rules()
    ).iloc[0]

    assert result["difference"] == -5_900
    assert result["severity"] == "REVIEW"
    assert result["review_required"]
