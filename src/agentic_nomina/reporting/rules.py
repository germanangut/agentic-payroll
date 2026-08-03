from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

RULE_STATUSES = {"PENDIENTE", "EN_VALIDACION", "VALIDADA", "APROBADA", "RECHAZADA"}
RULE_KEY_COLUMNS = ["rule_id", "rule_version"]
RULE_APPROVAL_COLUMNS = [
    "rule_id",
    "rule_version",
    "estado_aprobacion",
    "responsable_aprobacion",
    "fecha_aprobacion",
    "evidencia_aprobacion",
    "validation_status",
    "approver_role",
    "approver_id",
    "approver_name",
    "evidence_type",
    "evidence_reference",
    "evidence_date",
    "decision_date",
    "decision",
    "decision_comment",
    "validation_record_id",
    "previous_validation_record_id",
    "created_at",
    "decision_origin",
]


def rule_registry_frame(config: dict[str, Any]) -> pd.DataFrame:
    """Return the versioned, configuration-owned payroll rule registry."""
    registry = config.get("rule_governance", {}).get("registry", [])
    frame = pd.DataFrame(registry)
    required = {"rule_id", "rule_version", "rule_name", "active", "financial"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Rule registry is missing columns: {', '.join(sorted(missing))}")
    if frame.duplicated(RULE_KEY_COLUMNS).any():
        raise ValueError("Rule registry contains duplicate rule_id and rule_version entries.")
    return frame.sort_values(RULE_KEY_COLUMNS, kind="stable").reset_index(drop=True)


def load_rule_ledger(path: str | Path) -> pd.DataFrame:
    """Load version-specific approvals from a report workbook or CSV ledger."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=str).fillna("")
    else:
        frame = pd.read_excel(path, sheet_name="Reglas", dtype=str).fillna("")
    required = {"rule_id", "rule_version", "estado_aprobacion", "responsable_aprobacion", "fecha_aprobacion", "evidencia_aprobacion"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Rule ledger is missing columns: {', '.join(sorted(missing))}")
    for column in RULE_APPROVAL_COLUMNS:
        if column not in frame:
            frame[column] = ""
    return validate_rule_ledger(frame[RULE_APPROVAL_COLUMNS].copy())


def validate_rule_ledger(frame: pd.DataFrame) -> pd.DataFrame:
    legacy = "validation_status" not in frame
    for column in RULE_APPROVAL_COLUMNS:
        if column not in frame:
            frame[column] = ""
    if frame.duplicated(RULE_KEY_COLUMNS).any():
        raise ValueError("Rule ledger contains duplicate approvals for the same rule version.")
    statuses = set(frame["estado_aprobacion"]) - RULE_STATUSES
    if statuses:
        raise ValueError(f"Invalid rule approval statuses: {', '.join(sorted(statuses))}")
    frame["validation_status"] = frame["validation_status"].where(frame["validation_status"].ne(""), frame["estado_aprobacion"])
    approved = frame["validation_status"].isin({"VALIDADA", "APROBADA"})
    if legacy:
        approved = frame["estado_aprobacion"].eq("APROBADA")
    incomplete = approved & (
        frame["approver_role"].eq("") | frame["approver_id"].eq("")
        | frame["evidence_type"].eq("") | frame["evidence_reference"].eq("")
        | frame["decision_date"].eq("") | frame["decision"].eq("")
        | frame["validation_record_id"].eq("")
    )
    if legacy:
        incomplete = approved & (frame["responsable_aprobacion"].eq("") | frame["fecha_aprobacion"].eq("") | frame["evidencia_aprobacion"].eq(""))
    if incomplete.any():
        raise ValueError(
                "Validated rules require responsible person, role, evidence, decision and record traceability."
        )
    return frame


def apply_rule_ledger(
    registry: pd.DataFrame, approvals: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Attach a human approval to each configured version without carrying it forward."""
    registry = registry.copy()
    if approvals is None:
        approvals = pd.DataFrame(columns=RULE_APPROVAL_COLUMNS)
    approvals = validate_rule_ledger(approvals.copy())

    known_ids = set(registry["rule_id"])
    incoming_ids = set(approvals["rule_id"])
    unknown = sorted(incoming_ids - known_ids)
    if unknown:
        raise ValueError("Rule ledger contains unknown rules: " + ", ".join(unknown))
    known_keys = set(map(tuple, registry[RULE_KEY_COLUMNS].to_numpy()))
    obsolete = sorted(
        f"{rule_id}@{version}"
        for rule_id, version in approvals[RULE_KEY_COLUMNS].itertuples(index=False, name=None)
        if (rule_id, version) not in known_keys
    )
    if obsolete:
        raise ValueError(
            "Rule ledger contains obsolete approvals for rule versions: " + ", ".join(obsolete)
        )

    result = registry.merge(approvals, on=RULE_KEY_COLUMNS, how="left", validate="one_to_one")
    for column in RULE_APPROVAL_COLUMNS[2:]:
        result[column] = result[column].fillna("PENDIENTE" if column in {"estado_aprobacion", "validation_status"} else "")
    return result


def require_approved_financial_rules(rules: pd.DataFrame) -> None:
    """Raise when an active financial rule lacks a complete approval for its own version."""
    active_financial = rules["active"].astype(bool) & rules["financial"].astype(bool)
    valid = (
        rules["validation_status"].eq("APROBADA")
        & rules["approver_role"].ne("") & rules["approver_id"].ne("")
        & rules["evidence_type"].ne("") & rules["evidence_reference"].ne("")
        & rules["decision_date"].ne("") & rules["decision"].ne("")
        & rules["validation_record_id"].ne("")
    )
    valid |= (
        rules["estado_aprobacion"].eq("APROBADA")
        & rules["responsable_aprobacion"].ne("")
        & rules["fecha_aprobacion"].ne("")
        & rules["evidencia_aprobacion"].ne("")
    )
    pending = rules.loc[active_financial & ~valid, RULE_KEY_COLUMNS]
    if not pending.empty:
        entries = ", ".join(
            f"{rule_id}@{version}"
            for rule_id, version in pending.itertuples(index=False, name=None)
        )
        raise ValueError(
            "Active financial rules require a valid approval for their version: " + entries
        )
