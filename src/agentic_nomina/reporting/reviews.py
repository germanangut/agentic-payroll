from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

REVIEW_STATUSES = {"PENDIENTE", "EN_REVISION", "RESUELTO", "ESCALADO"}
REVIEW_DECISIONS = {"", "CONFIRMADO", "FALSO_POSITIVO", "CORRECCION_REQUERIDA"}
REVIEW_COLUMNS = [
    "exception_id",
    "revision_id",
    "material_fingerprint",
    "review_status",
    "review_decision",
    "reviewer",
    "reviewed_at",
    "review_notes",
    "previous_revision_id",
    "precedent_period",
    "precedent_decision",
    "continuity_status",
    "continuity_reason",
    "decision_origin",
]


def _canonical(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value).strip()


def exception_id(record: dict[str, object]) -> str:
    """Return an identifier that changes when the finding's material facts change."""
    identity_columns = (
        "module",
        "period_label",
        "employee_id",
        "control",
        "expected_value",
        "actual_value",
        "difference",
        "severity",
        "rule_id",
        "rule_version",
    )
    payload = "|".join(_canonical(record.get(column)) for column in identity_columns)
    return f"EXC-{hashlib.sha256(payload.encode()).hexdigest()[:16].upper()}"


def material_fingerprint(record: dict[str, object]) -> str:
    """Stable cross-period comparison key; deliberately excludes period and source location."""
    columns = (
        "module", "employee_id", "control", "expected_value", "actual_value", "difference",
        "severity", "rule_id", "rule_version", "source_file",
    )
    payload = "|".join(_canonical(record.get(column)) for column in columns)
    return f"MAT-{hashlib.sha256(payload.encode()).hexdigest()[:16].upper()}"


