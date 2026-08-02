from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from agentic_nomina.adapters.employees import load_employee_list
from agentic_nomina.adapters.payroll import load_payroll
from agentic_nomina.adapters.pila import load_pila
from agentic_nomina.reconciliation.employees import reconcile_employees
from agentic_nomina.reconciliation.social_security import reconcile_social_security
from agentic_nomina.reporting.excel import write_report


def run_baseline(
    *,
    payroll_q1_path: str | Path,
    payroll_q2_path: str | Path,
    employees_q1_path: str | Path,
    employees_q2_path: str | Path,
    pila_path: str | Path,
    output_path: str | Path,
    config: dict[str, Any],
) -> dict[str, pd.DataFrame]:
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
    write_report(output_path, employee_results, social)
    return {**employee_results, "social_security": social}
