# Signal vs price-event evaluation

Version: 8E.1
Status: PASS
Evaluation table: `data/processed/signal_price_evaluation_DE-LU_2024-08-01_to_2024-08-31.csv`
Confusion table: `dashboards/signal_price_confusion_DE-LU_2024-08-01_to_2024-08-31.csv`
Event summary: `dashboards/signal_price_event_summary_DE-LU_2024-08-01_to_2024-08-31.csv`

## Setup

- Rows: 744
- Signal threshold: 60.0
- Price-event rows: 192
- Signal-positive rows: 8

## Metrics

- True positives: 3
- False positives: 5
- True negatives: 547
- False negatives: 189
- Precision: 0.375
- Recall: 0.015625
- F1 score: 0.03
- Signal rate: 0.010752688172043012
- Event rate: 0.25806451612903225

## Data checks

- Duplicate timestamps: 0
- Missing price rows: 0
- Missing risk rows: 0

## Readout

There is some alignment between high-risk fundamentals and price events. This needs a longer-window check before interpretation.

## Notes

- More high-risk hours occurred without price events than with price events. This may be acceptable for a fundamentals stress proxy, but it needs review.

This is an ex-post alignment check, not a trading backtest. No P&L or predictability claim is made here.
