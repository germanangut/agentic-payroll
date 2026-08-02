from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from agentic_nomina.utils import clean_text, normalize_document, numeric


def load_overtime_summary(
    path: str | Path,
    config: dict[str, Any],
    period_label: str,
) -> pd.DataFrame:
    """Load the consolidated overtime sheet using configured zero-based columns."""
    sheet_name = config.get("sheet_name", "TOTAL HORAS EXTRAS")
    header_row = int(config.get("header_row_zero_based", 1))
    columns = config["columns_zero_based"]
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=object)
    data = raw.iloc[header_row + 1 :].copy()

    result = pd.DataFrame(
        {
            "employee_id": data.iloc[:, columns["employee_id"]].map(normalize_document),
            "employee_name": data.iloc[:, columns["employee_name"]].map(clean_text),
            "employee_group": data.iloc[:, columns["group"]].map(clean_text),
            "cost_center": data.iloc[:, columns["cost_center"]].map(clean_text),
            "subcost_center": data.iloc[:, columns["subcost_center"]].map(clean_text),
            "role": data.iloc[:, columns["role"]].map(clean_text),
            "reported_day_hours": data.iloc[:, columns["reported_day_hours"]].map(numeric),
            "reported_night_hours": data.iloc[:, columns["reported_night_hours"]].map(numeric),
            "reported_surcharge_hours": data.iloc[:, columns["reported_surcharge_hours"]].map(
                numeric
            ),
            "pending_day_hours": data.iloc[:, columns["pending_day_hours"]].map(numeric),
            "pending_night_hours": data.iloc[:, columns["pending_night_hours"]].map(numeric),
            "pending_surcharge_hours": data.iloc[
                :, columns["pending_surcharge_hours"]
            ].map(numeric),
            "deduct_hours": data.iloc[:, columns["deduct_hours"]].map(numeric),
            "period_label": period_label,
            "source_file": Path(path).name,
            "source_sheet": sheet_name,
            "source_row": data.index + 1,
        }
    )
    result = result[result["employee_id"].notna() & result["employee_name"].ne("")].copy()

    if result["employee_id"].duplicated().any():
        numeric_columns = [
            "reported_day_hours",
            "reported_night_hours",
            "reported_surcharge_hours",
            "pending_day_hours",
            "pending_night_hours",
            "pending_surcharge_hours",
            "deduct_hours",
        ]
        aggregations: dict[str, Any] = {column: "sum" for column in numeric_columns}
        for column in [
            "employee_name",
            "employee_group",
            "cost_center",
            "subcost_center",
            "role",
            "period_label",
            "source_file",
            "source_sheet",
        ]:
            aggregations[column] = "first"
        aggregations["source_row"] = lambda rows: ",".join(
            str(int(row)) for row in sorted(set(rows))
        )
        result = result.groupby("employee_id", as_index=False).agg(aggregations)

    return result.reset_index(drop=True)
