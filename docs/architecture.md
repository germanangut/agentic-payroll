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