def load_review_ledger(path: str | Path) -> pd.DataFrame:
    """Load human decisions from a previous workbook or a CSV review ledger."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=str).fillna("")
    else:
        frame = pd.read_excel(path, sheet_name="Revisiones", dtype=str).fillna("")
    required = {"exception_id", "review_status", "review_decision", "reviewer", "reviewed_at", "review_notes"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Review ledger is missing columns: {', '.join(sorted(missing))}")
    for column in REVIEW_COLUMNS:
        if column not in frame:
            frame[column] = ""
    frame["revision_id"] = frame["revision_id"].where(frame["revision_id"].ne(""), frame["exception_id"])
    validate_review_ledger(frame[REVIEW_COLUMNS].copy())
    return frame


def validate_review_ledger(frame: pd.DataFrame) -> pd.DataFrame:
    if frame["exception_id"].duplicated().any():
        duplicates = sorted(frame.loc[frame["exception_id"].duplicated(), "exception_id"].unique())
        raise ValueError(f"Duplicate exception IDs in review ledger: {', '.join(duplicates)}")

    invalid_statuses = sorted(set(frame["review_status"]) - REVIEW_STATUSES)
    if invalid_statuses:
        raise ValueError(f"Invalid review statuses: {', '.join(invalid_statuses)}")
    invalid_decisions = sorted(set(frame["review_decision"]) - REVIEW_DECISIONS)
    if invalid_decisions:
        raise ValueError(f"Invalid review decisions: {', '.join(invalid_decisions)}")

    resolved = frame["review_status"].eq("RESUELTO")
    incomplete = resolved & (
        frame["review_decision"].eq("")
        | frame["reviewer"].eq("")
        | frame["reviewed_at"].eq("")
    )
    if incomplete.any():
        ids = ", ".join(frame.loc[incomplete, "exception_id"])
        raise ValueError(
            "Resolved reviews require decision, reviewer and reviewed_at. " f"Invalid IDs: {ids}"
        )
    return frame


def apply_review_ledger(
    exceptions: pd.DataFrame, reviews: pd.DataFrame | None = None, *, reusable_rule_ids: set[str] | None = None
) -> pd.DataFrame:
    """Attach current human-review state to the deterministic exception registry."""
    result = exceptions.copy()
    result.insert(0, "exception_id", [exception_id(row) for row in result.to_dict("records")])
    result.insert(1, "revision_id", result["exception_id"])
    result.insert(2, "material_fingerprint", [material_fingerprint(row) for row in result.to_dict("records")])
    defaults = {
        "review_status": "PENDIENTE",
        "review_decision": "",
        "reviewer": "",
        "reviewed_at": "",
        "review_notes": "",
        "previous_revision_id": "",
        "precedent_period": "",
        "precedent_decision": "",
        "continuity_status": "SIN_PRECEDENTE",
        "continuity_reason": "No prior report supplied",
        "decision_origin": "NUEVA",
    }
    if reviews is None:
        for column, value in defaults.items():
            result[column] = value
        return result

    reviews = reviews.copy()
    legacy_ledger = "material_fingerprint" not in reviews
    for column in REVIEW_COLUMNS:
        if column not in reviews:
            reviews[column] = ""
    reviews["revision_id"] = reviews["revision_id"].where(
        reviews["revision_id"].ne(""), reviews["exception_id"]
    )
    reviews = validate_review_ledger(reviews.copy())
    if legacy_ledger:
        unknown = sorted(set(reviews["revision_id"]) - set(result["revision_id"]))
        if unknown:
            raise ValueError("Review ledger contains findings that are no longer current: " + ", ".join(unknown))
    current = reviews.loc[reviews["revision_id"].isin(result["revision_id"])]
    current = current.drop(columns=["exception_id", "material_fingerprint", "period_label", "rule_id", "rule_version"], errors="ignore")
    result = result.merge(current, on="revision_id", how="left", validate="one_to_one")
    for column, value in defaults.items():
        result[column] = result[column].fillna(value)
    unmatched = result["decision_origin"].eq("NUEVA")
    candidates = reviews.loc[
        reviews["review_status"].eq("RESUELTO")
        & reviews["review_decision"].ne("")
        & reviews["reviewer"].ne("")
        & reviews["reviewed_at"].ne("")
    ]
    for index, row in result.loc[unmatched].iterrows():
        matches = candidates.loc[candidates["material_fingerprint"].eq(row["material_fingerprint"])]
        if len(matches) != 1:
            result.at[index, "continuity_status"] = "AMBIGUO" if len(matches) > 1 else "SIN_PRECEDENTE"
            result.at[index, "continuity_reason"] = "Multiple matching precedents" if len(matches) > 1 else "No exact material precedent"
            continue
        prior = matches.iloc[0]
        result.at[index, "previous_revision_id"] = prior["revision_id"]
        result.at[index, "precedent_period"] = prior.get("period_label", "")
        result.at[index, "precedent_decision"] = prior["review_decision"]
        result.at[index, "continuity_status"] = "PRECEDENTE"
        result.at[index, "continuity_reason"] = "Exact material fingerprint; decision requires current-period confirmation"
        if row.get("rule_id") in (reusable_rule_ids or set()) and prior["review_decision"] == "FALSO_POSITIVO":
            result.loc[index, ["review_status", "review_decision", "reviewer", "reviewed_at"]] = prior[["review_status", "review_decision", "reviewer", "reviewed_at"]].to_list()
            result.at[index, "decision_origin"] = "PRECEDENTE_REUTILIZADO"
            result.at[index, "continuity_status"] = "REUTILIZADO"
        else:
            result.at[index, "decision_origin"] = "PRECEDENTE_CONTEXTO"
    return result


def review_sheet(exceptions: pd.DataFrame) -> pd.DataFrame:
    """Return the editable review ledger exported with every report."""
    context = ["employee_id", "employee_name", "module", "period_label", "control", "severity", "rule_id", "rule_version"]
    return exceptions[[*REVIEW_COLUMNS, *context]].copy()
