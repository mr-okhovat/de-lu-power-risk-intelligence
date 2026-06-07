# Pipeline Run Summary

- Pipeline: `DE-LU Power Risk Intelligence Sample Pipeline`
- Run label: `sample_2024-06-01_to_2024-06-03`
- Status: `PASS`
- Start date: `2024-06-01`
- End date: `2024-06-03`
- Market label: `DE-LU`
- SMARD region: `DE`
- Event study enabled: `False`
- Signal-event evaluation enabled: `False`

## Step Results

| Step | Status | Duration seconds |
|---|---:|---:|
| tests_start | PASS | 1.225 |
| smard_filter_discovery | PASS | 0.478 |
| smard_ingestion | PASS | 0.782 |
| build_staging | PASS | 0.554 |
| staging_hard_checks | PASS | 0.386 |
| build_features | PASS | 0.493 |
| build_dashboard_exports | PASS | 0.49 |
| build_risk_signals | PASS | 0.57 |
| build_risk_diagnostics | PASS | 0.481 |
| tests_end | PASS | 1.439 |

## Key Outputs

- `staging`: `data/staging/clean_hourly_DE-LU_2024-06-01_to_2024-06-03.csv`
- `features`: `data/processed/hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv`
- `dashboard_market_overview`: `dashboards/market_overview_DE-LU_2024-06-01_to_2024-06-03.csv`
- `risk_signals`: `data/processed/risk_signals_DE-LU_2024-06-01_to_2024-06-03.csv`
- `risk_diagnostics_report`: `reports/risk_diagnostics_2024-06-01_to_2024-06-03.md`

## Methodological Boundary

This automated run reproduces the currently implemented public-data analytics pipeline through risk diagnostics. It does not create a trading strategy, execution logic, or P&L claim.
