from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from agentic_nomina.models import RunMetadata

SCHEMA_VERSION = "1.0"
ALLOWED_EXTENSIONS = {".csv", ".pdf", ".xls", ".xlsx"}
REQUIRED_SOURCES = {"payroll_q1", "payroll_q2", "employees_q1", "employees_q2", "pila"}
OPTIONAL_PAIRS = (("overtime_q1", "overtime_q2"), ("loans_q1", "loans_q2"))


def validate_period(period: str | None) -> str:
    if period is None:
        return "NO_ESPECIFICADO"
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
        raise ValueError("El período de negocio debe usar el formato inequívoco YYYY-MM.")
    return period


def validate_run_id(run_id: str | None) -> str:
    if run_id is None:
        return f"RUN-{secrets.token_hex(8).upper()}"
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", run_id):
        raise ValueError("run_id debe contener 3-64 letras, números, guiones o guiones bajos.")
    return run_id


def load_external_manifest(path: str | Path) -> dict[str, Any]:
    """Read the execution-only YAML manifest without persisting its local paths."""
    try:
        content = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("El manifiesto externo no tiene YAML válido.") from error
    if not isinstance(content, dict) or content.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"El manifiesto requiere schema_version: '{SCHEMA_VERSION}'.")
    sources = content.get("sources", {})
    if not isinstance(sources, dict) or not all(isinstance(key, str) for key in sources):
        raise ValueError("El manifiesto requiere fuentes como un mapa de identificadores lógicos.")
    unknown = set(sources) - (REQUIRED_SOURCES | {item for pair in OPTIONAL_PAIRS for item in pair} | {"los_olivos", "comfatolima", "reviews", "rules", "absence_evidence"})
    if unknown:
        raise ValueError("El manifiesto contiene fuentes desconocidas: " + ", ".join(sorted(unknown)))
    return content


def resolve_run_contract(
    sources: dict[str, str | Path | None],
    *,
    period: str | None,
    run_id: str | None,
    manifest_path: str | Path | None = None,
) -> tuple[dict[str, str | Path | None], str | None, str | None, list[dict[str, str]]]:
    """Apply CLI > external manifest > defaults and retain visible contradictions."""
    diagnostics: list[dict[str, str]] = []
    if manifest_path is None:
        return sources, period, run_id, diagnostics
    external = load_external_manifest(manifest_path)
    external_sources = external["sources"]
    manifest_dir = Path(manifest_path).parent
    resolved = dict(sources)
    for name, value in external_sources.items():
        value = str((manifest_dir / value).resolve()) if not Path(value).is_absolute() else value
        if name in resolved and resolved[name] is not None and str(resolved[name]) != str(value):
            diagnostics.append({"severity": "WARNING", "code": "CLI_MANIFEST_CONTRADICTION", "message": f"La fuente CLI prevalece sobre el manifiesto para {name}."})
        elif resolved.get(name) is None:
            resolved[name] = value
    for name, cli_value, external_value in (("business_period", period, external.get("business_period")), ("run_id", run_id, external.get("run_id"))):
        if cli_value is not None and external_value is not None and cli_value != external_value:
            diagnostics.append({"severity": "WARNING", "code": "CLI_MANIFEST_CONTRADICTION", "message": f"{name} de CLI prevalece sobre el manifiesto."})
    return resolved, period if period is not None else external.get("business_period"), run_id if run_id is not None else external.get("run_id"), diagnostics


def _validate_rule_registry(config: dict[str, Any]) -> None:
    registry = config.get("rule_governance", {}).get("registry")
    if not isinstance(registry, list) or not registry:
        raise ValueError("Falta el registro esencial de reglas de gobernanza.")
    for rule in registry:
        if rule.get("active") and (not rule.get("rule_id") or not rule.get("rule_version")):
            raise ValueError("Toda regla activa requiere rule_id y rule_version.")


