from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    REVIEW = "REVIEW"
    BLOCKING = "BLOCKING"


class ReconciliationSummary(BaseModel):
    total: int = 0
    ok: int = 0
    warning: int = 0
    review: int = 0
    blocking: int = 0


class RunMetadata(BaseModel):
    company: str
    period: str = "NO_ESPECIFICADO"
    run_id: str
    execution_timestamp: str
    schema_version: str = "1.0"
    source_files: list[str] = Field(default_factory=list)
    preflight_status: str = "OK"
