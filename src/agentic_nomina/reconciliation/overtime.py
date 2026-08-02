from __future__ import annotations

from typing import Any

import pandas as pd

from agentic_nomina.models import Severity
from agentic_nomina.utils import round_money

_CONCEPTS = {
    "day": ("reported_day_hours", "overtime_day_hours", "overtime_day_value"),
    "night": ("reported_night_hours", "overtime_night_hours", "overtime_night_value"),
    "surcharge": (
        "reported_surcharge_hours",
        "night_surcharge_hours",
        "night_surcharge_value",
    ),
}

_SEVERITY_ORDER = {
    Severity.OK.value: 0,
    Severity.WARNING.value: 1,
    Severity.REVIEW.value: 2,
    Severity.BLOCKING.value: 3,
}


def _overall_severity(values: list[str]) -> str:
    return max(values, key=lambda value: _SEVERITY_ORDER[value])


def _expected_hours(reported: pd.Series, minimum: float, cap: float) -> pd.Series:
    return reported.fillna(0).clip(lower=minimum, upper=cap)


def _concept_severity(
    *,
    difference: float,
    tolerance: float,
    source_match: str,
    source_active: bool,
    payroll_active: bool,
    adjustment_applied: bool,
    capped_match_severity: str,
) -> str:
    if source_match == "left_only" and source_active:
        return Severity.BLOCKING.value
    if source_match == "right_only" and payroll_active:
        return Severity.BLOCKING.value
    if abs(difference) > tolerance:
        return Severity.REVIEW.value
    if adjustment_applied:
        return capped_match_severity
    return Severity.OK.value


def _observed_rate(value: float, hours: float) -> float | None:
    if hours <= 0:
        return None
    return value / hours


def _nonzero(value: object) -> bool:
    return not pd.isna(value) and float(value) != 0


