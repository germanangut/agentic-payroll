from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

REVIEW_STATUSES = {"PENDIENTE", "EN_REVISION", "RESUELTO", "ESCALADO"}
REVIEW_DECISIONS = {"", "CONFIRMADO", "FALSO_POSITIVO", "CORRECCION_REQUERIDA"}
REVIEW_COLUMNS = [
    "exception_id",
    "review_status",
    "review_decision",
    "reviewer",
    "reviewed_at",
    "review_notes",
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


def load_review_ledger(path: str | Path) -> pd.DataFrame:
    """Load human decisions from a previous workbook or a CSV review ledger."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=str).fillna("")
    else:
        frame = pd.read_excel(path, sheet_name="Revisiones", dtype=str).fillna("")
    missing = set(REVIEW_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Review ledger is missing columns: {', '.join(sorted(missing))}")
    return validate_review_ledger(frame[REVIEW_COLUMNS].copy())


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
    exceptions: pd.DataFrame, reviews: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Attach current human-review state to the deterministic exception registry."""
    result = exceptions.copy()
    result.insert(0, "exception_id", [exception_id(row) for row in result.to_dict("records")])
    defaults = {
        "review_status": "PENDIENTE",
        "review_decision": "",
        "reviewer": "",
        "reviewed_at": "",
        "review_notes": "",
    }
    if reviews is None:
        for column, value in defaults.items():
            result[column] = value
        return result

    reviews = validate_review_ledger(reviews.copy())
    unknown = sorted(set(reviews["exception_id"]) - set(result["exception_id"]))
    if unknown:
        raise ValueError(
            "Review ledger contains findings that are no longer current: " + ", ".join(unknown)
        )
    result = result.merge(reviews, on="exception_id", how="left", validate="one_to_one")
    for column, value in defaults.items():
        result[column] = result[column].fillna(value)
    return result


def review_sheet(exceptions: pd.DataFrame) -> pd.DataFrame:
    """Return the editable review ledger exported with every report."""
    context = ["employee_id", "employee_name", "module", "period_label", "control", "severity"]
    return exceptions[[*REVIEW_COLUMNS, *context]].copy()
