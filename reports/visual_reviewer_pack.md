# Visual reviewer pack

Version: 9A.1

## Current read

The current fundamentals signal is conservative. It fires rarely, but signal-positive hours show higher ex-post price-event concentration than the monthly base rate across the reviewed months.

This is still not a trading model, price forecast, or P&L backtest.

## Key metrics

- Months: 4
- Rows: 2952
- Signal-positive hours: 41
- Price-event hours: 773
- Aggregate precision: 0.463
- Aggregate recall: 0.025
- Aggregate event lift: 1.770
- Monthly lift range: 1.453 to 2.273
- Summary CSV: `dashboards/visual_reviewer_summary.csv`

## Figures

![Monthly event lift](reports/figures/monthly_event_lift.png)

![Precision and recall](reports/figures/precision_recall.png)

![Base event rate vs signal-positive event rate](reports/figures/signal_vs_event_rate.png)

![Confusion summary](reports/figures/confusion_summary.png)

![June price-risk timeline](reports/figures/june_price_risk_timeline.png)

## Caveat

The figures show ex-post alignment, not forecast skill. The next serious step should test lead time and add forecast-error or balancing/imbalance context.
