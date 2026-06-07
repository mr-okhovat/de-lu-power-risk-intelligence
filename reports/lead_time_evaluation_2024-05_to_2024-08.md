# Lead-time evaluation

Version: 11A.1

## Purpose

This checks whether the current fundamentals signal has any forward-looking relationship with price events.

Same-hour alignment was already tested. This report adds exact future-hour checks and forward-window checks.

## Output tables

- Monthly table: `dashboards/lead_time_monthly_DE-LU_2024-05_to_2024-08.csv`
- Aggregate table: `dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv`

## Aggregate lead-time summary

| mode | horizon | target | signals | target events | precision | recall | lift |
|---|---:|---|---:|---:|---:|---:|---:|
| exact_hour | 0 | event_at_t_plus_0 | 41 | 773 | 0.4634146341463415 | 0.02457956015523933 | 1.7697283311772316 |
| exact_hour | 1 | event_at_t_plus_1 | 41 | 773 | 0.6097560975609756 | 0.03234152652005175 | 2.3254346385637206 |
| exact_hour | 2 | event_at_t_plus_2 | 41 | 773 | 0.5609756097560976 | 0.029754204398447608 | 2.1364970182690186 |
| exact_hour | 3 | event_at_t_plus_3 | 41 | 773 | 0.4146341463414634 | 0.02199223803363519 | 1.577004385826523 |
| exact_hour | 6 | event_at_t_plus_6 | 41 | 773 | 0.0 | 0.0 | 0.0 |
| future_window | 1 | any_event_next_1h | 41 | 773 | 0.6097560975609756 | 0.03234152652005175 | 2.3254346385637206 |
| future_window | 3 | any_event_next_3h | 41 | 1231 | 0.6341463414634146 | 0.021121039805036556 | 1.5145330982148164 |
| future_window | 6 | any_event_next_6h | 41 | 1720 | 0.6585365853658537 | 0.015697674418604653 | 1.1210436755530346 |
| future_window | 12 | any_event_next_12h | 41 | 2474 | 0.8292682926829268 | 0.0137429264349232 | 0.9734014235857799 |

## Readout

The signal keeps some forward-looking event concentration in the next 3 hours, but this still needs longer-window validation.

## Caveat

This is still not a trading backtest. It does not include forecast revisions, execution timing, liquidity, imbalance settlement or P&L.
