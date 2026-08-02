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

## Provisional overtime validation

The overtime increment was executed locally against both February overtime workbooks and the two
Siigo payroll exports. No client workbook or row-level result is committed.

- 220 employee-period records were evaluated.
- 660 concept controls were generated across daytime overtime, nighttime overtime and nighttime
  surcharge.
- 143 employee-period records were fully `OK`.
- 73 records were `WARNING`, primarily because a provisional cap or zero-floor adjustment was
  applied and the adjusted hours matched payroll.
- 3 records were `REVIEW` because source and payroll hours still differed after applying the
  provisional rules.
- 1 record was `BLOCKING` because the overtime source contained active hours for an employee absent
  from the payroll export.

The observed February behavior supports a provisional 24-hour cap for daytime overtime. One
first-period case also shows payroll limiting both nighttime overtime and nighttime surcharge to 24
hours, so the prototype keeps all three caps configurable and explicitly provisional.

The monetary estimates in the detailed output use the hourly rate observed in the payroll export.
They are diagnostic estimates, not an independent recalculation of legally payable overtime.


## External deductions validation

The structured-PDF adapters were executed locally against the February Los Olivos invoice and
Comfatolima credit report, then compared with the second-period Siigo payroll export.

### Los Olivos

- 31 primary affiliate deductions were extracted.
- Provider total: COP 699,200.
- Payroll total: COP 699,200.
- 31 exact matches and no exceptions.

### Comfatolima

- 42 credit rows were extracted; 39 contained an active February expected amount.
- Expected February total: COP 7,435,735.
- Payroll deduction total: COP 6,536,650.
- Total difference: COP -899,085 from payroll relative to the provider source.
- 38 records were `OK`, including inactive zero-amount rows.
- 3 active provider records were `BLOCKING` because the employees were absent from payroll.
- 1 active employee was `REVIEW` because the expected COP 188,294 deduction was zero in payroll.

These classifications are evidence for review, not approved payroll corrections.


## Employee-loan balance validation

The two Siigo loan balance PDFs were parsed locally and compared with the `PRESTAMOS Y/O ANT`
payroll deductions.

### First period

- 10 employee loan balances were extracted.
- Reported balance total before the payroll reduction: COP 3,829,379.
- New loan debits within the report: COP 900,000.
- Next-report opening balances for those loans: COP 2,803,397.
- Expected reduction by balance movement: COP 1,025,982.
- Payroll deductions: COP 1,025,982.
- 10 exact `OK` matches and no exceptions.

### Second period

- 12 employee loan balances were extracted.
- Reported balance total: COP 3,503,397.
- New loan debits within the report: COP 700,000.
- Payroll deductions: COP 857,836.
- Projected post-payroll balance: COP 2,645,561.
- All 12 records are `WARNING` with `PENDING_NEXT_CUTOFF` because a March opening-balance report is required to validate the movement.

The balance movement is a provisional interpretation of the Siigo reports. It requires confirmation
from payroll/accounting before the rule lifecycle can move from `PROVISIONAL` to `VALIDATED`.
