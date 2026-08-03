from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd


def explain_contributed_day_differences(
    social: pd.DataFrame, evidence: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    """Attach non-financial, exact-match absence context to observed PILA day differences."""
    result = social.copy()
    rule_id = config["rule_id"]
    version = config["rule_version"]
    allowed_types = set(config.get("absence_types", []))
    comparable = set(config.get("comparable_units", ["DAYS"]))
    for column, value in {
        "absence_candidate_days": 0.0,
        "absence_explained_days": 0.0,
        "unexplained_days_difference": result["days_difference"],
        "days_explanation_status": "SIN_DIFERENCIA",
        "days_explanation_reason": "Observed source values are equal",
        "days_explanation_rule_id": rule_id,
        "days_explanation_rule_version": version,
        "absence_evidence_references": "",
        "absence_financial_effect": False,
    }.items():
        result[column] = value
    for index, row in result.iterrows():
        result.at[index, "contributed_days_control_id"] = "CDD-" + hashlib.sha256(
            f"{row.get('employee_id')}|{rule_id}|{version}".encode()
        ).hexdigest()[:16].upper()
        difference = float(row["days_difference"] or 0)
        if difference == 0:
            continue
        matches = evidence.loc[evidence["employee_id"].eq(row["employee_id"])]
        if matches.empty:
            result.at[index, "days_explanation_status"] = "DIFERENCIA_SIN_EXPLICACION"
            result.at[index, "days_explanation_reason"] = "No absence evidence for employee"
            continue
        same_period = matches.loc[matches["period_label"].eq("MONTH")]
        if same_period.empty:
            result.at[index, "days_explanation_status"] = "REVIEW"
            result.at[index, "days_explanation_reason"] = "Absence evidence period is incompatible"
            continue
        units = same_period.get("unit", pd.Series("DAYS", index=same_period.index)).fillna("")
        eligible = same_period.loc[
            same_period["absence_type"].isin(allowed_types)
            & units.isin(comparable)
            & same_period["evidence_status"].eq("VALID")
        ]
        result.at[index, "absence_evidence_references"] = ", ".join(eligible["support_reference"].astype(str))
        candidate = float(eligible["units"].sum())
        result.at[index, "absence_candidate_days"] = candidate
        # Only a negative payroll-minus-PILA difference may be explained by configured absence days.
        if difference >= 0 or len(eligible) != len(same_period) or candidate != abs(difference):
            result.at[index, "days_explanation_status"] = "REVIEW"
            result.at[index, "days_explanation_reason"] = "Evidence is incomplete, incompatible, partial or directionally invalid"
            continue
        result.at[index, "absence_explained_days"] = candidate
        result.at[index, "unexplained_days_difference"] = 0.0
        result.at[index, "days_explanation_status"] = "EXPLICACION_PROVISIONAL"
        result.at[index, "days_explanation_reason"] = "Exact configurable non-financial absence match"
    return result
