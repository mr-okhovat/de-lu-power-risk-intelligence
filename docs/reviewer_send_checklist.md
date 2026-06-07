# Reviewer send checklist

Use this before sending the repository to a technical reviewer.

## Current checkpoint

Reviewer-ready v1 with visual README.

The project currently includes:

- SMARD/Bundesnetzagentur data ingestion
- hourly market feature engineering
- fundamentals-based risk signal
- day-ahead price table
- ex-post price-event labels
- signal-vs-price-event evaluation
- cross-month price-risk comparison
- visual reviewer pack

## Files to check before sending

Open these files in GitHub and confirm they render correctly:

- README.md
- reports/reviewer_ready_v1.md
- reports/visual_reviewer_pack.md
- reports/cross_month_price_risk_2024-05_to_2024-08.md
- reports/figures/monthly_event_lift.png
- reports/figures/precision_recall.png
- reports/figures/signal_vs_event_rate.png
- reports/figures/confusion_summary.png
- reports/figures/june_price_risk_timeline.png

## Claims allowed

You can say:

- this is a public-data analytics prototype
- it uses SMARD/Bundesnetzagentur data
- it builds an hourly fundamentals risk signal
- it adds day-ahead price-event labels
- it compares signal-positive hours with ex-post price events
- across May to August 2024, signal-positive hours show higher price-event concentration than the monthly base rate
- the signal is conservative and recall is low

## Claims not allowed

Do not say:

- trading system
- profitable signal
- forecast model
- price prediction
- P&L backtest
- execution model
- production-ready tool
- Uniper-level internal system
- desk-grade analytics

## What to ask the reviewer

Ask for feedback on:

1. Whether the fundamentals framing makes sense for DE-LU power-market stress monitoring.
2. Whether the reason codes are useful or too coarse.
3. Whether the ex-post price-event definition is acceptable for first diagnostics.
4. Whether the next layer should be forecast error, imbalance/balancing, weather, cross-border flows, intraday prices, or lead-time analysis.
5. What would make the project closer to a useful trading analytics workflow.

## Sending rule

Send it as a private technical feedback request, not as a public success announcement.

Do not send it as LinkedIn content yet. LinkedIn comes after feedback or after a small dashboard layer.
