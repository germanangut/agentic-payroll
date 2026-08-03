# Agentic Nomina

Privacy-first reconciliation baseline for Colombian payroll audit workflows.

## Current scope

The baseline reconciles:

- employee master lists against first- and second-period payroll exports;
- monthly PILA detail against payroll health, pension and worked-day values;
- consolidated overtime sources against Siigo daytime, nighttime and surcharge hours;
- monthly Los Olivos invoice totals and Comfatolima expected installments against payroll deductions;
- employee-loan deductions through consecutive Siigo balance reports;
- a consolidated employee case file across every enabled control;
- configurable provisional caps, lower bounds, tolerances and rule versions;
- missing, additional and name-mismatched employees;
- an Excel review workbook with summary, detailed controls and a normalized exception registry.
- a human review ledger that preserves auditable decisions across reconciliation runs.
- a versioned payroll-rule registry with version-specific approval evidence.

The engine is deterministic. AI is intentionally excluded from financial calculations and
approvals.

## Data protection

Real payroll and support files must never be committed. The repository ignores raw and processed
data, PDFs, Excel workbooks and CSV files. Only synthetic or explicitly anonymized fixtures may be
versioned.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
pytest
```

## Run the February baseline

Place the client files under `data/raw/` locally and run:

```bash
agentic-nomina reconcile \
  --payroll-q1 "data/raw/1RA NOMINA FEBRERO 2026.xlsx" \
  --payroll-q2 "data/raw/2DA NOMINA FEBRERO 2026 (3).xlsx" \
  --employees-q1 "data/raw/Lista de empleados 15 feb 26.xlsx" \
  --employees-q2 "data/raw/LISTA DE EMPLEADOS.xlsx" \
  --pila "data/raw/Planilla febrero 2026 (1).xlsx" \
  --overtime-q1 "data/raw/PLANILLA EXTRAS 30 Ene al 12 Feb.xlsx" \
  --overtime-q2 "data/raw/PLANILLA EXTRAS 13 Febrero al 28.xlsx" \
  --los-olivos "data/raw/LOS OLIVOS.pdf" \
  --comfatolima "data/raw/NOVEDADES AGREGADOS NACIONALES FEBRERO 2026..pdf" \
  --loans-q1 "data/raw/PRESTAMO FEBRERO 2026.pdf" \
  --loans-q2 "data/raw/PRESTAMOS 2DA QUINCENA FEBRERO 2026.pdf" \
  --reviews "data/processed/reconciliation-feb-2026-previous.xlsx" \
  --output "data/processed/reconciliation-feb-2026.xlsx"
```

The overtime options and employee-loan report options are optional pairs: when one file in a pair is supplied, the other is required. Provider PDFs can be supplied independently. `--reviews` is optional and accepts a prior report or a CSV ledger.

## Manifiesto de corrida y preflight

Cada ejecución tiene un `run_id`, un período técnico opcional `YYYY-MM`, marca UTC y versión
de esquema. `--period` y `--run-id` son aditivos; si no se indica período se exporta
`NO_ESPECIFICADO` y si no se indica identificador se genera uno. Antes de leer una fuente, el
preflight valida las cinco fuentes obligatorias, los pares reales de horas extra y préstamos,
archivos regulares, extensiones permitidas, rutas repetidas, registro de reglas activo y una
salida que no pueda sobrescribir una entrada. No inspecciona ni expone registros de nómina.

También puede usarse un manifiesto YAML local de ejecución:

```yaml
schema_version: "1.0"
business_period: "2026-02"
run_id: "SINTETICO-2026-02"
sources:
  payroll_q1: "data/raw/synthetic-payroll-q1.xlsx"
  payroll_q2: "data/raw/synthetic-payroll-q2.xlsx"
  employees_q1: "data/raw/synthetic-employees-q1.xlsx"
  employees_q2: "data/raw/synthetic-employees-q2.xlsx"
  pila: "data/raw/synthetic-pila.xlsx"
