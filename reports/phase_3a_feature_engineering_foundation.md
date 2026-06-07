# Phase 3A — Feature Engineering Foundation

## Scope

This phase creates the first feature table from the validated hourly staging table.

## Created/modified files

- src/features/market_features.py
- tests/test_market_features.py
- run_pipeline.py

## Features

- wind_total_mw
- renewable_generation_mw
- residual_load_calculated_mw
- residual_gap_mw
- residual_gap_abs_mw
- renewable_share
- wind_share
- solar_share
- load_ramp_mw
- residual_load_ramp_mw
- renewable_generation_ramp_mw
- local_date
- local_hour
- local_weekday
- is_weekend

## Acceptance

- Tests pass.
- Feature CSV is created.
- Feature metadata JSON is created.
- Feature quality report is created.
- Residual gap remains within tolerance.
- No risk scores or backtests are created in this phase.
