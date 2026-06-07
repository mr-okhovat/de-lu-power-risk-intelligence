# Pipeline run summary

Pipeline: DE-LU Power Risk Intelligence — may_2024
Run: may_2024
Status: PASS
Window: 2024-05-01 to 2024-05-31
Market: DE-LU
SMARD region: DE

## Steps

| step | status | seconds |
|---|---:|---:|
| tests_start | PASS | 1.27 |
| smard_filter_discovery | PASS | 0.337 |
| smard_ingestion | PASS | 1.232 |
| build_staging | PASS | 0.785 |
| staging_hard_checks | PASS | 0.38 |
| build_features | PASS | 0.558 |
| build_dashboard_exports | PASS | 0.539 |
| build_risk_signals | PASS | 1.076 |
| build_risk_diagnostics | PASS | 0.509 |
| build_reviewer_pack | PASS | 0.476 |
| tests_end | PASS | 1.27 |

## Outputs

- features: `data/processed/hourly_features_DE-LU_2024-05-01_to_2024-05-31.csv` (yes)
- market_export: `dashboards/market_overview_DE-LU_2024-05-01_to_2024-05-31.csv` (yes)
- reviewer_pack: `reports/reviewer_pack_2024-05-01_to_2024-05-31.md` (yes)
- reviewer_pack_json: `reports/reviewer_pack_2024-05-01_to_2024-05-31.json` (yes)
- risk_diagnostics_json: `reports/risk_diagnostics_2024-05-01_to_2024-05-31.json` (yes)
- risk_diagnostics_report: `reports/risk_diagnostics_2024-05-01_to_2024-05-31.md` (yes)
- risk_reason_codes: `dashboards/risk_reason_code_summary_DE-LU_2024-05-01_to_2024-05-31.csv` (yes)
- risk_regime_distribution: `dashboards/risk_regime_distribution_DE-LU_2024-05-01_to_2024-05-31.csv` (yes)
- risk_signal_report: `reports/risk_signal_quality_2024-05-01_to_2024-05-31.md` (yes)
- risk_signals: `data/processed/risk_signals_DE-LU_2024-05-01_to_2024-05-31.csv` (yes)
- run_summary: `reports/pipeline_run_summary_2024-05-01_to_2024-05-31.md` (yes)
- run_summary_json: `reports/pipeline_run_summary_2024-05-01_to_2024-05-31.json` (yes)
- staging: `data/staging/clean_hourly_DE-LU_2024-05-01_to_2024-05-31.csv` (yes)
- staging_hard_json: `reports/staging_hard_checks_2024-05-01_to_2024-05-31.json` (yes)
- staging_hard_report: `reports/staging_hard_checks_2024-05-01_to_2024-05-31.md` (yes)
- top_risk_hours: `dashboards/top_risk_hours_DE-LU_2024-05-01_to_2024-05-31.csv` (yes)

This run reproduces the implemented public-data pipeline. It does not claim trading profitability, execution capability, or P&L.
