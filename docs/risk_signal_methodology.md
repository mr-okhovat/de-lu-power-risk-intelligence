# Risk Signal Methodology

## Purpose

This document defines the Phase 4A rule-based risk signal layer.

## Scope

Phase 4A creates explainable market stress signals from the Phase 3A feature table.

It does not create:

- trading strategy
- P&L claim
- price forecast
- backtest
- execution logic
- intraday trading recommendation

## Current Inputs

- residual_load_official_mw
- renewable_share
- load_ramp_mw
- residual_load_ramp_mw
- renewable_generation_ramp_mw

## No-Lookahead Rule

Percentile ranks are calculated using past observations only.

For each timestamp t, the percentile rank uses observations before t.

Early rows with insufficient history receive no percentile-triggered stress reason.

## Rules

| Rule | Condition | Score |
|---|---:|---:|
| HIGH_RESIDUAL_LOAD | residual_load_percentile >= 0.90 | +30 |
| LOW_RENEWABLE_SHARE | renewable_share_percentile <= 0.10 | +25 |
| HIGH_RESIDUAL_LOAD_RAMP | abs_residual_load_ramp_percentile >= 0.90 | +20 |
| HIGH_LOAD_RAMP | abs_load_ramp_percentile >= 0.90 | +15 |
| HIGH_RENEWABLE_GENERATION_RAMP | abs_renewable_generation_ramp_percentile >= 0.90 | +10 |

Score is capped at 100.

## Regime Mapping

| Score | Regime |
|---:|---|
| 0-29 | NORMAL |
| 30-59 | WATCH |
| 60-84 | STRESSED |
| 85-100 | EXTREME |

## Reason Codes

Every row must have reason codes.

If no stress rule is triggered:

```text
NO_RULE_TRIGGERED
```

## Professional Boundary

This layer is a market stress proxy.

It should be reviewed by domain experts before being treated as a desk-relevant risk signal.
