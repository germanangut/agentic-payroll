from __future__ import annotations

from pathlib import Path

import pandas as pd


def _summary_frame(employee_results: dict[str, pd.DataFrame], social: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label, frame in employee_results.items():
        counts = frame["severity"].value_counts().to_dict()
        rows.append(
            {
                "module": f"Employees {label}",
                "total": len(frame),
                "ok": counts.get("OK", 0),
                "warning": counts.get("WARNING", 0),
                "review": counts.get("REVIEW", 0),
                "blocking": counts.get("BLOCKING", 0),
            }
        )
    social_statuses = social[["health_severity", "pension_severity", "days_severity"]].stack()
    counts = social_statuses.value_counts().to_dict()
    rows.append(
        {
            "module": "Social security controls",
            "total": len(social_statuses),
            "ok": counts.get("OK", 0),
            "warning": counts.get("WARNING", 0),
            "review": counts.get("REVIEW", 0),
            "blocking": counts.get("BLOCKING", 0),
        }
    )
    return pd.DataFrame(rows)


def write_report(
    output: str | Path,
    employee_results: dict[str, pd.DataFrame],
    social: pd.DataFrame,
) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _summary_frame(employee_results, social).to_excel(writer, sheet_name="Resumen", index=False)
        for label, frame in employee_results.items():
            safe_label = label.replace(" ", "_")[:20]
            frame.to_excel(writer, sheet_name=f"Empleados_{safe_label}", index=False)
        social.to_excel(writer, sheet_name="Seguridad_Social", index=False)
        exceptions = social[
            social[["health_severity", "pension_severity", "days_severity"]]
            .ne("OK")
            .any(axis=1)
        ]
        exceptions.to_excel(writer, sheet_name="Excepciones", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for column_cells in worksheet.columns:
                width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 38)
                worksheet.column_dimensions[column_cells[0].column_letter].width = width
