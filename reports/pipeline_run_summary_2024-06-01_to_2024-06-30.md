# Pipeline run summary

Pipeline: DE-LU Power Risk Intelligence — June 2024
Run: june_2024
Status: FAIL
Window: 2024-06-01 to 2024-06-30
Market: DE-LU
SMARD region: DE

## Steps

| step | status | seconds |
|---|---:|---:|
| tests_start | PASS | 1.286 |
| smard_filter_discovery | PASS | 0.368 |
| smard_ingestion | PASS | 1.281 |
| build_staging | PASS | 0.766 |
| staging_hard_checks | PASS | 0.384 |
| build_features | PASS | 0.685 |
| build_dashboard_exports | PASS | 0.543 |
| build_risk_signals | PASS | 1.039 |
| build_risk_diagnostics | PASS | 0.513 |
| build_reviewer_pack | FAIL | 0.388 |

## Outputs

- features: `data/processed/hourly_features_DE-LU_2024-06-01_to_2024-06-30.csv` (yes)
- market_export: `dashboards/market_overview_DE-LU_2024-06-01_to_2024-06-30.csv` (yes)
- reviewer_pack: `reports/reviewer_pack_2024-06-01_to_2024-06-30.md` (yes)
- reviewer_pack_json: `reports/reviewer_pack_2024-06-01_to_2024-06-30.json` (yes)
- risk_diagnostics_json: `reports/risk_diagnostics_2024-06-01_to_2024-06-30.json` (yes)
- risk_diagnostics_report: `reports/risk_diagnostics_2024-06-01_to_2024-06-30.md` (yes)
- risk_reason_codes: `dashboards/risk_reason_code_summary_DE-LU_2024-06-01_to_2024-06-30.csv` (yes)
- risk_regime_distribution: `dashboards/risk_regime_distribution_DE-LU_2024-06-01_to_2024-06-30.csv` (yes)
- risk_signal_report: `reports/risk_signal_quality_2024-06-01_to_2024-06-30.md` (yes)
- risk_signals: `data/processed/risk_signals_DE-LU_2024-06-01_to_2024-06-30.csv` (yes)
- run_summary: `reports/pipeline_run_summary_2024-06-01_to_2024-06-30.md` (no)
- run_summary_json: `reports/pipeline_run_summary_2024-06-01_to_2024-06-30.json` (no)
- staging: `data/staging/clean_hourly_DE-LU_2024-06-01_to_2024-06-30.csv` (yes)
- staging_hard_json: `reports/staging_hard_checks_2024-06-01_to_2024-06-30.json` (yes)
- staging_hard_report: `reports/staging_hard_checks_2024-06-01_to_2024-06-30.md` (yes)
- top_risk_hours: `dashboards/top_risk_hours_DE-LU_2024-06-01_to_2024-06-30.csv` (yes)

This run reproduces the implemented public-data pipeline. It does not claim trading profitability, execution capability, or P&L.
