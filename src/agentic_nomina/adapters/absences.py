from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader

from agentic_nomina.utils import clean_text, normalize_document, numeric

ABSENCE_COLUMNS = ["period_label", "employee_id", "employee_name", "absence_type", "units", "support_reference", "evidence_status", "source_file", "source_page"]


def load_absence_evidence(path: str | Path, config: dict[str, Any], period_label: str) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=object)
        required = {"employee_id", "absence_type", "units", "support_reference"}
        if missing := required - set(frame.columns):
            raise ValueError(f"Absence evidence is missing columns: {', '.join(sorted(missing))}")
        result = pd.DataFrame({column: "" for column in ABSENCE_COLUMNS}, index=frame.index)
        result["period_label"] = period_label
        result["employee_id"] = frame["employee_id"].map(normalize_document)
        result["employee_name"] = frame.get("employee_name", "").map(clean_text)
        result["absence_type"] = frame["absence_type"].map(lambda value: clean_text(value).upper())
        result["units"] = frame["units"].map(numeric)
        result["support_reference"] = frame["support_reference"].map(clean_text)
        result["evidence_status"] = "VALID"
        result["source_file"] = path.name
        invalid = result["employee_id"].isna() | result["absence_type"].eq("") | result["units"].le(0) | result["support_reference"].eq("")
        result.loc[invalid, "evidence_status"] = "REVIEW_MISSING_REFERENCE"
        return result
    reader = PdfReader(path)
    rows = []
    for page, item in enumerate(reader.pages, start=1):
        if not (item.extract_text() or "").strip():
            rows.append({"period_label": period_label, "employee_id": None, "employee_name": "", "absence_type": "UNKNOWN", "units": 0.0, "support_reference": f"{path.stem}:p{page}", "evidence_status": "REVIEW_SCANNED_PDF", "source_file": path.name, "source_page": page})
    return pd.DataFrame(rows, columns=ABSENCE_COLUMNS)


def absence_payroll_units(payroll: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for absence_type, column in config["payroll_units"].items():
        for record in payroll[["period_label", "employee_id", "employee_name", column]].to_dict("records"):
            if record[column]:
                rows.append({"period_label": record["period_label"], "employee_id": record["employee_id"], "employee_name": record["employee_name"], "absence_type": absence_type, "units": record[column]})
    return pd.DataFrame(rows, columns=["period_label", "employee_id", "employee_name", "absence_type", "units"])