```

Use `--manifest ruta.yml`. La precedencia es CLI, manifiesto y finalmente los valores
generados/default compatibles; una contradicción CLI/manifiesto queda como advertencia visible.
Las rutas sólo se usan durante la ejecución: la hoja `Ejecucion` conserva un nombre base
sanitizado a partir del identificador lógico, SHA-256, tamaño, identificador lógico, estado y diagnósticos. Incluye además las reglas
activas, versión, gobernanza y naturaleza financiera, sin valores de nómina ni datos personales.
El hash identifica el archivo exacto, pero no sustituye la política de retención ni la evidencia
operativa.

## Demostración sintética reproducible

Desde un clon limpio puede recorrerse el flujo completo sin archivos reales:

```bash
agentic-nomina demo --output-dir C:\temp\agentic-nomina-demo
```

El directorio debe ser explícito y estar vacío o no existir; el comando nunca borra ni
sobrescribe contenido. Genera entradas ficticias, `manifest.yml`, `summary.json` y
`results/agentic-nomina-demo.xlsx`, ejecutando el mismo manifiesto, preflight, servicio y
exportador de `reconcile`. El período por defecto es el técnico sintético `2099-01`; puede
sobrescribirse con `--period` y el identificador puede fijarse con `--run-id`.

Inspeccione `Ejecucion`, `Resumen`, `Excepciones`, `Revisiones`, `Casos_Empleado` y `Reglas`.
Los artefactos se marcan **SINTÉTICO — DEMOSTRACIÓN — SIN EFECTO FINANCIERO**, no deben
publicarse y pueden eliminarse manualmente cuando el operador lo decida. La demo no constituye
validación laboral, contable, tributaria ni regulatoria.

## Rule governance

- `Reglas` is the editable versioned rule register included in every generated workbook.
- Approval states are `PENDIENTE`, `EN_VALIDACION`, `APROBADA` and `RECHAZADA`.
- An approval belongs to exactly one `rule_id` and `rule_version`; approved entries require a responsible person, date and evidence.
- Reusing a prior workbook with `--rules` rejects duplicate, unknown and obsolete rule-version approvals.
- Use `--require-approved-rules` to block the run unless every active financial rule has a complete `APROBADA` entry for its current version.
- The existing `Revisiones` human-exception ledger remains independent and compatible.

### Operational validation

- Rule validations are version-specific and use `PENDIENTE`, `EN_VALIDACION`, `VALIDADA`, `APROBADA` or `RECHAZADA`.
- `VALIDADA` is technical/operational evidence review; only a complete `APROBADA` record satisfies strict financial-rule mode.
- New records require an auditable responsible id and role, evidence type/reference, explicit decision/date and validation record id. Legacy rows are read conservatively and never become approved implicitly.
- `rule_governance.authorization_matrix` is a synthetic provisional policy. Real authorized roles and evidence types remain an operational acceptance requirement from payroll/accounting.
- `Reglas` shows current rule-version state and `Reglas_Validaciones` exposes the exported audit trail; evidence documents remain external references only.

## Human review workflow

- Every exception receives a deterministic `exception_id` based on its material facts.
- The `Revisiones` sheet is the editable human decision ledger; deterministic calculation sheets remain unchanged.
- Review statuses are `PENDIENTE`, `EN_REVISION`, `RESUELTO` and `ESCALADO`.
- Decisions are `CONFIRMADO`, `FALSO_POSITIVO` and `CORRECCION_REQUERIDA`.
- A resolved item requires a decision, reviewer and review date.
- If a finding changes materially, it receives a new identifier and returns to `PENDIENTE`.
- A stale or unknown identifier blocks the run instead of silently transferring an old approval.

## Multi-period review continuity

- `revision_id` is period-specific; it never transfers between reporting periods.
- `material_fingerprint` compares only material content: module, employee, control, expected and actual values, difference, severity, rule id/version and evidence file. It excludes period, row position and cosmetic notes.
- A prior exact match is audit context only by default. Financial approvals never transfer between periods.
- A non-financial `FALSO_POSITIVO` may be reused only for a configured rule id, one complete exact precedent and no ambiguity.
- Operational acceptance with a real second payroll month remains pending; synthetic two-period fixtures validate the technical continuity contract.

## Días cotizados y ausencias

- La diferencia observada es `días nómina - días de salud PILA`; sus valores fuente nunca se modifican.
- La regla `absence_aware_contributed_days` sólo aporta una explicación provisional no financiera cuando una incapacidad sintética en días completos coincide exactamente y en la dirección configurada.
- Horas, fracciones, solapamientos, períodos ambiguos, evidencia incompleta o coincidencias parciales permanecen en `REVIEW`; no se convierten horas a días.
- La explicación no autoriza correcciones de PILA, pagos ni aportes. La definición real de tipos elegibles, jornada, festivos y distribución entre períodos sigue pendiente de nómina/contabilidad.

## Overtime rule semantics

- Raw hours remain visible in the output.
- Expected hours are produced through configurable provisional rules.
- A clean match without adjustment is `OK`.
- A match after applying a cap or zero floor is `WARNING`.
- An unexplained difference is `REVIEW`.
- Active hours present in only one entire source are `BLOCKING`.
- No provisional result is treated as an approved payroll correction.

## External deduction semantics

- Provider PDFs are text-extracted locally and normalized by employee identifier.
- The February provider amount is compared with the second-period payroll deduction.
- A direct value match is `OK`.
- A matched employee with a different deduction is `REVIEW`.
- An active provider amount with no payroll employee match is `BLOCKING`.
- Provider balances and arrears remain context only; the engine does not alter payroll.

## Employee-loan rule semantics

- Each report preserves opening balance, period debits, period credits and reported balance.
- The first-period expected deduction is the reduction from its reported balance to the next report's opening balance.
- A missing employee in the next report is provisionally interpreted as a zero opening balance, allowing fully paid loans to reconcile.
- The last available period is `WARNING` with `PENDING_NEXT_CUTOFF`; its projected closing balance is diagnostic until the following report is available.
- A payroll deduction without a source balance, or a deduction exceeding the reported balance, is `BLOCKING`. Unexplained balance differences are `REVIEW`.
- These rules are provisional and do not authorize accounting or payroll adjustments.

## Architecture

- `adapters/`: source-specific extraction and normalization;
- `reconciliation/`: deterministic comparison rules;
- `reporting/`: review workbooks and normalized exceptions;
- `config/`: client mappings, rule versions, caps, rates, rounding and tolerances;
- `tests/`: synthetic regression tests.

## Límites operativos pendientes

Ausencias, continuidad multiperíodo y la interfaz de revisión en Excel ya están implementadas
con datos sintéticos. Continúan pendientes la convención productiva de período y nombres de
fuentes, retención de hashes/metadatos, matriz real de roles y evidencias, y la aceptación
operativa y regulatoria por nómina y contabilidad. El manifiesto no cambia cálculos, días,
bases, aportes, descuentos ni pagos.
