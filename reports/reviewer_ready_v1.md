# Reviewer-ready v1

Version: 8I.1

## What this is

A reproducible public-data analytics prototype for DE-LU power-market risk intelligence.

It ingests SMARD data, builds hourly market features, creates an explainable fundamentals risk signal, adds day-ahead price data, labels ex-post price events, and compares signal-positive hours with price-event behavior across four months.

It is not a trading system, not a price forecast, and not a P&L backtest.

## Current evidence

- Months reviewed: 4
- Rows reviewed: 2952
- Signal-positive hours: 41
- Price-event hours: 773
- Aggregate precision: 0.463
- Aggregate recall: 0.025
- Aggregate event lift: 1.770
- Monthly lift range: 1.453 to 2.273
- Metrics table: `dashboards/reviewer_ready_v1_metrics.csv`

## Monthly price-risk result

| month | signals | events | TP | FP | FN | precision | recall | lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| May 2024 | 7 | 203 | 4 | 3 | 199 | 0.571 | 0.020 | 2.094 |
| June 2024 | 7 | 181 | 4 | 3 | 177 | 0.571 | 0.022 | 2.273 |
| July 2024 | 19 | 197 | 8 | 11 | 189 | 0.421 | 0.041 | 1.590 |
| August 2024 | 8 | 192 | 3 | 5 | 189 | 0.375 | 0.016 | 1.453 |

## Readout

Signal-positive hours show a higher price-event concentration than the monthly base rate in every reviewed month.

The current signal is conservative. That is visible in the low number of signal-positive hours and low recall. The useful point is that when the signal does fire, it is not random relative to price-event behavior.

## What to ask a reviewer

1. Does the fundamentals framing make sense for DE-LU power-market stress monitoring?
2. Are the current risk reasons useful, or are they too coarse for trading analytics?
3. Is the price-event definition acceptable as a first ex-post diagnostic?
4. Which layer should come next: forecast error, balancing/imbalance, weather, cross-border flows, or intraday prices?

## Main files to inspect

- `reports/cross_month_price_risk_2024-05_to_2024-08.md`
- `dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv`
- `reports/price_risk_behavior_2024-06-01_to_2024-06-30.md`
- `src/prices/cross_month_price_risk.py`
- `src/signals/risk_engine.py`
- `src/features/market_features.py`

## Caveats

- Four months are not enough for a robust statistical claim.
- Price events are ex-post labels, not signal inputs.
- The current evaluation checks same-hour alignment, not lead time.
- No P&L, execution, tradability or forecast-skill claim is made.
- The next serious layer should add forecast errors or balancing/imbalance context.