def reconcile_overtime(
    source_frames: list[pd.DataFrame],
    payroll_frames: list[pd.DataFrame],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Compare reported overtime hours with payroll under provisional rules."""
    source = pd.concat(source_frames, ignore_index=True)
    payroll = pd.concat(payroll_frames, ignore_index=True)

    source_keys = ["period_label", "employee_id"]
    payroll_columns = [
        "period_label",
        "employee_id",
        "employee_name",
        "overtime_day_hours",
        "overtime_day_value",
        "overtime_night_hours",
        "overtime_night_value",
        "night_surcharge_hours",
        "night_surcharge_value",
        "source_file",
        "source_sheet",
        "source_row",
    ]
    payroll = payroll[[column for column in payroll_columns if column in payroll.columns]].copy()
    payroll = payroll.rename(
        columns={
            "employee_name": "employee_name_payroll",
            "source_file": "payroll_source_file",
            "source_sheet": "payroll_source_sheet",
            "source_row": "payroll_source_row",
        }
    )
    source = source.rename(columns={"employee_name": "employee_name_source"})
    merged = source.merge(payroll, how="outer", on=source_keys, indicator=True)
    merged["source_match"] = merged.pop("_merge").astype(str)

    rules = config["rules"]
    minimum = float(rules.get("minimum_hours", 0))
    tolerance = float(rules.get("hours_tolerance", 0.01))
    rounding = int(rules.get("monetary_rounding", 1))
    capped_match_severity = str(
        rules.get("adjusted_match_severity", Severity.WARNING.value)
    ).upper()

    severities: list[str] = []
    for concept, (reported_col, payroll_hours_col, payroll_value_col) in _CONCEPTS.items():
        cap = float(rules["caps_hours"][concept])
        reported = merged[reported_col].fillna(0)
        actual_hours = merged[payroll_hours_col].fillna(0)
        actual_value = merged[payroll_value_col].fillna(0)
        expected_col = f"expected_{concept}_hours"
        difference_col = f"{concept}_hours_difference"
        cap_col = f"{concept}_cap_applied"
        floor_col = f"{concept}_floor_applied"
        severity_col = f"{concept}_severity"
        observed_rate_col = f"{concept}_observed_hourly_rate"
        estimated_value_col = f"estimated_expected_{concept}_value"
        estimated_difference_col = f"estimated_{concept}_value_difference"

        merged[expected_col] = _expected_hours(reported, minimum, cap)
        merged[difference_col] = actual_hours - merged[expected_col]
        merged[cap_col] = reported.gt(cap)
        merged[floor_col] = reported.lt(minimum)

        source_active = reported.abs().gt(tolerance)
        payroll_active = actual_hours.abs().gt(tolerance) | actual_value.abs().gt(0)
        merged[severity_col] = [
            _concept_severity(
                difference=float(difference),
                tolerance=tolerance,
                source_match=str(source_match),
                source_active=bool(has_source_activity),
                payroll_active=bool(has_payroll_activity),
                adjustment_applied=bool(cap_applied or floor_applied),
                capped_match_severity=capped_match_severity,
            )
            for difference, source_match, has_source_activity, has_payroll_activity,
            cap_applied, floor_applied in zip(
                merged[difference_col],
                merged["source_match"],
                source_active,
                payroll_active,
                merged[cap_col],
                merged[floor_col],
                strict=True,
            )
        ]
        merged[observed_rate_col] = [
            _observed_rate(float(value), float(hours))
            for value, hours in zip(actual_value, actual_hours, strict=True)
        ]
        merged[estimated_value_col] = [
            round_money(float(rate) * float(expected), rounding) if rate is not None else None
            for rate, expected in zip(
                merged[observed_rate_col], merged[expected_col], strict=True
            )
        ]
        merged[estimated_difference_col] = [
            float(actual) - float(expected) if expected is not None else None
            for actual, expected in zip(actual_value, merged[estimated_value_col], strict=True)
        ]
        severities.append(severity_col)

    merged["overall_severity"] = [
        _overall_severity(list(row))
        for row in merged[severities].itertuples(index=False, name=None)
    ]
    merged["rule_id"] = str(rules.get("rule_id", "overtime_hours_cap"))
    merged["rule_version"] = str(rules.get("rule_version", "1.0"))
    merged["rule_status"] = str(rules.get("rule_status", "provisional")).upper()
    merged["review_required"] = merged["overall_severity"].ne(Severity.OK.value)

    notes: list[str] = []
    for row in merged.itertuples(index=False):
        row_notes: list[str] = []
        if row.source_match == "left_only":
            row_notes.append("Employee is present only in the overtime source")
        elif row.source_match == "right_only":
            row_notes.append("Employee is present only in payroll")
        for concept in _CONCEPTS:
            if getattr(row, f"{concept}_cap_applied"):
                row_notes.append(f"{concept} hours capped by provisional rule")
            if getattr(row, f"{concept}_floor_applied"):
                row_notes.append(f"negative {concept} hours normalized to zero")
        if _nonzero(getattr(row, "pending_day_hours", 0)):
            row_notes.append("source contains pending daytime hours")
        if _nonzero(getattr(row, "pending_night_hours", 0)):
            row_notes.append("source contains pending nighttime hours")
        if _nonzero(getattr(row, "pending_surcharge_hours", 0)):
            row_notes.append("source contains pending surcharge hours")
        if _nonzero(getattr(row, "deduct_hours", 0)):
            row_notes.append("source contains hours marked for deduction")
        notes.append("; ".join(row_notes))
    merged["notes"] = notes

    ordered = [
        "period_label",
        "employee_id",
        "employee_name_source",
        "employee_name_payroll",
        "employee_group",
        "cost_center",
        "subcost_center",
        "role",
        "source_match",
        "reported_day_hours",
        "expected_day_hours",
        "overtime_day_hours",
        "day_hours_difference",
        "day_severity",
        "reported_night_hours",
        "expected_night_hours",
        "overtime_night_hours",
        "night_hours_difference",
        "night_severity",
        "reported_surcharge_hours",
        "expected_surcharge_hours",
        "night_surcharge_hours",
        "surcharge_hours_difference",
        "surcharge_severity",
        "pending_day_hours",
        "pending_night_hours",
        "pending_surcharge_hours",
        "deduct_hours",
        "day_cap_applied",
        "night_cap_applied",
        "surcharge_cap_applied",
        "day_floor_applied",
        "night_floor_applied",
        "surcharge_floor_applied",
        "overtime_day_value",
        "day_observed_hourly_rate",
        "estimated_expected_day_value",
        "estimated_day_value_difference",
        "overtime_night_value",
        "night_observed_hourly_rate",
        "estimated_expected_night_value",
        "estimated_night_value_difference",
        "night_surcharge_value",
        "surcharge_observed_hourly_rate",
        "estimated_expected_surcharge_value",
        "estimated_surcharge_value_difference",
        "overall_severity",
        "review_required",
        "rule_id",
        "rule_version",
        "rule_status",
        "source_file",
        "source_sheet",
        "source_row",
        "payroll_source_file",
        "payroll_source_sheet",
        "payroll_source_row",
        "notes",
    ]
    for column in ordered:
        if column not in merged.columns:
            merged[column] = None
    return merged[ordered].sort_values(["period_label", "employee_id"]).reset_index(drop=True)
