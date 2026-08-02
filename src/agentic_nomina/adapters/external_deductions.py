from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader

from agentic_nomina.utils import clean_text, normalize_document, numeric

_LOS_OLIVOS_ROW = re.compile(
    r"^(?P<name>[A-ZÁÉÍÓÚÑÜ ]+?)(?P<employee_id>\d{6,12})CCT\s*-\s*"
    r"(?P<period_end>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<base_value>[\d.]+)\s+(?P<expected_value>[\d.]+)"
    r"(?P<period_start>\d{2}/\d{2}/\d{4})"
)

_COMFATOLIMA_ROW = re.compile(
    r"^(?P<credit_id>\d+)\s+(?P<employee_id>\d+)\s+(?P<name>.+?)\s+"
    r"\$\s*(?P<principal>[\d.]+)\s+"
    r"(?P<start_date>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<end_date>\d{2}/\d{2}/\d{4})\s+"
    r"\$\s*(?P<installment>[\d.]+)\s+"
    r"\$\s*(?P<november>[\d.]+)\s+"
    r"\$\s*(?P<december>[\d.]+)\s+"
    r"\$\s*(?P<january>[\d.]+)\s+"
    r"\$\s*(?P<february>[\d.]+)\s+"
    r"\$\s*(?P<arrears>[\d.]+)$"
)


def _page_text(path: str | Path) -> list[str]:
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]


def _provider_money(value: str) -> float:
    return numeric(value.replace(".", ""))


def parse_los_olivos_text(
    pages: list[str], *, source_file: str, period_label: str = "MONTH"
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for page_number, text in enumerate(pages, start=1):
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = _LOS_OLIVOS_ROW.match(clean_text(line))
            if not match:
                continue
            values = match.groupdict()
            rows.append(
                {
                    "provider": "LOS_OLIVOS",
                    "period_label": period_label,
                    "employee_id": normalize_document(values["employee_id"]),
                    "employee_name": clean_text(values["name"]),
                    "expected_value": _provider_money(values["expected_value"]),
                    "base_value": _provider_money(values["base_value"]),
                    "period_start": values["period_start"],
                    "period_end": values["period_end"],
                    "source_file": source_file,
                    "source_page": page_number,
                    "source_row": line_number,
                    "source_reference": None,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No Los Olivos primary affiliate rows were found in the PDF.")
    return frame


def load_los_olivos(
    path: str | Path, config: dict[str, Any]
) -> pd.DataFrame:
    frame = parse_los_olivos_text(
        _page_text(path),
        source_file=Path(path).name,
        period_label=str(config.get("period_label", "MONTH")),
    )
    expected_total = config.get("expected_total")
    if expected_total is not None:
        observed_total = float(frame["expected_value"].sum())
        if observed_total != float(expected_total):
            raise ValueError(
                "Los Olivos extracted total does not match configured document total: "
                f"{observed_total} != {expected_total}."
            )
    return frame


def parse_comfatolima_text(
    pages: list[str], *, source_file: str, period_label: str = "MONTH"
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for page_number, text in enumerate(pages, start=1):
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = _COMFATOLIMA_ROW.match(clean_text(line))
            if not match:
                continue
            values = match.groupdict()
            rows.append(
                {
                    "provider": "COMFATOLIMA",
                    "period_label": period_label,
                    "employee_id": normalize_document(values["employee_id"]),
                    "employee_name": clean_text(values["name"]),
                    "expected_value": _provider_money(values["february"]),
                    "credit_id": values["credit_id"],
                    "principal": _provider_money(values["principal"]),
                    "installment": _provider_money(values["installment"]),
                    "start_date": values["start_date"],
                    "end_date": values["end_date"],
                    "arrears": _provider_money(values["arrears"]),
                    "source_file": source_file,
                    "source_page": page_number,
                    "source_row": line_number,
                    "source_reference": values["credit_id"],
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No Comfatolima credit rows were found in the PDF.")
    return frame


def load_comfatolima(
    path: str | Path, config: dict[str, Any]
) -> pd.DataFrame:
    return parse_comfatolima_text(
        _page_text(path),
        source_file=Path(path).name,
        period_label=str(config.get("period_label", "MONTH")),
    )
