from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from agentic_nomina.adapters.absences import absence_payroll_units, load_absence_evidence
from agentic_nomina.adapters.employees import load_employee_list
from agentic_nomina.adapters.external_deductions import load_comfatolima, load_los_olivos
from agentic_nomina.adapters.loans import load_loan_balance_report
from agentic_nomina.adapters.overtime import load_overtime_summary
from agentic_nomina.adapters.payroll import load_payroll
from agentic_nomina.adapters.pila import load_pila
from agentic_nomina.reconciliation.absence_aware_days import explain_contributed_day_differences
from agentic_nomina.reconciliation.absences import reconcile_absences
from agentic_nomina.reconciliation.employees import reconcile_employees
from agentic_nomina.reconciliation.external_deductions import reconcile_external_deduction
from agentic_nomina.reconciliation.loans import reconcile_loan_balances
from agentic_nomina.reconciliation.overtime import reconcile_overtime
from agentic_nomina.reconciliation.social_security import reconcile_social_security
from agentic_nomina.reporting.excel import write_report
from agentic_nomina.reporting.reviews import load_review_ledger
from agentic_nomina.reporting.rules import (
    apply_rule_ledger,
    load_rule_ledger,
    require_approved_financial_rules,
    rule_registry_frame,
)
from agentic_nomina.run_manifest import build_run_metadata, execution_frame, resolve_run_contract


