# Signal vs price-event evaluation

Version: 8E.1
Status: PASS
Evaluation table: `data/processed/signal_price_evaluation_DE-LU_2024-07-01_to_2024-07-31.csv`
Confusion table: `dashboards/signal_price_confusion_DE-LU_2024-07-01_to_2024-07-31.csv`
Event summary: `dashboards/signal_price_event_summary_DE-LU_2024-07-01_to_2024-07-31.csv`

## Setup

- Rows: 744
- Signal threshold: 60.0
- Price-event rows: 197
- Signal-positive rows: 19

## Metrics

- True positives: 8
- False positives: 11
- True negatives: 536
- False negatives: 189
- Precision: 0.42105263157894735
- Recall: 0.04060913705583756
- F1 score: 0.07407407407407407
- Signal rate: 0.025537634408602152
- Event rate: 0.2647849462365591

## Data checks

- Duplicate timestamps: 0
- Missing price rows: 0
- Missing risk rows: 0

## Readout

There is some alignment between high-risk fundamentals and price events. This needs a longer-window check before interpretation.

## Notes

- More high-risk hours occurred without price events than with price events. This may be acceptable for a fundamentals stress proxy, but it needs review.

This is an ex-post alignment check, not a trading backtest. No P&L or predictability claim is made here.
