# Agentic Nomina

Privacy-first reconciliation baseline for Colombian payroll audit workflows.

## Current scope

The baseline reconciles:

- employee master lists against first- and second-period payroll exports;
- monthly PILA detail against payroll health, pension and worked-day values;
- missing, additional and name-mismatched employees;
- monetary differences using configurable rates, rounding and tolerances;
- an Excel review workbook with summary, detailed controls and exceptions.

The engine is deterministic. AI is intentionally excluded from financial calculations and approvals.

## Data protection

Real payroll and support files must never be committed. The repository ignores raw and processed data, PDFs, Excel workbooks and CSV files. Only synthetic or explicitly anonymized fixtures may be versioned.

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
  --output "data/processed/reconciliation-feb-2026.xlsx"
```

## Architecture

- `adapters/`: source-specific extraction and normalization;
- `reconciliation/`: deterministic comparison rules;
- `reporting/`: review workbooks;
- `config/`: client mappings, rates, rounding and tolerances;
- `tests/`: synthetic regression tests.

## Next increments

1. Harden February PILA equivalence rules with the accountant.
2. Add overtime reconciliation with configurable caps and adjustments.
3. Add text-based PDFs: Los Olivos, loans and Comfatolima.
4. Add a Streamlit review interface.
5. Add OCR/vision for incapacity and permission scans with confidence gates.
