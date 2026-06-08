# Reviewer quick path

This project is a reproducible DE-LU power-market risk-intelligence prototype built on public market data.

It is not presented as a live trading system. The purpose is to show a clean analytics workflow: ingest public data, validate it, build market features, generate rule-based risk signals, evaluate price-event behaviour, compare market/month runs, and expose the outputs through reports and a Streamlit dashboard.

## Review in 5 minutes

1. Start with README.md for the project scope and run instructions.
2. Open reports/reviewer_ready_v2.md for the main reviewer summary.
3. Open reports/market_month_run_catalog.md to see the available monthly DE-LU runs.
4. Open reports/active_run_selection.md to see the currently selected READY runs used by downstream review layers.
5. Open the dashboard with: streamlit run app/streamlit_app.py

Then check these tabs:

- Overview
- Lead time
- Run catalog
- Active selection
- Project health

## Current active review set

The active selection uses four READY DE-LU monthly runs:

- May 2024
- June 2024
- July 2024
- August 2024

These runs are selected from the market/month run catalog and rebuilt through the project checkpoint.

## What to look for

A reviewer should mainly check:

- whether the data pipeline is reproducible,
- whether the signal logic is transparent,
- whether the price-event evaluation is honest about its limits,
- whether the dashboard and reports agree,
- whether the project is useful as a portfolio-grade market analytics prototype.

## Current maturity

The project is suitable as a portfolio and interview discussion artifact for energy market analytics, power-market risk, and trading analytics support roles.

It should not be described as production trading infrastructure or as a proven alpha model.
