# Baseline architecture

The prototype separates source adapters, normalized records, deterministic rules and reports.

```text
Excel/PDF source -> adapter -> canonical data -> versioned rules -> exceptions/report
```

## Guardrails

- The LLM will not calculate, alter or approve payroll values.
- Each difference preserves source values, source location and the applied rule.
- Rates, caps, rounding and tolerances are configuration, not prompt instructions.
- Provisional rules generate evidence and review signals; they do not confirm payroll errors.
- Client files remain local or in approved encrypted storage and are excluded from Git.

## Provisional rule lifecycle

Every inferred rule must carry an identifier, version and lifecycle status:

- `PROVISIONAL`: inferred from observed source behavior and subject to review;
- `VALIDATED`: confirmed by an authorized payroll/accounting owner;
- `DEPRECATED`: retained for historical traceability but no longer active.

The overtime increment applies configurable lower bounds and caps before comparing source hours
with Siigo hours. A match produced by an adjustment is a `WARNING`, not an unconditional `OK`.
An unexplained mismatch is `REVIEW`; an active amount missing from one entire source is
`BLOCKING`.


## Structured PDF deduction lane

Los Olivos and Comfatolima use a deterministic text-PDF lane:

```text
structured PDF -> page text -> provider parser -> canonical deduction record
               -> employee-id join -> provisional comparison -> report/exception
```

The provider parser stores page and extracted-line references. The comparison uses the second-period
payroll deduction because both February sources are monthly statements reflected in that payroll export.
Missing active provider records are `BLOCKING`; matched value differences are `REVIEW`.


## Employee-loan balance lane

Employee loans use consecutive Siigo detailed-by-third-party reports:

```text
period report -> opening/movements/reported balance -> employee-id join
              -> next-period opening balance + payroll deduction
              -> deterministic balance movement -> report/exception
```

For a period with a following report, the expected payroll deduction is the prior reported balance
minus the next report's opening balance. An employee absent from the next report is provisionally
assigned a zero opening balance so fully paid loans remain reconcilable. For the final available
period, the engine calculates a projected closing balance but emits `PENDING_NEXT_CUTOFF` as a
`WARNING`; it does not claim the deduction is validated until another report is supplied.
