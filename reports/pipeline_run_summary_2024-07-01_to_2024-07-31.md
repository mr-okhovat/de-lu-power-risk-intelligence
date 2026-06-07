# Pipeline run summary

Pipeline: DE-LU Power Risk Intelligence — july_2024
Run: july_2024
Status: PASS
Window: 2024-07-01 to 2024-07-31
Market: DE-LU
SMARD region: DE

## Steps

| step | status | seconds |
|---|---:|---:|
| tests_start | PASS | 1.184 |
| smard_filter_discovery | PASS | 0.363 |
| smard_ingestion | PASS | 1.405 |
| build_staging | PASS | 0.767 |
| staging_hard_checks | PASS | 0.395 |
| build_features | PASS | 0.563 |
| build_dashboard_exports | PASS | 0.577 |
| build_risk_signals | PASS | 0.968 |
| build_risk_diagnostics | PASS | 0.545 |
| build_reviewer_pack | PASS | 0.432 |
| tests_end | PASS | 1.205 |

## Outputs

- features: `data/processed/hourly_features_DE-LU_2024-07-01_to_2024-07-31.csv` (yes)
- market_export: `dashboards/market_overview_DE-LU_2024-07-01_to_2024-07-31.csv` (yes)
- reviewer_pack: `reports/reviewer_pack_2024-07-01_to_2024-07-31.md` (yes)
- reviewer_pack_json: `reports/reviewer_pack_2024-07-01_to_2024-07-31.json` (yes)
- risk_diagnostics_json: `reports/risk_diagnostics_2024-07-01_to_2024-07-31.json` (yes)
- risk_diagnostics_report: `reports/risk_diagnostics_2024-07-01_to_2024-07-31.md` (yes)
- risk_reason_codes: `dashboards/risk_reason_code_summary_DE-LU_2024-07-01_to_2024-07-31.csv` (yes)
- risk_regime_distribution: `dashboards/risk_regime_distribution_DE-LU_2024-07-01_to_2024-07-31.csv` (yes)
- risk_signal_report: `reports/risk_signal_quality_2024-07-01_to_2024-07-31.md` (yes)
- risk_signals: `data/processed/risk_signals_DE-LU_2024-07-01_to_2024-07-31.csv` (yes)
- run_summary: `reports/pipeline_run_summary_2024-07-01_to_2024-07-31.md` (no)
- run_summary_json: `reports/pipeline_run_summary_2024-07-01_to_2024-07-31.json` (no)
- staging: `data/staging/clean_hourly_DE-LU_2024-07-01_to_2024-07-31.csv` (yes)
- staging_hard_json: `reports/staging_hard_checks_2024-07-01_to_2024-07-31.json` (yes)
- staging_hard_report: `reports/staging_hard_checks_2024-07-01_to_2024-07-31.md` (yes)
- top_risk_hours: `dashboards/top_risk_hours_DE-LU_2024-07-01_to_2024-07-31.csv` (yes)

This run reproduces the implemented public-data pipeline. It does not claim trading profitability, execution capability, or P&L.
