from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader

from agentic_nomina.utils import clean_text, normalize_document, numeric

_LOAN_HEADER = re.compile(
    r"^(?P<employee_id>\d{6,12})\s+(?P<name>.+?)\s+"
    r"C U E N T A:\s*\d+\s+PRESTAMOS A TRABAJADORES\s+"
    r"(?P<opening_balance>[\d,.]+)$"
)
_MONEY = re.compile(r"\d[\d,]*\.\d{2}")
_MOVEMENT = re.compile(
    r"^(?P<reference>[A-Z]-\d{3}-\d+-\d{3})\s+"
    r"(?P<date>\d{4}/\d{2}/\d{2})\s+(?P<detail>.+)$"
)


def _page_text(path: str | Path) -> list[str]:
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]


def _money(value: str) -> float:
    return numeric(value.replace(",", ""))


def _finalize_record(
    record: dict[str, object],
    amounts: list[float],
    *,
    total_page: int,
    total_row: int,
) -> dict[str, object]:
    if not amounts:
        raise ValueError("Loan employee total line did not contain a balance.")
    if len(amounts) == 1:
        debits = 0.0
        credits = 0.0
        reported_balance = amounts[0]
    elif len(amounts) == 2:
        debits = amounts[0]
        credits = 0.0
        reported_balance = amounts[1]
    else:
        debits = amounts[-3]
        credits = amounts[-2]
        reported_balance = amounts[-1]

    record["period_debits"] = debits
    record["period_credits"] = credits
    record["reported_balance"] = reported_balance
    record["source_total_page"] = total_page
    record["source_total_row"] = total_row
    return record


def parse_loan_balance_text(
    pages: list[str], *, source_file: str, period_label: str
) -> pd.DataFrame:
    """Parse a Siigo detailed-by-third-party employee-loan balance report."""
    rows: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    movement_references: list[str] = []

    for page_number, text in enumerate(pages, start=1):
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = clean_text(raw_line)
            header_match = _LOAN_HEADER.match(line)
            if header_match:
                if current is not None:
                    raise ValueError(
                        "A new loan employee record started before the prior TOTAL line."
                    )
                values = header_match.groupdict()
                current = {
                    "period_label": period_label,
                    "employee_id": normalize_document(values["employee_id"]),
                    "employee_name": clean_text(values["name"]),
                    "opening_balance": _money(values["opening_balance"]),
                    "movement_count": 0,
                    "movement_references": "",
                    "source_file": source_file,
                    "source_page": page_number,
                    "source_row": line_number,
                }
                movement_references = []
                continue

            if current is None:
                continue

            movement_match = _MOVEMENT.match(line)
            if movement_match:
                current["movement_count"] = int(current["movement_count"]) + 1
                movement_references.append(movement_match.group("reference"))
                continue

            if line.startswith("TOTAL GENERAL"):
                continue
            if line.startswith("TOTAL"):
                amounts = [_money(value) for value in _MONEY.findall(line)]
                current["movement_references"] = ", ".join(movement_references)
                rows.append(
                    _finalize_record(
                        current,
                        amounts,
                        total_page=page_number,
                        total_row=line_number,
                    )
                )
                current = None
                movement_references = []

    if current is not None:
        raise ValueError("Loan report ended before the final employee TOTAL line.")
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No employee loan balance rows were found in the PDF.")
    return frame


def load_loan_balance_report(
    path: str | Path, config: dict[str, Any], period_label: str
) -> pd.DataFrame:
    frame = parse_loan_balance_text(
        _page_text(path),
        source_file=Path(path).name,
        period_label=period_label,
    )
    report_config = config.get("reports", {}).get(period_label.lower(), {})
    expected_balance = report_config.get("expected_reported_total")
    expected_debits = report_config.get("expected_debit_total")
    observed_balance = float(frame["reported_balance"].sum())
    observed_debits = float(frame["period_debits"].sum())
    if expected_balance is not None and observed_balance != float(expected_balance):
        raise ValueError(
            "Loan extracted balance total does not match configured report total: "
            f"{observed_balance} != {expected_balance}."
        )
    if expected_debits is not None and observed_debits != float(expected_debits):
        raise ValueError(
            "Loan extracted debit total does not match configured report total: "
            f"{observed_debits} != {expected_debits}."
        )
    return frame
