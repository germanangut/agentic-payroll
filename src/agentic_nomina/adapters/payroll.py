from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from agentic_nomina.adapters.common import find_header_row, unique_headers
from agentic_nomina.utils import canonical_text, clean_text, normalize_document, numeric


def _column_by_prefix(columns: list[str], configured: str) -> str | None:
    target = canonical_text(configured)
    for column in columns:
        if column == target or column.startswith(target):
            return column
    return None


def load_payroll(path: str | Path, config: dict[str, Any], period_label: str) -> pd.DataFrame:
    sheet_name = config.get("sheet_name", "Hoja1")
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=object)
    header_index = find_header_row(raw, config["header_markers"])
    headers = unique_headers(raw.iloc[header_index].tolist())
    data = raw.iloc[header_index + 1 :].copy()
    data.columns = headers

    concepts = config["concepts"]
    id_col = _column_by_prefix(headers, concepts["employee_id"])
    name_col = _column_by_prefix(headers, concepts["employee_name"])
    if id_col is None or name_col is None:
        raise ValueError("Payroll employee identifier/name columns were not found.")

    result = pd.DataFrame()
    result["employee_id"] = data[id_col].map(normalize_document)
    result["employee_name"] = data[name_col].map(clean_text)
    result = result[result["employee_id"].notna() & result["employee_name"].ne("")].copy()
    result["period_label"] = period_label
    result["source_file"] = Path(path).name
    result["source_sheet"] = sheet_name
    result["source_row"] = result.index + 1

    for output, configured in {
        "salary_value": concepts.get("salary", ""),
        "health_employee": concepts.get("health_employee", ""),
        "pension_employee": concepts.get("pension_employee", ""),
        "overtime_day_value": concepts.get("overtime_day", ""),
        "overtime_night_value": concepts.get("overtime_night", ""),
        "night_surcharge_value": concepts.get("night_surcharge", ""),
    }.items():
        column = _column_by_prefix(headers, configured) if configured else None
        result[output] = data.loc[result.index, column].map(numeric).abs() if column else 0.0

    # In Siigo exports the quantity/days column is the VAR column immediately before the value.
    for output, configured in {
        "salary_days": concepts.get("salary", ""),
        "overtime_day_hours": concepts.get("overtime_day", ""),
        "overtime_night_hours": concepts.get("overtime_night", ""),
        "night_surcharge_hours": concepts.get("night_surcharge", ""),
    }.items():
        value_col = _column_by_prefix(headers, configured) if configured else None
        if value_col and headers.index(value_col) > 0:
            quantity_col = headers[headers.index(value_col) - 1]
            result[output] = data.loc[result.index, quantity_col].map(numeric)
        else:
            result[output] = 0.0

    return result.reset_index(drop=True)
