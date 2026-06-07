# Cross-month risk behavior

Version: 7F.1
Table: `dashboards/cross_month_risk_behavior_DE-LU_2024-05_to_2024-08.csv`

## Monthly summary

| month | rows | mean | median | max | high-risk rows | high-risk share | extreme | top reason |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| May 2024 | 744 | 7.124 | 0.0 | 90.0 | 7 | 0.0094 | 1 | LOW_RENEWABLE_SHARE |
| June 2024 | 720 | 8.236 | 0.0 | 85.0 | 7 | 0.0097 | 1 | HIGH_RENEWABLE_GENERATION_RAMP |
| July 2024 | 744 | 10.78 | 0.0 | 85.0 | 19 | 0.0255 | 2 | LOW_RENEWABLE_SHARE |
| August 2024 | 744 | 7.829 | 0.0 | 70.0 | 8 | 0.0108 | 0 | HIGH_RESIDUAL_LOAD_RAMP |

## Readout

Signal frequency looks controlled across the current months. No threshold change is justified yet.

## Decision

Keep the current rules unchanged.

The next useful step is not threshold tuning. The next useful step is adding a price layer, because without prices we still cannot say whether these stress hours mattered economically.
