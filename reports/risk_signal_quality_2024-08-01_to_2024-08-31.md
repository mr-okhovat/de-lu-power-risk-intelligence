# Risk Signal Quality Report — Phase 4A

- Feature input: `data/processed/hourly_features_DE-LU_2024-08-01_to_2024-08-31.csv`
- Risk signal output: `data/processed/risk_signals_DE-LU_2024-08-01_to_2024-08-31.csv`
- Status: `PASS`
- Row count: `744`
- Risk schema version: `4A.1`
- Minimum history for percentile logic: `168`
- Minimum risk score: `0.0`
- Maximum risk score: `70.0`
- EXTREME rows with fewer than two reason codes: `0`

## Regime Counts

- `NORMAL`: `645`
- `STRESSED`: `8`
- `WATCH`: `91`

## Required Columns Missing

- None

## Missing Values in Critical Columns

- `timestamp_utc`: `0`
- `market_label`: `0`
- `risk_score`: `0`
- `regime_label`: `0`
- `reason_codes`: `0`

## Notes

- Risk signal table passed Phase 4A checks.

## Methodological Boundary

This is a rule-based market stress signal layer, not a trading strategy.

No price data, P&L, execution logic, or backtest is included in Phase 4A.

Percentile ranks are calculated using past observations only. Early rows with insufficient history receive no percentile-triggered stress reasons.
