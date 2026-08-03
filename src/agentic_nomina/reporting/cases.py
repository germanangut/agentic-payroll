from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

_SEVERITY_RANK = {"OK": 0, "WARNING": 1, "REVIEW": 2, "EXCEPTION": 3, "BLOCKING": 3}


def _value(record: dict[str, object], *columns: str) -> object:
    for column in columns:
        value = record.get(column)
        if value is not None and not pd.isna(value) and str(value).strip():
            return value
    return ""


def _control(
    record: dict[str, object],
    *,
    module: str,
    period: str,
    control: str,
    severity_column: str,
) -> dict[str, object]:
    return {
        "employee_id": str(record.get("employee_id") or ""),
        "employee_name": _value(
            record,
            "employee_name_payroll",
            "employee_name_source",
            "employee_name_list",
            "employee_name",
        ),
        "module": module,
        "period_label": period,
        "control": control,
        "severity": str(record.get(severity_column) or "OK"),
    }


def _employee_controls(employee_results: dict[str, pd.DataFrame]) -> Iterable[dict[str, object]]:
    for period, frame in employee_results.items():
        for record in frame.to_dict(orient="records"):
            yield _control(
                record,
                module="EMPLOYEES",
                period=period,
                control=str(record.get("outcome") or "employee_membership"),
                severity_column="severity",
            )


def _social_controls(social: pd.DataFrame) -> Iterable[dict[str, object]]:
    for record in social.to_dict(orient="records"):
        for control in ("health", "pension", "days"):
            yield _control(
                record,
                module="SOCIAL_SECURITY",
                period="MONTH",
                control=control,
                severity_column=f"{control}_severity",
            )


def _overtime_controls(overtime: pd.DataFrame) -> Iterable[dict[str, object]]:
    for record in overtime.to_dict(orient="records"):
        for control in ("day", "night", "surcharge"):
            yield _control(
                record,
                module="OVERTIME",
                period=str(record.get("period_label") or ""),
                control=f"{control}_hours",
                severity_column=f"{control}_severity",
            )


def _single_controls(
    frames: Iterable[pd.DataFrame], *, module_column: str, default_module: str, control: str
) -> Iterable[dict[str, object]]:
    for frame in frames:
        for record in frame.to_dict(orient="records"):
            yield _control(
                record,
                module=str(record.get(module_column) or default_module),
                period=str(record.get("period_label") or ""),
                control=control,
                severity_column="severity",
            )


def build_employee_case_file(
    employee_results: dict[str, pd.DataFrame],
    social: pd.DataFrame,
    overtime: pd.DataFrame | None = None,
    external_deductions: dict[str, pd.DataFrame] | None = None,
    loans: pd.DataFrame | None = None,
    absences: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build one auditable summary row per employee across every enabled control."""
    rows = [*_employee_controls(employee_results), *_social_controls(social)]
    if overtime is not None:
        rows.extend(_overtime_controls(overtime))
    if external_deductions:
        rows.extend(
            _single_controls(
                external_deductions.values(),
                module_column="provider",
                default_module="EXTERNAL_DEDUCTION",
                control="monthly_deduction",
            )
        )
    if loans is not None:
        rows.extend(
            _single_controls(
                [loans],
                module_column="",
                default_module="EMPLOYEE_LOANS",
                control="balance_movement",
            )
        )
    if absences is not None:
        rows.extend(_single_controls([absences], module_column="", default_module="ABSENCES", control="reported_vs_paid"))

    columns = [
        "employee_id",
        "employee_name",
        "overall_severity",
        "review_required",
        "total_controls",
        "ok_controls",
        "warning_controls",
        "review_controls",
        "blocking_controls",
        "modules",
        "periods",
        "exception_controls",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    controls = pd.DataFrame(rows)
    cases: list[dict[str, object]] = []
    for employee_id, group in controls.groupby("employee_id", sort=True):
        severities = group["severity"].value_counts().to_dict()
        overall = max(group["severity"], key=lambda value: _SEVERITY_RANK.get(value, 0))
        exceptions = group.loc[group["severity"].ne("OK")]
        exception_controls = "; ".join(
            f"{row.module}/{row.period_label}/{row.control}:{row.severity}"
            for row in exceptions.itertuples(index=False)
        )
        cases.append(
            {
                "employee_id": employee_id,
                "employee_name": next(
                    (str(value) for value in group["employee_name"] if str(value).strip()), ""
                ),
                "overall_severity": overall,
                "review_required": overall != "OK",
                "total_controls": len(group),
                "ok_controls": severities.get("OK", 0),
                "warning_controls": severities.get("WARNING", 0),
                "review_controls": severities.get("REVIEW", 0),
                "blocking_controls": severities.get("BLOCKING", 0),
                "modules": ", ".join(sorted(set(group["module"]))),
                "periods": ", ".join(sorted(set(group["period_label"]))),
                "exception_controls": exception_controls,
            }
        )
    return pd.DataFrame(cases, columns=columns)
