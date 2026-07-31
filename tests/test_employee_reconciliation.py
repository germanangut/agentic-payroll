import pandas as pd

from agentic_nomina.reconciliation.employees import reconcile_employees


def test_employee_reconciliation_classifies_missing_and_extra() -> None:
    employee_list = pd.DataFrame(
        [
            {"employee_id": "1", "employee_name": "Ana", "employee_status": "E"},
            {"employee_id": "2", "employee_name": "Luis", "employee_status": "V"},
        ]
    )
    payroll = pd.DataFrame(
        [
            {"employee_id": "1", "employee_name": "Ana"},
            {"employee_id": "3", "employee_name": "Marta"},
        ]
    )

    result = reconcile_employees(employee_list, payroll).set_index("employee_id")
    assert result.at["1", "severity"] == "OK"
    assert result.at["2", "severity"] == "WARNING"
    assert result.at["3", "severity"] == "BLOCKING"
