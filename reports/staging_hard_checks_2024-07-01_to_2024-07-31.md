# Staging Validation Hardening Report

- Staging file: `data/staging/clean_hourly_DE-LU_2024-07-01_to_2024-07-31.csv`
- Status: `PASS`
- Row count: `744`
- Expected hour count from timestamp span: `744`
- Duplicate timestamps: `0`
- Hourly continuity breaks: `0`

## Required Columns Missing

- None

## Missing Values

- `total_load_mw`: `0`
- `residual_load_official_mw`: `0`
- `wind_onshore_validated_mw`: `0`
- `solar_validated_mw`: `0`
- `wind_offshore_validated_mw`: `0`

## Range Violations

- `total_load_mw`: `0`
- `residual_load_official_mw`: `0`
- `wind_onshore_validated_mw`: `0`
- `solar_validated_mw`: `0`
- `wind_offshore_validated_mw`: `0`

## Residual Load Reconciliation

- Checked: `True`
- Tolerance MW: `1.0`
- Pass: `True`
- Max absolute error MW: `0.0`
- Mean absolute error MW: `0.0`
- Note: Residual reconciliation passed. Candidate renewable columns reconcile against official residual load within tolerance.

## Notes

- Residual reconciliation passed. Candidate renewable columns reconcile against official residual load within tolerance.
- Renewable component series have been promoted based on exact residual-load reconciliation evidence. This validates staging coherence, not predictive value.

## Interpretation

This hardening report checks whether the staging table is structurally reliable enough for feature engineering. It does not yet claim predictive value or trading usefulness.
