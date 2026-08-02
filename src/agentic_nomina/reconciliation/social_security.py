from __future__ import annotations

from typing import Any

import pandas as pd

from agentic_nomina.models import Severity
from agentic_nomina.utils import round_money


def _severity(diff: float, tolerance: float, missing: bool) -> str:
    if missing:
        return Severity.BLOCKING.value
    if abs(diff) <= tolerance:
        return Severity.OK.value
    return Severity.REVIEW.value


def reconcile_social_security(
    payroll_frames: list[pd.DataFrame],
    pila: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    payroll = pd.concat(payroll_frames, ignore_index=True)
    payroll_agg = payroll.groupby("employee_id", as_index=False).agg(
        employee_name_payroll=("employee_name", "first"),
        payroll_salary_days=("salary_days", "sum"),
        payroll_health=("health_employee", "sum"),
        payroll_pension=("pension_employee", "sum"),
    )
    merged = payroll_agg.merge(pila, how="outer", on="employee_id", indicator=True)

    rate_health = float(config["health_employee_rate"])
    rate_pension = float(config["pension_employee_rate"])
    rounding = int(config["monetary_rounding"])
    tolerance = float(config["monetary_tolerance"])
    days_tolerance = float(config.get("days_tolerance", 0))

    merged["expected_health_from_ibc"] = merged["health_ibc"].fillna(0).map(
        lambda value: round_money(value * rate_health, rounding)
    )
    merged["expected_pension_from_ibc"] = merged["pension_ibc"].fillna(0).map(
        lambda value: round_money(value * rate_pension, rounding)
    )
    merged["health_difference"] = merged["payroll_health"].fillna(0) - merged["expected_health_from_ibc"]
    merged["pension_difference"] = merged["payroll_pension"].fillna(0) - merged["expected_pension_from_ibc"]
    merged["days_difference"] = merged["payroll_salary_days"].fillna(0) - merged["health_days"].fillna(0)

    missing = merged["_merge"].ne("both")
    merged["health_severity"] = [
        _severity(diff, tolerance, bool(is_missing))
        for diff, is_missing in zip(merged["health_difference"], missing, strict=True)
    ]
    merged["pension_severity"] = [
        _severity(diff, tolerance, bool(is_missing))
        for diff, is_missing in zip(merged["pension_difference"], missing, strict=True)
    ]
    merged["days_severity"] = [
        _severity(diff, days_tolerance, bool(is_missing))
        for diff, is_missing in zip(merged["days_difference"], missing, strict=True)
    ]
    merged["source_match"] = merged.pop("_merge").astype(str)
    return merged.sort_values(["source_match", "employee_id"]).reset_index(drop=True)
