from __future__ import annotations

from typing import Any

import pandas as pd

from agentic_nomina.models import Severity


def _join_values(values: pd.Series) -> str:
    return ", ".join(dict.fromkeys(str(value) for value in values if pd.notna(value)))


def _aggregate_source(source: pd.DataFrame) -> pd.DataFrame:
    aggregations: dict[str, object] = {
        "employee_name": "first",
        "expected_value": "sum",
        "source_file": _join_values,
        "source_page": _join_values,
        "source_row": _join_values,
        "source_reference": _join_values,
    }
    optional = [
        "base_value",
        "credit_id",
        "principal",
        "installment",
        "arrears",
        "period_start",
        "period_end",
        "start_date",
        "end_date",
    ]
    for column in optional:
        if column in source.columns:
            aggregations[column] = "sum" if column in {"base_value", "principal", "arrears"} else _join_values
    return (
        source.groupby(["provider", "period_label", "employee_id"], as_index=False)
        .agg(aggregations)
        .rename(columns={"employee_name": "employee_name_source"})
    )


def _severity(
    *, source_match: str, expected: float, actual: float, difference: float, tolerance: float
) -> str:
    source_active = abs(expected) > tolerance
    payroll_active = abs(actual) > tolerance
    if source_match == "left_only" and source_active:
        return Severity.BLOCKING.value
    if source_match == "right_only" and payroll_active:
        return Severity.BLOCKING.value
    if abs(difference) > tolerance:
        return Severity.REVIEW.value
    return Severity.OK.value


def reconcile_external_deduction(
    source: pd.DataFrame,
    payroll: pd.DataFrame,
    provider_config: dict[str, Any],
    rules_config: dict[str, Any],
) -> pd.DataFrame:
    """Compare a provider's expected monthly deduction with payroll."""
    source = _aggregate_source(source)
    payroll_field = str(provider_config["payroll_field"])
    if payroll_field not in payroll.columns:
        raise ValueError(f"Payroll field is unavailable for external deduction: {payroll_field}")

    payroll_view = payroll[
        [
            "employee_id",
            "employee_name",
            payroll_field,
            "source_file",
            "source_sheet",
            "source_row",
        ]
    ].copy()
    payroll_view = payroll_view.rename(
        columns={
            "employee_name": "employee_name_payroll",
            payroll_field: "actual_value",
            "source_file": "payroll_source_file",
            "source_sheet": "payroll_source_sheet",
            "source_row": "payroll_source_row",
        }
    )

    merged = source.merge(payroll_view, how="outer", on="employee_id", indicator=True)
    merged["source_match"] = merged.pop("_merge").astype(str)
    merged["provider"] = merged["provider"].fillna(str(provider_config.get("provider", "")))
    merged["period_label"] = merged["period_label"].fillna(
        str(provider_config.get("period_label", "MONTH"))
    )
    merged["expected_value"] = merged["expected_value"].fillna(0.0)
    merged["actual_value"] = merged["actual_value"].fillna(0.0).abs()
    merged["difference"] = merged["actual_value"] - merged["expected_value"]

    tolerance = float(rules_config.get("monetary_tolerance", 0))
    merged = merged[
        ~((merged["source_match"] == "right_only") & merged["actual_value"].abs().le(tolerance))
    ].copy()
    merged["severity"] = [
        _severity(
            source_match=str(source_match),
            expected=float(expected),
            actual=float(actual),
            difference=float(difference),
            tolerance=tolerance,
        )
        for source_match, expected, actual, difference in zip(
            merged["source_match"],
            merged["expected_value"],
            merged["actual_value"],
            merged["difference"],
            strict=True,
        )
    ]
    merged["review_required"] = merged["severity"].ne(Severity.OK.value)
    merged["rule_id"] = str(provider_config["rule_id"])
    merged["rule_version"] = str(rules_config.get("rule_version", "1.0"))
    merged["rule_status"] = str(rules_config.get("rule_status", "provisional")).upper()
    merged["notes"] = [
        "Provider record has no payroll employee match"
        if source_match == "left_only" and abs(float(expected)) > tolerance
        else "Payroll deduction has no provider record"
        if source_match == "right_only" and abs(float(actual)) > tolerance
        else "Expected provider deduction differs from payroll"
        if abs(float(difference)) > tolerance
        else ""
        for source_match, expected, actual, difference in zip(
            merged["source_match"],
            merged["expected_value"],
            merged["actual_value"],
            merged["difference"],
            strict=True,
        )
    ]

    ordered = [
        "provider",
        "period_label",
        "employee_id",
        "employee_name_source",
        "employee_name_payroll",
        "source_match",
        "expected_value",
        "actual_value",
        "difference",
        "severity",
        "review_required",
        "rule_id",
        "rule_version",
        "rule_status",
        "credit_id",
        "principal",
        "installment",
        "arrears",
        "base_value",
        "period_start",
        "period_end",
        "start_date",
        "end_date",
        "source_reference",
        "source_file",
        "source_page",
        "source_row",
        "payroll_source_file",
        "payroll_source_sheet",
        "payroll_source_row",
        "notes",
    ]
    for column in ordered:
        if column not in merged.columns:
            merged[column] = None
    return merged[ordered].sort_values(["provider", "employee_id"]).reset_index(drop=True)
