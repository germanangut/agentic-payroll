from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return " ".join(str(value).strip().split())


def canonical_text(value: Any) -> str:
    text = clean_text(value).upper()
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def normalize_document(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    digits = re.sub(r"\D", "", str(value))
    return digits or None


def numeric(value: Any) -> float:
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(" ", "")
    if not text:
        return 0.0
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def round_money(value: float, unit: int = 100) -> float:
    if unit <= 1:
        return float(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    units = Decimal(str(value)) / Decimal(unit)
    rounded = units.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(rounded * Decimal(unit))
