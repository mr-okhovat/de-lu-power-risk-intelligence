# Dataset adapter run

Adapter: `signal_price_evaluation_identity`
Adapter version: `12B.1`
Status: `PASS`
Input: `data/processed/signal_price_evaluation_DE-LU_2024-07-01_to_2024-07-31.csv`
Output: `data/adapted/signal_price_evaluation_DE-LU_2024-07-01_to_2024-07-31_registry_adapted.csv`
Rows: `744`

## Output columns

- `timestamp_utc`
- `price_eur_per_mwh`
- `risk_score`
- `signal_positive`
- `event_positive`
- `confusion_bucket`
- `price_event_labels`
- `regime_label`
- `reason_codes`

## Checks

- Missing source columns: `[]`
- Conversion errors: `{}`

## Notes

- Dataset adapted successfully.
