from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from agentic_nomina.adapters.common import find_header_row, unique_headers
from agentic_nomina.utils import canonical_text, clean_text, normalize_document


def _column(columns: list[str], configured: str) -> str | None:
    target = canonical_text(configured)
    return next((column for column in columns if column == target), None)


def load_employee_list(path: str | Path, config: dict[str, Any], period_label: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=config.get("sheet_name", "Hoja1"), header=None, dtype=object)
    header_index = find_header_row(raw, config["header_markers"])
    headers = unique_headers(raw.iloc[header_index].tolist())
    data = raw.iloc[header_index + 1 :].copy()
    data.columns = headers
    fields = config["fields"]

    id_col = _column(headers, fields["employee_id"])
    name_col = _column(headers, fields["employee_name"])
    status_col = _column(headers, fields["status"])
    retirement_col = _column(headers, fields["retirement_date"])
    if id_col is None or name_col is None:
        raise ValueError("Employee list identifier/name columns were not found.")

    result = pd.DataFrame(
        {
            "employee_id": data[id_col].map(normalize_document),
            "employee_name": data[name_col].map(clean_text),
            "employee_status": data[status_col].map(clean_text) if status_col else "",
            "retirement_date": data[retirement_col] if retirement_col else None,
            "period_label": period_label,
        }
    )
    return result[result["employee_id"].notna() & result["employee_name"].ne("")].reset_index(drop=True)
