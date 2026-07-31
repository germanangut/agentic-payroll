# February 2026 local validation

This validation was executed locally against the client files. No client workbook, PDF, personal identifier or row-level result is committed.

## Source cardinalities

- First-period employee master: 109 unique employees.
- First-period payroll: 108 unique employees.
- Expected first-period exception: one master employee absent from payroll with non-active status `V`.
- Second-period employee master: 110 unique employees.
- Second-period payroll: 110 unique employees.
- Monthly PILA: 111 unique contributors.
- Expected PILA exception: one contributor not present in the second-period payroll.

## Baseline output

The engine generated a local Excel workbook with:

- summary controls;
- first- and second-period employee reconciliation;
- monthly health, pension and day comparisons;
- an exceptions-only sheet.

The current health and pension expectations use configurable 4% employee rates, rounding to COP 100 and a COP 200 tolerance. These are implementation assumptions for the prototype and require accountant approval before they can become approval rules.

Worked-day comparison currently uses the Siigo `SUELDO BASICO` quantity. It deliberately exposes cases involving vacation, leave, incapacity or other payroll concepts; the final contributed-day formula remains a domain-rule backlog item.
