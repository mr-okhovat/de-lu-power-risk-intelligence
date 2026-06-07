# SQL / Power BI Export Contract

## Purpose

This document defines the Phase 3B export contract for SQL and Power BI consumption.

## Current Export

Main dashboard export:

```text
dashboards/market_overview_DE-LU_2024-06-01_to_2024-06-03.csv
```

Feature dictionary:

```text
dashboards/feature_dictionary_DE-LU_2024-06-01_to_2024-06-03.csv
```

SQL schema contract:

```text
sql/schema_power_market_features.sql
```

## Design Rule

Power BI and SQL should consume dashboard-ready feature exports, not raw SMARD JSON.

## Current Scope

Phase 3B includes:

- market overview CSV
- feature dictionary CSV
- SQL schema contract
- export quality report

Phase 3B does not include:

- Power BI .pbix file
- risk scores
- trading signals
- backtests
- automated database load

## Primary Table

`power_market_features`

Primary key:

```text
timestamp_utc
```

Recommended indexes:

```text
market_label, timestamp_utc
local_date
```

## Power BI Notes

Recommended initial visuals later:

- total load vs residual load
- renewable generation vs load
- renewable share by local hour
- load ramp distribution
- residual load ramp distribution

These visuals are not built in Phase 3B.
