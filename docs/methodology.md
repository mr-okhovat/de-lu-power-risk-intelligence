# Methodology

## Purpose

This project builds an explainable DE-LU power market risk intelligence pipeline using public and official data only.

## Version 1

Version 1 is rule-based, explainable, reproducible, auditable, public-data-only, and avoids black-box machine learning.

## Pipeline

1. Ingest raw public market data.
2. Store immutable raw data.
3. Attach metadata.
4. Validate timestamps, units, duplicates, and missing values.
5. Build clean staging time series.
6. Engineer market features.
7. Generate rule-based risk scores.
8. Add reason codes.
9. Backtest signals.
10. Export dashboards and reports.
11. Run audit checks.

## Core Features

- load
- wind generation
- solar generation
- renewable generation
- residual load
- renewable share
- load ramp
- wind ramp
- solar ramp
- price
- price return
- rolling volatility
- price spike flag
- negative price flag
- historical percentiles

## Residual Load

residual_load = load - wind_generation - solar_generation

Official residual-load data can later be used for validation.

## Risk Regimes

- NORMAL
- WATCH
- STRESSED
- EXTREME

## Backtesting Metrics

- precision
- recall
- false positives
- false negatives
- lead time
- signal frequency
- event coverage
