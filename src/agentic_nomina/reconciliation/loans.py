from __future__ import annotations

from typing import Any

import pandas as pd

from agentic_nomina.models import Severity


def _payroll_view(payroll: pd.DataFrame) -> pd.DataFrame:
    required = [
        "employee_id",
        "employee_name",
        "loan_value",
        "source_file",
        "source_sheet",
        "source_row",
    ]
    missing = [column for column in required if column not in payroll.columns]
    if missing:
        raise ValueError(f"Payroll loan fields are unavailable: {', '.join(missing)}")
    return payroll[required].rename(
        columns={
            "employee_name": "employee_name_payroll",
            "loan_value": "actual_value",
            "source_file": "payroll_source_file",
            "source_sheet": "payroll_source_sheet",
            "source_row": "payroll_source_row",
        }
    )


def _next_balance_view(next_report: pd.DataFrame) -> pd.DataFrame:
    return next_report[
        ["employee_id", "opening_balance", "source_file", "source_page", "source_row"]
    ].rename(
        columns={
            "opening_balance": "next_opening_balance",
            "source_file": "next_source_file",
            "source_page": "next_source_page",
            "source_row": "next_source_row",
        }
    )


def reconcile_loan_balances(
    report: pd.DataFrame,
    payroll: pd.DataFrame,
    rules_config: dict[str, Any],
    *,
    next_report: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Reconcile payroll loan deductions through consecutive report balances."""
    report_view = report.rename(columns={"employee_name": "employee_name_source"}).copy()
    merged = report_view.merge(
        _payroll_view(payroll), how="outer", on="employee_id", indicator=True
    )
    merged["source_match"] = merged.pop("_merge").astype(str)
    merged["actual_value"] = merged["actual_value"].fillna(0.0).abs()
    tolerance = float(rules_config.get("monetary_tolerance", 0))
    merged = merged[
        ~((merged["source_match"] == "right_only") & merged["actual_value"].le(tolerance))
    ].copy()

    has_next_cutoff = next_report is not None
    if next_report is not None:
        merged = merged.merge(_next_balance_view(next_report), how="left", on="employee_id")
        merged["next_opening_balance"] = merged["next_opening_balance"].fillna(0.0)
        merged["expected_value"] = (
            merged["reported_balance"].fillna(0.0) - merged["next_opening_balance"]
        )
        merged["difference"] = merged["actual_value"] - merged["expected_value"]
        merged["balance_status"] = "RECONCILED"
    else:
        merged["next_opening_balance"] = pd.NA
        merged["expected_value"] = pd.NA
        merged["difference"] = pd.NA
        merged["balance_status"] = "PENDING_NEXT_CUTOFF"
        merged["next_source_file"] = None
        merged["next_source_page"] = None
        merged["next_source_row"] = None

    merged["projected_closing_balance"] = (
        merged["reported_balance"].fillna(0.0) - merged["actual_value"]
    )
    severities: list[str] = []
    notes: list[str] = []
    for record in merged.to_dict(orient="records"):
        source_match = str(record["source_match"])
        actual = float(record["actual_value"] or 0)
        projected = float(record["projected_closing_balance"] or 0)

        if source_match == "right_only" and actual > tolerance:
            severities.append(Severity.BLOCKING.value)
            notes.append("Payroll loan deduction has no matching balance-report employee")
            continue
        if projected < -tolerance:
            severities.append(Severity.BLOCKING.value)
            notes.append("Payroll deduction exceeds the reported employee loan balance")
            continue
        if not has_next_cutoff:
            severities.append(Severity.WARNING.value)
            notes.append("Next cutoff balance report is required to validate the deduction")
            continue

        expected = float(record["expected_value"] or 0)
        difference = float(record["difference"] or 0)
        if expected < -tolerance:
            severities.append(Severity.REVIEW.value)
            notes.append("Next opening balance exceeds the prior reported balance")
        elif source_match == "left_only" and expected > tolerance:
            severities.append(Severity.BLOCKING.value)
            notes.append("Expected balance reduction has no matching payroll employee")
        elif abs(difference) > tolerance:
            severities.append(Severity.REVIEW.value)
            notes.append("Payroll loan deduction differs from the balance movement")
        else:
            severities.append(Severity.OK.value)
            notes.append("")

    merged["severity"] = severities
    merged["review_required"] = merged["severity"].ne(Severity.OK.value)
    merged["rule_id"] = str(
        rules_config.get("rule_id", "employee_loan_balance_movement")
    )
    merged["rule_version"] = str(rules_config.get("rule_version", "1.0"))
    merged["rule_status"] = str(
        rules_config.get("rule_status", "provisional")
    ).upper()
    merged["notes"] = notes

    ordered = [
        "period_label",
        "employee_id",
        "employee_name_source",
        "employee_name_payroll",
        "source_match",
        "opening_balance",
        "period_debits",
        "period_credits",
        "reported_balance",
        "next_opening_balance",
        "expected_value",
        "actual_value",
        "difference",
        "projected_closing_balance",
        "balance_status",
        "severity",
        "review_required",
        "rule_id",
        "rule_version",
        "rule_status",
        "movement_count",
        "movement_references",
        "source_file",
        "source_page",
        "source_row",
        "source_total_page",
        "source_total_row",
        "next_source_file",
        "next_source_page",
        "next_source_row",
        "payroll_source_file",
        "payroll_source_sheet",
        "payroll_source_row",
        "notes",
    ]
    for column in ordered:
        if column not in merged.columns:
            merged[column] = None
    return merged[ordered].sort_values(["period_label", "employee_id"]).reset_index(drop=True)
