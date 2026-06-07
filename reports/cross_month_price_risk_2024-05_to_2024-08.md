# Cross-month price-risk evaluation

Version: 8H.1
Table: `dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv`

## Monthly summary

| month | rows | signals | events | TP | FP | FN | precision | recall | lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| May 2024 | 744 | 7 | 203 | 4 | 3 | 199 | 0.5714285714285714 | 0.019704433497536946 | 2.0942997888810697 |
| June 2024 | 720 | 7 | 181 | 4 | 3 | 177 | 0.5714285714285714 | 0.022099447513812154 | 2.273086029992107 |
| July 2024 | 744 | 19 | 197 | 8 | 11 | 189 | 0.42105263157894735 | 0.04060913705583756 | 1.5901683141864815 |
| August 2024 | 744 | 8 | 192 | 3 | 5 | 189 | 0.375 | 0.015625 | 1.453125 |

## Readout

Signal-positive hours beat the base event rate in every month, but the strength varies.

## Decision

Do not tune thresholds yet.

The current signal is conservative and repeatedly shows event lift above the base price-event rate. The next useful step is a reviewer-ready package with clear caveats, then a longer data window or forecast-error layer.

This is still not a trading backtest. It does not claim forecast skill, tradability or P&L.
