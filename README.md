# Agentic Nomina

Privacy-first reconciliation baseline for Colombian payroll audit workflows.

## Current scope

The baseline reconciles:

- employee master lists against first- and second-period payroll exports;
- monthly PILA detail against payroll health, pension and worked-day values;
- consolidated overtime sources against Siigo daytime, nighttime and surcharge hours;
- monthly Los Olivos invoice totals and Comfatolima expected installments against payroll deductions;
- employee-loan deductions through consecutive Siigo balance reports;
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
  --los-olivos "data/raw/LOS OLIVOS.pdf" \
  --comfatolima "data/raw/NOVEDADES AGREGADOS NACIONALES FEBRERO 2026..pdf" \
  --loans-q1 "data/raw/PRESTAMO FEBRERO 2026.pdf" \
  --loans-q2 "data/raw/PRESTAMOS 2DA QUINCENA FEBRERO 2026.pdf" \
  --output "data/processed/reconciliation-feb-2026.xlsx"
```

The overtime options and employee-loan report options are optional pairs: when one file in a pair is supplied, the other is required. Provider PDFs can be supplied independently.

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

## Next increments

1. Build a consolidated employee case file.
2. Add a human review and approval workflow.
3. Validate provisional rules incrementally with payroll/accounting owners.
4. Add incapacity and permission evidence.
5. Add the first review interface and validate reusability with a second payroll month.