def run_baseline(
    *,
    payroll_q1_path: str | Path,
    payroll_q2_path: str | Path,
    employees_q1_path: str | Path,
    employees_q2_path: str | Path,
    pila_path: str | Path,
    output_path: str | Path,
    config: dict[str, Any],
    overtime_q1_path: str | Path | None = None,
    overtime_q2_path: str | Path | None = None,
    los_olivos_path: str | Path | None = None,
    comfatolima_path: str | Path | None = None,
    loans_q1_path: str | Path | None = None,
    loans_q2_path: str | Path | None = None,
    reviews_path: str | Path | None = None,
    rules_path: str | Path | None = None,
    require_approved_rules: bool = False,
    absence_evidence_paths: list[str | Path] | None = None,
    business_period: str | None = None,
    run_id: str | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    sources, business_period, run_id, diagnostics = resolve_run_contract(
        {"payroll_q1": payroll_q1_path, "payroll_q2": payroll_q2_path,
         "employees_q1": employees_q1_path, "employees_q2": employees_q2_path,
         "pila": pila_path, "overtime_q1": overtime_q1_path, "overtime_q2": overtime_q2_path,
         "los_olivos": los_olivos_path, "comfatolima": comfatolima_path,
         "loans_q1": loans_q1_path, "loans_q2": loans_q2_path,
         "reviews": reviews_path, "rules": rules_path, "absence_evidence": None},
        period=business_period, run_id=run_id, manifest_path=manifest_path,
    )
    metadata, manifest, preflight = build_run_metadata(
        config["company"]["name"], business_period, run_id, sources,
        config=config, output_path=output_path, diagnostics=diagnostics,
    )
    payroll_q1_path, payroll_q2_path = sources["payroll_q1"], sources["payroll_q2"]
    employees_q1_path, employees_q2_path = sources["employees_q1"], sources["employees_q2"]
    pila_path = sources["pila"]
    overtime_q1_path, overtime_q2_path = sources["overtime_q1"], sources["overtime_q2"]
    los_olivos_path, comfatolima_path = sources["los_olivos"], sources["comfatolima"]
    loans_q1_path, loans_q2_path = sources["loans_q1"], sources["loans_q2"]
    reviews_path, rules_path = sources["reviews"], sources["rules"]
    payroll_q1 = load_payroll(payroll_q1_path, config["payroll"], "Q1")
    payroll_q2 = load_payroll(payroll_q2_path, config["payroll"], "Q2")
    employees_q1 = load_employee_list(employees_q1_path, config["employee_list"], "Q1")
    employees_q2 = load_employee_list(employees_q2_path, config["employee_list"], "Q2")
    pila = load_pila(pila_path, config["pila"])

    employee_results = {
        "Q1": reconcile_employees(employees_q1, payroll_q1),
        "Q2": reconcile_employees(employees_q2, payroll_q2),
    }
    social = reconcile_social_security(
        [payroll_q1, payroll_q2], pila, config["reconciliation"]
    )
    absences: pd.DataFrame | None = None
    if absence_evidence_paths:
        evidence = pd.concat(
            [load_absence_evidence(path, config["absences"], "MONTH") for path in absence_evidence_paths],
            ignore_index=True,
        )
        social = explain_contributed_day_differences(
            social, evidence, config["contributed_days_explanation"]
        )
        payroll_units = absence_payroll_units(pd.concat([payroll_q1, payroll_q2]), config["absences"])
        absences = reconcile_absences(evidence, payroll_units)

    overtime: pd.DataFrame | None = None
    if (overtime_q1_path is None) != (overtime_q2_path is None):
        raise ValueError("Both overtime source files must be provided together.")
    if overtime_q1_path is not None and overtime_q2_path is not None:
        overtime_q1 = load_overtime_summary(
            overtime_q1_path, config["overtime"], "Q1"
        )
        overtime_q2 = load_overtime_summary(
            overtime_q2_path, config["overtime"], "Q2"
        )
        overtime = reconcile_overtime(
            [overtime_q1, overtime_q2],
            [payroll_q1, payroll_q2],
            config["overtime"],
        )

    external_deductions: dict[str, pd.DataFrame] = {}
    deductions_config = config.get("external_deductions", {})
    deduction_rules = deductions_config.get("rules", {})
    if los_olivos_path is not None:
        provider_config = {
            **deductions_config["los_olivos"],
            "provider": "LOS_OLIVOS",
        }
        los_olivos = load_los_olivos(los_olivos_path, provider_config)
        external_deductions["los_olivos"] = reconcile_external_deduction(
            los_olivos, payroll_q2, provider_config, deduction_rules
        )
    if comfatolima_path is not None:
        provider_config = {
            **deductions_config["comfatolima"],
            "provider": "COMFATOLIMA",
        }
        comfatolima = load_comfatolima(comfatolima_path, provider_config)
        external_deductions["comfatolima"] = reconcile_external_deduction(
            comfatolima, payroll_q2, provider_config, deduction_rules
        )

    loans: pd.DataFrame | None = None
    if (loans_q1_path is None) != (loans_q2_path is None):
        raise ValueError("Both employee-loan balance reports must be provided together.")
    if loans_q1_path is not None and loans_q2_path is not None:
        loan_config = config["loans"]
        loan_q1 = load_loan_balance_report(loans_q1_path, loan_config, "Q1")
        loan_q2 = load_loan_balance_report(loans_q2_path, loan_config, "Q2")
        q1_loan_results = reconcile_loan_balances(
            loan_q1, payroll_q1, loan_config["rules"], next_report=loan_q2
        )
        q2_loan_results = reconcile_loan_balances(
            loan_q2, payroll_q2, loan_config["rules"]
        )
        loans = pd.DataFrame.from_records(
            [
                *q1_loan_results.to_dict(orient="records"),
                *q2_loan_results.to_dict(orient="records"),
            ]
        )

    reviews = load_review_ledger(reviews_path) if reviews_path is not None else None
    rule_approvals = load_rule_ledger(rules_path) if rules_path is not None else None
    rules = apply_rule_ledger(rule_registry_frame(config), rule_approvals)
    if require_approved_rules:
        require_approved_financial_rules(rules)
    write_report(
        output_path,
        employee_results,
        social,
        overtime,
        external_deductions,
        loans,
        reviews,
        rules,
        absences,
        set(config.get("review_continuity", {}).get("reusable_non_financial_rule_ids", [])),
        execution_frame(metadata, manifest, preflight, rules),
    )
    results = {**employee_results, "social_security": social, **external_deductions}
    if overtime is not None:
        results["overtime"] = overtime
    if loans is not None:
        results["loans"] = loans
    if absences is not None:
        results["absences"] = absences
    results["run_metadata"] = pd.DataFrame([metadata.model_dump()])
    return results
