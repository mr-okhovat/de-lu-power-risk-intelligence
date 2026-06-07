# Reviewer-ready v2

Version: 11D.1

## What this is

A reproducible public-data analytics prototype for DE-LU power-market risk intelligence.

The project ingests SMARD/Bundesnetzagentur data, builds hourly market features, creates an explainable fundamentals risk signal, adds day-ahead price-event labels, checks cross-month signal-vs-price-event behavior, and now adds lead-time diagnostics.

It is not a trading system, not a price forecast, and not a P&L backtest.

## Current evidence

- Months reviewed: 4
- Rows reviewed: 2952
- Signal-positive hours: 41
- Price-event hours: 773
- Aggregate precision: 0.463
- Aggregate recall: 0.025
- Aggregate same-hour event lift: 1.770
- Monthly lift range: 1.453 to 2.273
- Metrics table: `dashboards/reviewer_ready_v2_metrics.csv`

## Monthly same-hour result

| month | signals | events | TP | FP | FN | precision | recall | lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| May 2024 | 7 | 203 | 4 | 3 | 199 | 0.571 | 0.020 | 2.094 |
| June 2024 | 7 | 181 | 4 | 3 | 177 | 0.571 | 0.022 | 2.273 |
| July 2024 | 19 | 197 | 8 | 11 | 189 | 0.421 | 0.041 | 1.590 |
| August 2024 | 8 | 192 | 3 | 5 | 189 | 0.375 | 0.016 | 1.453 |

## Lead-time readout

Lead-time check shows some forward-window event concentration, especially within the next 3 hours. This is still not forecast skill and needs longer-window validation.

| target | precision | recall | lift |
|---|---:|---:|---:|
| same hour | 0.463 | 0.025 | 1.770 |
| exact next 1h | 0.610 | 0.032 | 2.325 |
| any event next 3h | 0.634 | 0.021 | 1.515 |
| any event next 6h | 0.659 | 0.016 | 1.121 |

## What this means

The signal is conservative. It fires rarely and recall remains low. The useful point is that signal-positive hours are not random relative to ex-post price-event behavior.

Lead-time diagnostics clarify whether the signal is only a same-hour stress diagnostic or whether it also carries some forward-window concentration. This should guide the next development step.

## What to review

1. Does the fundamentals framing make sense for DE-LU market stress monitoring?
2. Are the current reason codes useful or too coarse?
3. Is the price-event labeling acceptable as a first ex-post diagnostic?
4. Is the lead-time behavior strong enough to justify early-warning development?
5. Should the next layer be forecast error, imbalance/balancing, weather, cross-border flows, or intraday prices?

## Caveats

- Four months are not enough for a robust statistical claim.
- Price events are ex-post labels and are not used as signal inputs.
- Lead-time checks are event alignment checks, not tradability tests.
- No P&L, execution, liquidity, forecast skill, or production-readiness claim is made.

## Main files

- `reports/lead_time_evaluation_2024-05_to_2024-08.md`
- `dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv`
- `reports/cross_month_price_risk_2024-05_to_2024-08.md`
- `reports/visual_reviewer_pack.md`
- `app/streamlit_app.py`
