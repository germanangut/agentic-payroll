from __future__ import annotations

import pandas as pd

from agentic_nomina.models import Severity
from agentic_nomina.utils import canonical_text


def reconcile_employees(employee_list: pd.DataFrame, payroll: pd.DataFrame) -> pd.DataFrame:
    listed = employee_list.drop_duplicates("employee_id").set_index("employee_id")
    paid = payroll.drop_duplicates("employee_id").set_index("employee_id")
    ids = sorted(set(listed.index) | set(paid.index))
    rows: list[dict[str, object]] = []

    for employee_id in ids:
        in_list = employee_id in listed.index
        in_payroll = employee_id in paid.index
        list_name = str(listed.at[employee_id, "employee_name"]) if in_list else ""
        payroll_name = str(paid.at[employee_id, "employee_name"]) if in_payroll else ""
        status = str(listed.at[employee_id, "employee_status"]) if in_list else ""

        if in_list and in_payroll:
            names_match = canonical_text(list_name) == canonical_text(payroll_name)
            severity = Severity.OK if names_match else Severity.WARNING
            outcome = "MATCHED" if names_match else "NAME_MISMATCH"
        elif in_list:
            severity = Severity.WARNING if canonical_text(status) not in {"", "E"} else Severity.REVIEW
            outcome = "MISSING_IN_PAYROLL"
        else:
            severity = Severity.BLOCKING
            outcome = "EXTRA_IN_PAYROLL"

        rows.append(
            {
                "employee_id": employee_id,
                "employee_name_list": list_name,
                "employee_name_payroll": payroll_name,
                "employee_status": status,
                "in_employee_list": in_list,
                "in_payroll": in_payroll,
                "outcome": outcome,
                "severity": severity.value,
            }
        )
    return pd.DataFrame(rows)