def preflight_sources(
    sources: dict[str, str | Path | None], config: dict[str, Any], output_path: str | Path | None = None
) -> list[dict[str, object]]:
    """Validate the real input contract before opening any payroll source."""
    _validate_rule_registry(config)
    diagnostics: list[dict[str, object]] = []
    for required in REQUIRED_SOURCES:
        if sources.get(required) is None:
            raise ValueError(f"Falta la fuente obligatoria: {required}.")
    for first, second in OPTIONAL_PAIRS:
        if (sources.get(first) is None) != (sources.get(second) is None):
            raise ValueError(f"Las fuentes opcionales {first} y {second} deben declararse juntas.")
    seen: dict[Path, str] = {}
    for name, value in sources.items():
        if value is None:
            diagnostics.append({"severity": "INFO", "code": "OPTIONAL_ABSENT", "source_name": name, "message": "Fuente opcional no declarada."})
            continue
        path = Path(value)
        if not path.is_file():
            raise ValueError(f"La fuente declarada no es un archivo regular: {name}.")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"La extensión de {name} no está admitida.")
        resolved = path.resolve()
        if resolved in seen:
            raise ValueError(f"La misma ruta se declaró para fuentes incompatibles: {seen[resolved]} y {name}.")
        seen[resolved] = name
        diagnostics.append({"severity": "INFO", "code": "SOURCE_READY", "source_name": name, "message": "Fuente validada."})
    if output_path is not None and Path(output_path).resolve() in seen:
        raise ValueError("La salida no puede sobrescribir una fuente de entrada.")
    return diagnostics


def source_manifest(sources: dict[str, str | Path | None]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for logical_name, value in sorted(sources.items()):
        required = logical_name in REQUIRED_SOURCES
        if value is None:
            rows.append({"record_type": "FUENTE", "source_name": logical_name, "required": required, "status": "OPTIONAL_ABSENT"})
            continue
        path = Path(value)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"record_type": "FUENTE", "source_name": logical_name, "required": required, "file_name": f"{logical_name}{path.suffix.lower()}", "sha256": digest, "size_bytes": path.stat().st_size, "status": "USED"})
    return rows


def build_run_metadata(
    company: str, period: str | None, run_id: str | None, sources: dict[str, str | Path | None],
    *, config: dict[str, Any] | None = None, output_path: str | Path | None = None,
    diagnostics: list[dict[str, object]] | None = None,
) -> tuple[RunMetadata, list[dict[str, object]], list[dict[str, object]]]:
    preflight = diagnostics or []
    if config is not None:
        preflight.extend(preflight_sources(sources, config, output_path))
    manifest = source_manifest(sources)
    metadata = RunMetadata(company=company, period=validate_period(period), run_id=validate_run_id(run_id), execution_timestamp=datetime.now(UTC).isoformat(), schema_version=SCHEMA_VERSION, source_files=[str(row.get("file_name", "")) for row in manifest if row["status"] == "USED"], preflight_status="WARNING" if any(row["severity"] == "WARNING" for row in preflight) else "OK")
    return metadata, manifest, preflight


def execution_frame(metadata: RunMetadata, sources: list[dict[str, object]], diagnostics: list[dict[str, object]], rules: pd.DataFrame) -> pd.DataFrame:
    base = metadata.model_dump()
    rows = [{**base, "record_type": "CORRIDA"}]
    rows.extend({**base, **row} for row in sources)
    rows.extend({**base, "record_type": "DIAGNOSTICO", **row} for row in diagnostics)
    for rule in rules.to_dict(orient="records"):
        rows.append({**base, "record_type": "REGLA", "rule_id": rule.get("rule_id"), "rule_version": rule.get("rule_version"), "rule_active": rule.get("active"), "financial": rule.get("financial"), "governance_status": rule.get("estado_aprobacion"), "operational_acceptance_pending": True})
    return pd.DataFrame(rows)
