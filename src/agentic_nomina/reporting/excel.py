from __future__ import annotations

from pathlib import Path

import pandas as pd

from agentic_nomina.reporting.cases import build_employee_case_file
from agentic_nomina.reporting.reviews import apply_review_ledger, review_sheet


def _summary_frame(
    employee_results: dict[str, pd.DataFrame],
    social: pd.DataFrame,
    overtime: pd.DataFrame | None,
    external_deductions: dict[str, pd.DataFrame] | None,
    loans: pd.DataFrame | None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label, frame in employee_results.items():
        counts = frame["severity"].value_counts().to_dict()
        rows.append(
            {
                "module": f"Employees {label}",
                "total": len(frame),
                "ok": counts.get("OK", 0),
                "warning": counts.get("WARNING", 0),
                "review": counts.get("REVIEW", 0),
                "blocking": counts.get("BLOCKING", 0),
            }
        )
    social_statuses = social[["health_severity", "pension_severity", "days_severity"]].stack()
    counts = social_statuses.value_counts().to_dict()
    rows.append(
        {
            "module": "Social security controls",
            "total": len(social_statuses),
            "ok": counts.get("OK", 0),
            "warning": counts.get("WARNING", 0),
            "review": counts.get("REVIEW", 0),
            "blocking": counts.get("BLOCKING", 0),
        }
    )
    if overtime is not None:
        overtime_statuses = overtime[
            ["day_severity", "night_severity", "surcharge_severity"]
        ].stack()
        counts = overtime_statuses.value_counts().to_dict()
        rows.append(
            {
                "module": "Overtime controls",
                "total": len(overtime_statuses),
                "ok": counts.get("OK", 0),
                "warning": counts.get("WARNING", 0),
                "review": counts.get("REVIEW", 0),
                "blocking": counts.get("BLOCKING", 0),
            }
        )
    for label, frame in (external_deductions or {}).items():
        counts = frame["severity"].value_counts().to_dict()
        rows.append(
            {
                "module": f"External deduction: {label}",
                "total": len(frame),
                "ok": counts.get("OK", 0),
                "warning": counts.get("WARNING", 0),
                "review": counts.get("REVIEW", 0),
                "blocking": counts.get("BLOCKING", 0),
            }
        )
    if loans is not None:
        counts = loans["severity"].value_counts().to_dict()
        rows.append(
            {
                "module": "Employee loan balances",
                "total": len(loans),
                "ok": counts.get("OK", 0),
                "warning": counts.get("WARNING", 0),
                "review": counts.get("REVIEW", 0),
                "blocking": counts.get("BLOCKING", 0),
            }
        )
    return pd.DataFrame(rows)


def _social_exceptions(social: pd.DataFrame) -> list[dict[str, object]]:
    controls = {
        "health": (
            "expected_health_from_ibc",
            "payroll_health",
            "health_difference",
            "health_severity",
        ),
        "pension": (
            "expected_pension_from_ibc",
            "payroll_pension",
            "pension_difference",
            "pension_severity",
        ),
        "days": (
            "health_days",
            "payroll_salary_days",
            "days_difference",
            "days_severity",
        ),
    }
    rows: list[dict[str, object]] = []
    for record in social.to_dict(orient="records"):
        for control, (expected, actual, difference, severity) in controls.items():
            if record.get(severity) == "OK":
                continue
            rows.append(
                {
                    "module": "SOCIAL_SECURITY",
                    "period_label": "MONTH",
                    "employee_id": record.get("employee_id"),
                    "employee_name": record.get("employee_name_payroll")
                    or record.get("employee_name"),
                    "control": control,
                    "expected_value": record.get(expected),
                    "actual_value": record.get(actual),
                    "difference": record.get(difference),
                    "severity": record.get(severity),
                    "rule_id": "social_security_baseline",
                    "rule_version": "1.0",
                    "rule_status": "PROVISIONAL",
                    "source_file": None,
                    "source_sheet": None,
                    "source_row": None,
                    "notes": (
                        f"source_match={record.get('source_match')}; "
                        f"control_id={record.get('contributed_days_control_id', '')}; "
                        f"explanation={record.get('days_explanation_status', '')}; "
                        f"reason={record.get('days_explanation_reason', '')}; "
                        f"financial_effect={record.get('absence_financial_effect', False)}"
                    ),
                }
            )
    return rows


def _employee_exceptions(
    employee_results: dict[str, pd.DataFrame],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for period, frame in employee_results.items():
        for record in frame.to_dict(orient="records"):
            if record.get("severity") == "OK":
                continue
            rows.append(
                {
                    "module": "EMPLOYEES",
                    "period_label": period,
                    "employee_id": record.get("employee_id"),
                    "employee_name": record.get("employee_name_payroll")
                    or record.get("employee_name_list"),
                    "control": record.get("outcome"),
                    "expected_value": record.get("in_employee_list"),
                    "actual_value": record.get("in_payroll"),
                    "difference": None,
                    "severity": record.get("severity"),
                    "rule_id": "employee_master_membership",
                    "rule_version": "1.0",
                    "rule_status": "PROVISIONAL",
                    "source_file": None,
                    "source_sheet": None,
                    "source_row": None,
                    "notes": f"employee_status={record.get('employee_status')}",
                }
            )
    return rows


def _overtime_exceptions(overtime: pd.DataFrame) -> list[dict[str, object]]:
    controls = {
        "day": ("expected_day_hours", "overtime_day_hours", "day_hours_difference"),
        "night": (
            "expected_night_hours",
            "overtime_night_hours",
            "night_hours_difference",
        ),
        "surcharge": (
            "expected_surcharge_hours",
            "night_surcharge_hours",
            "surcharge_hours_difference",
        ),
    }
    rows: list[dict[str, object]] = []
    for record in overtime.to_dict(orient="records"):
        for control, (expected, actual, difference) in controls.items():
            severity = record.get(f"{control}_severity")
            if severity == "OK":
                continue
            rows.append(
                {
                    "module": "OVERTIME",
                    "period_label": record.get("period_label"),
                    "employee_id": record.get("employee_id"),
                    "employee_name": record.get("employee_name_source")
                    or record.get("employee_name_payroll"),
                    "control": f"{control}_hours",
                    "expected_value": record.get(expected),
                    "actual_value": record.get(actual),
                    "difference": record.get(difference),
                    "severity": severity,
                    "rule_id": record.get("rule_id"),
                    "rule_version": record.get("rule_version"),
                    "rule_status": record.get("rule_status"),
                    "source_file": record.get("source_file"),
                    "source_sheet": record.get("source_sheet"),
                    "source_row": record.get("source_row"),
                    "notes": record.get("notes"),
                }
            )
    return rows


def _external_deduction_exceptions(
    external_deductions: dict[str, pd.DataFrame],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for frame in external_deductions.values():
        for record in frame.to_dict(orient="records"):
            if record.get("severity") == "OK":
                continue
            rows.append(
                {
                    "module": str(record.get("provider") or "EXTERNAL_DEDUCTION"),
                    "period_label": record.get("period_label"),
                    "employee_id": record.get("employee_id"),
                    "employee_name": record.get("employee_name_source")
                    or record.get("employee_name_payroll"),
                    "control": "monthly_deduction",
                    "expected_value": record.get("expected_value"),
                    "actual_value": record.get("actual_value"),
                    "difference": record.get("difference"),
                    "severity": record.get("severity"),
                    "rule_id": record.get("rule_id"),
                    "rule_version": record.get("rule_version"),
                    "rule_status": record.get("rule_status"),
                    "source_file": record.get("source_file"),
                    "source_sheet": None,
                    "source_row": record.get("source_row"),
                    "notes": record.get("notes"),
                }
            )
    return rows


def _loan_exceptions(loans: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in loans.to_dict(orient="records"):
        if record.get("severity") == "OK":
            continue
        rows.append(
            {
                "module": "EMPLOYEE_LOANS",
                "period_label": record.get("period_label"),
                "employee_id": record.get("employee_id"),
                "employee_name": record.get("employee_name_source")
                or record.get("employee_name_payroll"),
                "control": "balance_movement",
                "expected_value": record.get("expected_value"),
                "actual_value": record.get("actual_value"),
                "difference": record.get("difference"),
                "severity": record.get("severity"),
                "rule_id": record.get("rule_id"),
                "rule_version": record.get("rule_version"),
                "rule_status": record.get("rule_status"),
                "source_file": record.get("source_file"),
                "source_sheet": None,
                "source_row": record.get("source_row"),
                "notes": record.get("notes"),
            }
        )
    return rows


def _absence_exceptions(absences: pd.DataFrame) -> list[dict[str, object]]:
    return [{"module": "ABSENCES", "period_label": r.get("period_label"), "employee_id": r.get("employee_id"), "employee_name": r.get("employee_name_evidence") or r.get("employee_name_payroll"), "control": r.get("absence_type"), "expected_value": r.get("expected_units"), "actual_value": r.get("actual_units"), "difference": r.get("difference"), "severity": r.get("severity"), "rule_id": "absence_evidence_vs_payroll", "rule_version": "1.0", "rule_status": "PROVISIONAL", "source_file": None, "source_sheet": None, "source_row": None, "notes": r.get("evidence_status")} for r in absences.to_dict("records") if r.get("severity") != "OK"]


def _exception_frame(
    employee_results: dict[str, pd.DataFrame],
    social: pd.DataFrame,
    overtime: pd.DataFrame | None,
    external_deductions: dict[str, pd.DataFrame] | None,
    loans: pd.DataFrame | None,
    absences: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows = _employee_exceptions(employee_results)
    rows.extend(_social_exceptions(social))
    if overtime is not None:
        rows.extend(_overtime_exceptions(overtime))
    if external_deductions:
        rows.extend(_external_deduction_exceptions(external_deductions))
    if loans is not None:
        rows.extend(_loan_exceptions(loans))
    if absences is not None:
        rows.extend(_absence_exceptions(absences))
    columns = [
        "module",
        "period_label",
        "employee_id",
        "employee_name",
        "control",
        "expected_value",
        "actual_value",
        "difference",
        "severity",
        "rule_id",
        "rule_version",
        "rule_status",
        "source_file",
        "source_sheet",
        "source_row",
        "notes",
    ]
    return pd.DataFrame(rows, columns=columns)


def write_report(
    output: str | Path,
    employee_results: dict[str, pd.DataFrame],
    social: pd.DataFrame,
    overtime: pd.DataFrame | None = None,
    external_deductions: dict[str, pd.DataFrame] | None = None,
    loans: pd.DataFrame | None = None,
    reviews: pd.DataFrame | None = None,
    rules: pd.DataFrame | None = None,
    absences: pd.DataFrame | None = None,
    reusable_rule_ids: set[str] | None = None,
) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _summary_frame(employee_results, social, overtime, external_deductions, loans).to_excel(
            writer, sheet_name="Resumen", index=False
        )
        for label, frame in employee_results.items():
            safe_label = label.replace(" ", "_")[:20]
            frame.to_excel(writer, sheet_name=f"Empleados_{safe_label}", index=False)
        social.to_excel(writer, sheet_name="Seguridad_Social", index=False)
        if overtime is not None:
            overtime.to_excel(writer, sheet_name="Horas_Extras", index=False)
        for label, frame in (external_deductions or {}).items():
            sheet_name = "Los_Olivos" if label == "los_olivos" else "Comfatolima"
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
        if loans is not None:
            loans.to_excel(writer, sheet_name="Prestamos", index=False)
        build_employee_case_file(
            employee_results, social, overtime, external_deductions, loans, absences
        ).to_excel(writer, sheet_name="Casos_Empleado", index=False)
        exceptions = apply_review_ledger(
            _exception_frame(employee_results, social, overtime, external_deductions, loans, absences),
            reviews, reusable_rule_ids=reusable_rule_ids,
        )
        exceptions.to_excel(writer, sheet_name="Excepciones", index=False)
        review_sheet(exceptions).to_excel(writer, sheet_name="Revisiones", index=False)
        (rules if rules is not None else pd.DataFrame()).to_excel(
            writer, sheet_name="Reglas", index=False
        )
        (rules if rules is not None else pd.DataFrame()).to_excel(
            writer, sheet_name="Reglas_Validaciones", index=False
        )
        if absences is not None:
            absences.to_excel(writer, sheet_name="Ausencias", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for column_cells in worksheet.columns:
                width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 38)
                worksheet.column_dimensions[column_cells[0].column_letter].width = width
