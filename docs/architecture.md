# Baseline architecture

The prototype separates source adapters, normalized records, deterministic rules and reports.

```text
Excel/PDF source -> adapter -> canonical data -> reconciliation rules -> exceptions/report
```

## Guardrails

- The LLM will not calculate, alter or approve payroll values.
- Each difference must preserve both source values and the applied rule.
- Rates, rounding and tolerances are configuration, not prompt instructions.
- Client files remain local or in approved encrypted storage and are excluded from Git.
