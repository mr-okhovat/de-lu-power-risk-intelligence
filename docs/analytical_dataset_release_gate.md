# Analytical Dataset Release Gate

## Purpose

This control determines whether a feature dataset is eligible to feed downstream
risk signals, dashboards, and reviewer-facing reports.

It is intentionally separate from staging hard checks:

- staging hard checks validate structural readiness before feature engineering;
- this release gate validates analytical readiness after feature engineering.

## Release policy

A dataset is `READY` only when all of the following hold:

1. The expected feature-schema columns exist.
2. UTC timestamps are valid, unique, and hourly continuous.
3. Core analytical columns contain no missing values.
4. Ramp values are complete after the first observation.
5. Residual-gap values remain within the configured tolerance.
6. Renewable, wind, and solar shares stay within the inclusive `[0, 1]` range.
7. The dataset has one consistent market label and SMARD region.
8. The feature metadata matches the file, row count, quality status, and schema version.
9. `missing_any_flag` is never true.

A `BLOCKED` dataset must not feed downstream risk signals, dashboards, or reports.

## Scope

This is a public-data reference implementation based on DE-LU hourly feature data.
It demonstrates data-release control and auditability; it does not claim predictive
performance, trading profitability, or production deployment.
