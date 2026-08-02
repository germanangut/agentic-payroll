import pandas as pd

from agentic_nomina.adapters.overtime import load_overtime_summary
from agentic_nomina.reconciliation.overtime import reconcile_overtime


def _config() -> dict[str, object]:
    return {
        "rules": {
            "rule_id": "overtime_hours_cap",
            "rule_version": "1.0",
            "rule_status": "provisional",
            "minimum_hours": 0,
            "caps_hours": {"day": 24, "night": 24, "surcharge": 24},
            "hours_tolerance": 0.01,
            "monetary_rounding": 1,
            "adjusted_match_severity": "WARNING",
        }
    }


def _source_row(employee_id: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "period_label": "Q1",
        "employee_id": employee_id,
        "employee_name": "Ana",
        "employee_group": "51",
        "cost_center": "1",
        "subcost_center": "4",
        "role": "Operaria",
        "reported_day_hours": 0.0,
        "reported_night_hours": 0.0,
        "reported_surcharge_hours": 0.0,
        "pending_day_hours": 0.0,
        "pending_night_hours": 0.0,
        "pending_surcharge_hours": 0.0,
        "deduct_hours": 0.0,
        "source_file": "overtime.xlsx",
        "source_sheet": "TOTAL HORAS EXTRAS",
        "source_row": 3,
    }
    row.update(overrides)
    return row


def _payroll_row(employee_id: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "period_label": "Q1",
        "employee_id": employee_id,
        "employee_name": "Ana",
        "overtime_day_hours": 0.0,
        "overtime_day_value": 0.0,
        "overtime_night_hours": 0.0,
        "overtime_night_value": 0.0,
        "night_surcharge_hours": 0.0,
        "night_surcharge_value": 0.0,
        "source_file": "payroll.xlsx",
        "source_sheet": "Hoja1",
        "source_row": 10,
    }
    row.update(overrides)
    return row


def test_overtime_applies_provisional_cap_and_marks_warning() -> None:
    source = pd.DataFrame([_source_row("1", reported_day_hours=30.0)])
    payroll = pd.DataFrame(
        [_payroll_row("1", overtime_day_hours=24.0, overtime_day_value=240_000.0)]
    )

    result = reconcile_overtime([source], [payroll], _config()).iloc[0]

    assert result["expected_day_hours"] == 24.0
    assert result["day_hours_difference"] == 0.0
    assert result["day_cap_applied"]
    assert result["day_severity"] == "WARNING"
    assert result["overall_severity"] == "WARNING"
    assert result["review_required"]


def test_overtime_classifies_mismatch_and_missing_active_source() -> None:
    source = pd.DataFrame(
        [
            _source_row("1", reported_day_hours=15.0),
            _source_row("2", reported_day_hours=8.0),
        ]
    )
    payroll = pd.DataFrame(
        [
            _payroll_row("1", overtime_day_hours=11.0, overtime_day_value=110_000.0),
            _payroll_row("3", overtime_day_hours=4.0, overtime_day_value=40_000.0),
        ]
    )

    result = reconcile_overtime([source], [payroll], _config()).set_index("employee_id")

    assert result.at["1", "day_severity"] == "REVIEW"
    assert result.at["2", "day_severity"] == "BLOCKING"
    assert result.at["3", "day_severity"] == "BLOCKING"


def test_overtime_adapter_reads_configured_summary_columns(tmp_path) -> None:
    workbook = tmp_path / "overtime.xlsx"
    raw = pd.DataFrame([[None] * 60 for _ in range(4)])
    raw.iloc[1, 0] = "CEDULA"
    raw.iloc[1, 1] = "Nombre y Apellido"
    raw.iloc[2, 0] = 1_001_234_567
    raw.iloc[2, 1] = "Ana Example"
    raw.iloc[2, 51] = 30
    raw.iloc[2, 52] = 2
    raw.iloc[2, 53] = 3
    raw.iloc[2, 55] = 1
    raw.iloc[2, 59] = 4
    raw.to_excel(workbook, sheet_name="TOTAL HORAS EXTRAS", header=False, index=False)

    source_config = {
        "sheet_name": "TOTAL HORAS EXTRAS",
        "header_row_zero_based": 1,
        "columns_zero_based": {
            "employee_id": 0,
            "employee_name": 1,
            "group": 2,
            "cost_center": 3,
            "subcost_center": 4,
            "role": 5,
            "reported_day_hours": 51,
            "reported_night_hours": 52,
            "reported_surcharge_hours": 53,
            "pending_day_hours": 55,
            "pending_night_hours": 56,
            "pending_surcharge_hours": 57,
            "deduct_hours": 59,
        },
    }

    result = load_overtime_summary(workbook, source_config, "Q1").iloc[0]

    assert result["employee_id"] == "1001234567"
    assert result["reported_day_hours"] == 30
    assert result["pending_day_hours"] == 1
    assert result["deduct_hours"] == 4
    assert result["source_row"] == 3
