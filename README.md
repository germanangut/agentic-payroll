# Agentic Nomina

Privacy-first reconciliation baseline for Colombian payroll audit workflows.

## Current scope

The baseline reconciles:

- employee master lists against first- and second-period payroll exports;
- monthly PILA detail against payroll health, pension and worked-day values;
- consolidated overtime sources against Siigo daytime, nighttime and surcharge hours;
- configurable provisional caps, lower bounds, tolerances and rule versions;
- missing, additional and name-mismatched employees;
- an Excel review workbook with summary, detailed controls and a normalized exception registry.

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
  --output "data/processed/reconciliation-feb-2026.xlsx"
```

The two overtime options are optional, but they must be supplied together.

## Overtime rule semantics

- Raw hours remain visible in the output.
- Expected hours are produced through configurable provisional rules.
- A clean match without adjustment is `OK`.
- A match after applying a cap or zero floor is `WARNING`.
- An unexplained difference is `REVIEW`.
- Active hours present in only one entire source are `BLOCKING`.
- No provisional result is treated as an approved payroll correction.

## Architecture

- `adapters/`: source-specific extraction and normalization;
- `reconciliation/`: deterministic comparison rules;
- `reporting/`: review workbooks and normalized exceptions;
- `config/`: client mappings, rule versions, caps, rates, rounding and tolerances;
- `tests/`: synthetic regression tests.

## Next increments

1. Add Los Olivos and Comfatolima reconciliation.
2. Add loan balance-movement reconciliation.
3. Build a consolidated employee case file.
4. Add a human review and approval workflow.
5. Validate provisional rules incrementally with payroll/accounting owners.
