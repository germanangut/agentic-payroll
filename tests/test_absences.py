import pandas as pd

from agentic_nomina.reconciliation.absences import reconcile_absences


def test_absence_reconciliation_keeps_mismatches_for_review() -> None:
    evidence = pd.DataFrame([{"employee_id": "100", "employee_name": "Persona Sintética", "absence_type": "PERMISO", "period_label": "Q1", "units": 4.0, "support_reference": "PER-1", "evidence_status": "VALID"}])
    payroll = pd.DataFrame([{"employee_id": "100", "employee_name": "Persona Sintética", "absence_type": "PERMISO", "period_label": "Q1", "units": 2.0}])
    result = reconcile_absences(evidence, payroll).iloc[0]
    assert result["severity"] == "REVIEW"
    assert result["difference"] == -2.0
