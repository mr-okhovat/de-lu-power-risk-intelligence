# No-Lookahead Policy

## Core Rule

A signal at time t may only use information available at or before time t.

## Forbidden

- Full-sample historical percentiles used for past signals.
- Centered rolling windows.
- Future prices used to classify past signals.
- Thresholds optimized on the same future events used for evaluation.
- Future-filled missing values used in signal generation.
- Actual data used where only forecast data would have been available, unless clearly marked as descriptive historical analysis.

## Allowed

- Expanding-window calculations using data up to time t.
- Rolling-window calculations using past values only.
- Same-hour historical percentiles using previous days only.
- Separate calibration and evaluation periods.

## Acceptance Requirement

Each feature/backtest module must explain what data it uses, when the data would have been available, and whether the calculation is descriptive or signal-feasible.
