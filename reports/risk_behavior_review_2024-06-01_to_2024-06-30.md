# June 2024 risk behavior review

Version: 7B.1
Signal input: `data/processed/risk_signals_DE-LU_2024-06-01_to_2024-06-30.csv`

## Headline

- Rows: 720
- Mean risk score: 8.24
- Median risk score: 0.00
- Max risk score: 85.00
- High-risk rows, score >= 60: 7
- Extreme rows: 1

## Output files

- Regime distribution: `dashboards/risk_behavior_regime_DE-LU_2024-06-01_to_2024-06-30.csv`
- Reason-code summary: `dashboards/risk_behavior_reasons_DE-LU_2024-06-01_to_2024-06-30.csv`
- Hourly profile: `dashboards/risk_behavior_hourly_DE-LU_2024-06-01_to_2024-06-30.csv`
- Weekday profile: `dashboards/risk_behavior_weekday_DE-LU_2024-06-01_to_2024-06-30.csv`
- Top risk hours: `dashboards/risk_behavior_top_hours_DE-LU_2024-06-01_to_2024-06-30.csv`

## First read

High-risk frequency is not obviously excessive for a first diagnostic run.
The median score is zero. Stress detection is concentrated in selected hours, not spread everywhere.

## Boundary

This is a behavior review, not a performance test. It does not prove predictive value or trading usefulness.
