# Price-risk panel quality

Version: 8C.1
Status: PASS
Output: `data/processed/price_risk_panel_DE-LU_2024-06-01_to_2024-06-30.csv`

## Join checks

- Panel rows: 720
- Feature rows: 720
- Price rows: 720
- Risk rows: 720
- Missing price rows: 0
- Missing risk rows: 0
- Duplicate timestamps: 0

## First read

- Min price EUR/MWh: -80.01
- Max price EUR/MWh: 235.52
- Mean price EUR/MWh: 72.88772222222222
- Max risk score: 85.0
- High-risk rows: 7

## Notes

- Panel join passed. Features, prices and risk signals align hourly.

This file is the first combined panel for price-aware analysis. It is not yet an event study or a backtest.
