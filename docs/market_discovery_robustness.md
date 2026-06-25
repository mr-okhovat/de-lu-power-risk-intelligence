# Market Discovery Robustness Gate

## Purpose

Test whether the initial ex-post association between realised DE-LU
fundamentals and same-delivery-hour day-ahead price stress survives basic
threshold, calendar-support and mechanism checks.

## Boundaries

This is not a causal model, forecast, trading strategy or claim about
information available before the day-ahead auction.

## Required checks

1. Price-event threshold sensitivity: monthly p85, p90 and p95.
2. Fundamental-state threshold sensitivity: p85/p15, p90/p10 and p95/p05.
3. Calendar support: year-month × delivery hour, with and without a
   weekend/weekday split.
4. Yearly and monthly directional stability.
5. State-combination decomposition.
6. Incremental residual-ramp check conditional on high residual load and
   low renewable share.

## Decision rule

A positive initial result becomes a candidate for deeper mechanism work only
if its direction is stable across reasonable thresholds and calendar controls,
is not concentrated in a small number of periods, and is not solely an
artefact of one component definition.
