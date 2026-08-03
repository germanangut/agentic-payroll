from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

RULE_STATUSES = {"PENDIENTE", "EN_VALIDACION", "APROBADA", "RECHAZADA"}
RULE_KEY_COLUMNS = ["rule_id", "rule_version"]
RULE_APPROVAL_COLUMNS = [
    "rule_id",
    "rule_version",
    "estado_aprobacion",
    "responsable_aprobacion",
    "fecha_aprobacion",
    "evidencia_aprobacion",
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
    missing = set(RULE_APPROVAL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Rule ledger is missing columns: {', '.join(sorted(missing))}")
    return validate_rule_ledger(frame[RULE_APPROVAL_COLUMNS].copy())


def validate_rule_ledger(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.duplicated(RULE_KEY_COLUMNS).any():
        raise ValueError("Rule ledger contains duplicate approvals for the same rule version.")
    statuses = set(frame["estado_aprobacion"]) - RULE_STATUSES
    if statuses:
        raise ValueError(f"Invalid rule approval statuses: {', '.join(sorted(statuses))}")
    approved = frame["estado_aprobacion"].eq("APROBADA")
    incomplete = approved & (
        frame["responsable_aprobacion"].eq("")
        | frame["fecha_aprobacion"].eq("")
        | frame["evidencia_aprobacion"].eq("")
    )
    if incomplete.any():
        raise ValueError(
            "Approved rules require responsible person, approval date and approval evidence."
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
        result[column] = result[column].fillna("PENDIENTE" if column == "estado_aprobacion" else "")
    return result


def require_approved_financial_rules(rules: pd.DataFrame) -> None:
    """Raise when an active financial rule lacks a complete approval for its own version."""
    active_financial = rules["active"].astype(bool) & rules["financial"].astype(bool)
    valid = (
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
