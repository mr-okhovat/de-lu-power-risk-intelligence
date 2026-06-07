# Price-risk panel quality

Version: 8C.1
Status: PASS
Output: `data/processed/price_risk_panel_DE-LU_2024-07-01_to_2024-07-31.csv`

## Join checks

- Panel rows: 744
- Feature rows: 744
- Price rows: 744
- Risk rows: 744
- Missing price rows: 0
- Missing risk rows: 0
- Duplicate timestamps: 0

## First read

- Min price EUR/MWh: -73.96
- Max price EUR/MWh: 257.35
- Mean price EUR/MWh: 67.69702956989246
- Max risk score: 85.0
- High-risk rows: 19

## Notes

- Panel join passed. Features, prices and risk signals align hourly.

This file is the first combined panel for price-aware analysis. It is not yet an event study or a backtest.
