from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

import pandas as pd

from agentic_nomina.utils import canonical_text


def find_header_row(frame: pd.DataFrame, markers: Iterable[str]) -> int:
    wanted = {canonical_text(marker) for marker in markers}
    for index, row in frame.iterrows():
        present = {canonical_text(value) for value in row.tolist() if canonical_text(value)}
        if wanted.issubset(present):
            return int(index)
    raise ValueError(f"Could not locate header row containing markers: {sorted(wanted)}")


def unique_headers(values: list[object]) -> list[str]:
    counts: Counter[str] = Counter()
    headers: list[str] = []
    for position, value in enumerate(values):
        base = canonical_text(value) or f"COLUMN_{position}"
        counts[base] += 1
        headers.append(base if counts[base] == 1 else f"{base}__{counts[base]}")
    return headers
