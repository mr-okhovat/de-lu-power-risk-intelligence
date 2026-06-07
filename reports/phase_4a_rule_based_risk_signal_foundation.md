# Phase 4A — Rule-Based Risk Signal Foundation

## Scope

This phase creates the first explainable rule-based risk signal table.

## Created/modified files

- src/signals/risk_engine.py
- tests/test_risk_engine.py
- run_pipeline.py
- docs/risk_signal_methodology.md

## Acceptance

- Tests pass.
- Risk signal CSV is created.
- Risk signal metadata JSON is created.
- Risk quality report is created.
- Risk scores remain between 0 and 100.
- EXTREME rows, if any, have at least two reason codes.
- No backtest or P&L claim is added in this phase.
