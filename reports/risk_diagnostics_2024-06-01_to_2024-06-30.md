# Risk Signal Diagnostic Report — Phase 4B

- Risk signal input: `data/processed/risk_signals_DE-LU_2024-06-01_to_2024-06-30.csv`
- Regime distribution output: `dashboards/risk_regime_distribution_DE-LU_2024-06-01_to_2024-06-30.csv`
- Reason-code summary output: `dashboards/risk_reason_code_summary_DE-LU_2024-06-01_to_2024-06-30.csv`
- Top-risk-hours output: `dashboards/top_risk_hours_DE-LU_2024-06-01_to_2024-06-30.csv`
- Status: `PASS`
- Row count: `720`
- Diagnostic schema version: `4B.1`

## Score Summary

- Min risk score: `0.0`
- Max risk score: `85.0`
- Mean risk score: `8.23611111111111`
- Median risk score: `0.0`

## Coverage Summary

- Unique regimes: `['EXTREME', 'NORMAL', 'STRESSED', 'WATCH']`
- Unique reason codes: `['HIGH_LOAD_RAMP', 'HIGH_RENEWABLE_GENERATION_RAMP', 'HIGH_RESIDUAL_LOAD', 'HIGH_RESIDUAL_LOAD_RAMP', 'LOW_RENEWABLE_SHARE', 'NO_RULE_TRIGGERED']`
- NO_RULE_TRIGGERED count: `520`
- STRESSED/EXTREME count: `7`
- EXTREME count: `1`
- Duplicate timestamps: `0`

## Required Columns Missing

- None

## Notes

- Risk diagnostics passed Phase 4B checks.

## Interpretation

This diagnostic layer checks risk-signal distribution and reason-code coverage. It does not evaluate predictive skill, market profitability, or backtest performance.

A calm short sample can legitimately produce mostly NORMAL or NO_RULE_TRIGGERED rows. Longer windows are required before judging usefulness.
