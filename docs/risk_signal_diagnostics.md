# Risk Signal Diagnostics

## Purpose

This document describes the Phase 4B risk diagnostic layer.

## Scope

Phase 4B checks:

- risk score distribution
- regime distribution
- reason-code coverage
- top risk hours
- duplicate timestamps
- diagnostic completeness

## Not in Scope

Phase 4B does not include:

- backtesting
- P&L analysis
- price forecasting
- execution logic
- trading strategy claims

## Important Interpretation

A short calm sample can produce mostly NORMAL or NO_RULE_TRIGGERED rows.

That is not a failure.

The purpose of Phase 4B is to ensure that the signal table is structurally diagnosable before backtesting or public presentation.
