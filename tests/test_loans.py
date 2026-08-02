import pandas as pd

from agentic_nomina.adapters.loans import parse_loan_balance_text
from agentic_nomina.reconciliation.loans import reconcile_loan_balances


def _payroll(employee_id: str, loan_value: float) -> dict[str, object]:
    return {
        "employee_id": employee_id,
        "employee_name": "Employee",
        "loan_value": loan_value,
        "source_file": "payroll.xlsx",
        "source_sheet": "Hoja1",
        "source_row": 10,
    }


def _report(
    employee_id: str,
    *,
    period_label: str,
    opening: float,
    debits: float,
    balance: float,
) -> dict[str, object]:
    return {
        "period_label": period_label,
        "employee_id": employee_id,
        "employee_name": "Employee",
        "opening_balance": opening,
        "period_debits": debits,
        "period_credits": 0.0,
        "reported_balance": balance,
        "movement_count": int(debits > 0),
        "movement_references": "G-004-1" if debits else "",
        "source_file": f"loans-{period_label}.pdf",
        "source_page": 1,
        "source_row": 5,
        "source_total_page": 1,
        "source_total_row": 7,
    }


def _rules() -> dict[str, object]:
    return {
        "rule_id": "employee_loan_balance_movement",
        "rule_version": "1.0",
        "rule_status": "provisional",
        "monetary_tolerance": 0,
    }


def test_loan_parser_reads_opening_debit_and_reported_balance() -> None:
    pages = [
        (
            "900000003 PERSONA PRUEBA TRES C U E N T A: 13659500 "
            "PRESTAMOS A TRABAJADORES 249,999.00\n"
            "G-001-00000024324-001 2026/02/11 PRESTAMO DESCONTAR 40 "
            "400,000.00 649,999.00\n"
            "TOTAL 400,000.00 649,999.00"
        )
    ]

    result = parse_loan_balance_text(
        pages, source_file="loans.pdf", period_label="Q1"
    ).iloc[0]

    assert result["employee_id"] == "900000003"
    assert result["opening_balance"] == 249_999
    assert result["period_debits"] == 400_000
    assert result["reported_balance"] == 649_999
    assert result["movement_count"] == 1


def test_loan_reconciliation_matches_balance_reduction() -> None:
    current = pd.DataFrame(
        [_report("1", period_label="Q1", opening=249_999, debits=400_000, balance=649_999)]
    )
    next_report = pd.DataFrame(
        [_report("1", period_label="Q2", opening=249_999, debits=0, balance=249_999)]
    )
    payroll = pd.DataFrame([_payroll("1", 400_000)])

    result = reconcile_loan_balances(
        current, payroll, _rules(), next_report=next_report
    ).iloc[0]

    assert result["expected_value"] == 400_000
    assert result["actual_value"] == 400_000
    assert result["difference"] == 0
    assert result["severity"] == "OK"
    assert result["balance_status"] == "RECONCILED"


def test_loan_reconciliation_treats_absent_next_record_as_zero_balance() -> None:
    current = pd.DataFrame(
        [_report("1", period_label="Q1", opening=50_000, debits=0, balance=50_000)]
    )
    next_report = pd.DataFrame(
        [_report("2", period_label="Q2", opening=0, debits=100_000, balance=100_000)]
    )
    payroll = pd.DataFrame([_payroll("1", 50_000)])

    result = reconcile_loan_balances(
        current, payroll, _rules(), next_report=next_report
    ).iloc[0]

    assert result["next_opening_balance"] == 0
    assert result["expected_value"] == 50_000
    assert result["severity"] == "OK"


def test_loan_reconciliation_marks_last_period_pending() -> None:
    current = pd.DataFrame(
        [_report("1", period_label="Q2", opening=100_000, debits=0, balance=100_000)]
    )
    payroll = pd.DataFrame([_payroll("1", 50_000)])

    result = reconcile_loan_balances(current, payroll, _rules()).iloc[0]

    assert pd.isna(result["expected_value"])
    assert result["projected_closing_balance"] == 50_000
    assert result["balance_status"] == "PENDING_NEXT_CUTOFF"
    assert result["severity"] == "WARNING"
    assert result["review_required"]


def test_loan_reconciliation_blocks_unsubstantiated_payroll_deduction() -> None:
    current = pd.DataFrame(
        [_report("2", period_label="Q1", opening=50_000, debits=0, balance=50_000)]
    )
    payroll = pd.DataFrame([_payroll("1", 50_000)])

    result = reconcile_loan_balances(current, payroll, _rules())
    payroll_only = result.loc[result["employee_id"].eq("1")].iloc[0]

    assert payroll_only["severity"] == "BLOCKING"
