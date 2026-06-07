# Phase 2B — Staging Validation Hardening

## Scope

This phase adds structural hard checks to the staging table before feature engineering.

## Created files

- src/data_quality/staging_hard_checks.py
- tests/test_staging_hard_checks.py

## Checks

- required columns
- row count
- duplicate timestamps
- hourly continuity
- missing values
- value range violations
- residual-load reconciliation

## Reconciliation Formula

```text
derived_residual_load = total_load - wind_candidate - solar_candidate - wind_offshore_candidate
```

This is compared against `residual_load_official_mw`.

## Acceptance

- Tests pass.
- Staging hard-check report is generated.
- Residual reconciliation passes within tolerance.
- Status is either PASS or PASS WITH LIMITATION.
- If status is STOP — NEEDS VERIFICATION, the project must not proceed to feature engineering.
