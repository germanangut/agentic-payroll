import pandas as pd

from agentic_nomina.reconciliation.social_security import reconcile_social_security


def test_social_security_aggregates_payroll_periods_and_compares_ibc() -> None:
    q1 = pd.DataFrame(
        [
            {
                "employee_id": "1",
                "employee_name": "Ana",
                "salary_days": 15,
                "health_employee": 0,
                "pension_employee": 0,
            }
        ]
    )
    q2 = pd.DataFrame(
        [
            {
                "employee_id": "1",
                "employee_name": "Ana",
                "salary_days": 15,
                "health_employee": 70_000,
                "pension_employee": 70_000,
            }
        ]
    )
    pila = pd.DataFrame(
        [
            {
                "employee_id": "1",
                "employee_name": "Ana",
                "health_days": 30,
                "health_ibc": 1_750_000,
                "pension_days": 30,
                "pension_ibc": 1_750_000,
            }
        ]
    )
    config = {
        "health_employee_rate": 0.04,
        "pension_employee_rate": 0.04,
        "monetary_rounding": 100,
        "monetary_tolerance": 200,
        "days_tolerance": 0,
    }

    result = reconcile_social_security([q1, q2], pila, config).iloc[0]
    assert result["health_severity"] == "OK"
    assert result["pension_severity"] == "OK"
    assert result["days_severity"] == "OK"
