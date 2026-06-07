# Signal vs price-event evaluation

Version: 8E.1
Status: PASS
Evaluation table: `data/processed/signal_price_evaluation_DE-LU_2024-06-01_to_2024-06-30.csv`
Confusion table: `dashboards/signal_price_confusion_DE-LU_2024-06-01_to_2024-06-30.csv`
Event summary: `dashboards/signal_price_event_summary_DE-LU_2024-06-01_to_2024-06-30.csv`

## Setup

- Rows: 720
- Signal threshold: 60.0
- Price-event rows: 181
- Signal-positive rows: 7

## Metrics

- True positives: 4
- False positives: 3
- True negatives: 536
- False negatives: 177
- Precision: 0.5714285714285714
- Recall: 0.022099447513812154
- F1 score: 0.0425531914893617
- Signal rate: 0.009722222222222222
- Event rate: 0.2513888888888889

## Data checks

- Duplicate timestamps: 0
- Missing price rows: 0
- Missing risk rows: 0

## Readout

There is some alignment between high-risk fundamentals and price events. This needs a longer-window check before interpretation.

## Notes

- Signal-price evaluation completed without blocking data quality issues.

This is an ex-post alignment check, not a trading backtest. No P&L or predictability claim is made here.
