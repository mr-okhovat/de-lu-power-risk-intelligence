# Historical run notes

The first real extension is June 2024.

This is still not a backtest. The goal is to check whether the existing pipeline behaves cleanly on a longer window.

Current historical run:

- window: 2024-06-01 to 2024-06-30
- resolution: hourly
- market label: DE-LU
- SMARD region: DE
- risk minimum history: 168 hours

Why 168 hours?

One week of hourly observations gives the percentile logic enough past context before it starts treating stress signals seriously.

What to inspect after the run:

- reports/pipeline_run_summary_2024-06-01_to_2024-06-30.md
- reports/reviewer_pack_2024-06-01_to_2024-06-30.md
- reports/risk_diagnostics_2024-06-01_to_2024-06-30.md
- dashboards/top_risk_hours_DE-LU_2024-06-01_to_2024-06-30.csv
- dashboards/risk_regime_distribution_DE-LU_2024-06-01_to_2024-06-30.csv
