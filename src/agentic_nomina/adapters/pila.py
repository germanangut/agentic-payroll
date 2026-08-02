from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from agentic_nomina.utils import clean_text, normalize_document, numeric


def load_pila(path: str | Path, config: dict[str, Any]) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=config.get("sheet_name", "Sheet1"), header=None, dtype=object)
    cols = config["columns_zero_based"]

    result = pd.DataFrame(
        {
            "employee_id": raw.iloc[:, cols["employee_id"]].map(normalize_document),
            "employee_name": raw.iloc[:, cols["employee_name"]].map(clean_text),
            "pension_days": raw.iloc[:, cols["pension_days"]].map(numeric),
            "pension_ibc": raw.iloc[:, cols["pension_ibc"]].map(numeric),
            "pension_total_contribution": raw.iloc[:, cols["pension_total_contribution"]].map(numeric),
            "health_days": raw.iloc[:, cols["health_days"]].map(numeric),
            "health_ibc": raw.iloc[:, cols["health_ibc"]].map(numeric),
            "health_employee_contribution": raw.iloc[:, cols["health_employee_contribution"]].map(numeric),
            "ccf_days": raw.iloc[:, cols["ccf_days"]].map(numeric),
            "ccf_ibc": raw.iloc[:, cols["ccf_ibc"]].map(numeric),
            "ccf_contribution": raw.iloc[:, cols["ccf_contribution"]].map(numeric),
            "arl_days": raw.iloc[:, cols["arl_days"]].map(numeric),
            "arl_ibc": raw.iloc[:, cols["arl_ibc"]].map(numeric),
            "arl_rate": raw.iloc[:, cols["arl_rate"]].map(numeric),
            "arl_contribution": raw.iloc[:, cols["arl_contribution"]].map(numeric),
            "total_contributions": raw.iloc[:, cols["total_contributions"]].map(numeric),
        }
    )
    result = result[result["employee_id"].notna() & result["employee_name"].ne("")].copy()

    numeric_columns = [column for column in result.columns if column not in {"employee_id", "employee_name"}]
    aggregations: dict[str, str] = {column: "sum" for column in numeric_columns}
    aggregations["employee_name"] = "first"
    return result.groupby("employee_id", as_index=False).agg(aggregations)
