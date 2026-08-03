from __future__ import annotations

import pandas as pd


def reconcile_absences(evidence: pd.DataFrame, payroll: pd.DataFrame) -> pd.DataFrame:
    """Compare reported absence units with configured payroll novelty units.

    This deliberately compares reported units only; it does not calculate legal pay.
    """
    keys = ["employee_id", "absence_type", "period_label"]
    expected = evidence.groupby(keys, as_index=False).agg(
        employee_name_evidence=("employee_name", "first"),
        expected_units=("units", "sum"),
        evidence_references=("support_reference", lambda values: ", ".join(sorted(set(values)))),
        evidence_status=("evidence_status", "first"),
    )
    actual = payroll.groupby(keys, as_index=False).agg(
        employee_name_payroll=("employee_name", "first"), actual_units=("units", "sum")
    )
    result = expected.merge(actual, on=keys, how="outer", indicator=True)
    result["expected_units"] = result["expected_units"].fillna(0.0)
    result["actual_units"] = result["actual_units"].fillna(0.0)
    result["difference"] = result["actual_units"] - result["expected_units"]
    result["severity"] = "OK"
    result.loc[result["evidence_status"].fillna("").ne("VALID"), "severity"] = "REVIEW"
    result.loc[(result["_merge"] != "both") & result["evidence_status"].fillna("").eq("VALID"), "severity"] = "EXCEPTION"
    result.loc[(result["_merge"] == "both") & result["difference"].ne(0), "severity"] = "REVIEW"
    result["review_required"] = result["severity"].ne("OK")
    return result.drop(columns="_merge").sort_values(keys).reset_index(drop=True)
