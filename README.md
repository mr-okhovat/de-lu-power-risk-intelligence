# DE-LU Power Risk Intelligence

A reproducible, explainable, audit-ready analytics pipeline for the German/Luxembourg electricity market.

## Mission

Build a public-data-based intelligence system that:

1. Ingests official/public DE-LU power market data.
2. Stores immutable raw data with metadata.
3. Cleans and validates time-series data.
4. Engineers explainable market stress features.
5. Generates transparent rule-based risk signals.
6. Backtests those signals against historical stress events.
7. Produces dashboard-ready outputs and professional reports.
8. Documents assumptions, limitations, and quality checks.

## Core Analytical Idea

German/Luxembourg power market stress can be monitored through load, residual load, renewable generation, renewable share, ramps, price spikes, negative prices, volatility, forecast errors, cross-border stress, balancing indicators, weather drivers, and gas-system context.

Version 1 is rule-based and explainable. No black-box machine learning is used in v1.

## Core Sources

- SMARD / Bundesnetzagentur
- ENTSO-E Transparency Platform
- Regelleistung.net / German TSOs
- DWD Open Data / Bright Sky
- GIE AGSI/ALSI as optional future context
- EPEX SPOT as market reference only unless licensed data is available

## One-Command Target

python run_pipeline.py --start YYYY-MM-DD --end YYYY-MM-DD --market DE-LU

## Current Phase

Phase 0 — Project Control and Design Lock.

No market data is downloaded in Phase 0.
