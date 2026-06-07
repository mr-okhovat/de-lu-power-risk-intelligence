# Pipeline Run Summary

- Pipeline: `DE-LU Power Risk Intelligence Sample Pipeline`
- Run label: `sample_2024-06-01_to_2024-06-03`
- Status: `FAIL`
- Dry run: `False`
- Start date: `2024-06-01`
- End date: `2024-06-03`
- Market label: `DE-LU`
- SMARD region: `DE`
- Resolution: `hour`
- Filters: `['410', '4359', '4067', '4068', '1225']`

## Step Results

| Step | Status | Duration seconds |
|---|---:|---:|
| tests_start | PASS | 1.128 |
| smard_filter_discovery | PASS | 0.384 |
| smard_ingestion | PASS | 0.863 |
| build_staging | PASS | 0.536 |
| staging_hard_checks | PASS | 0.387 |
| build_features | PASS | 0.472 |
| build_dashboard_exports | PASS | 0.494 |
| build_risk_signals | PASS | 0.596 |
| build_risk_diagnostics | PASS | 0.606 |
| build_event_study_skeleton | FAIL | 0.474 |

## Key Outputs

- `staging`: `data/staging/clean_hourly_DE-LU_2024-06-01_to_2024-06-03.csv`
- `features`: `data/processed/hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv`
- `dashboard_market_overview`: `dashboards/market_overview_DE-LU_2024-06-01_to_2024-06-03.csv`
- `risk_signals`: `data/processed/risk_signals_DE-LU_2024-06-01_to_2024-06-03.csv`
- `risk_diagnostics_report`: `reports/risk_diagnostics_2024-06-01_to_2024-06-03.md`
- `event_labels`: `data/processed/event_labels_DE-LU_2024-06-01_to_2024-06-03.csv`
- `signal_event_evaluation`: `data/processed/signal_event_evaluation_DE-LU_2024-06-01_to_2024-06-03.csv`
- `signal_event_report`: `reports/signal_event_evaluation_2024-06-01_to_2024-06-03.md`

## Methodological Boundary

This automated run reproduces the current public-data analytics pipeline. It does not create a trading strategy, execution logic, or P&L claim.
