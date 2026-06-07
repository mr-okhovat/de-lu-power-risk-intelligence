# Data Contracts

## Layers

1. Raw
2. Staging
3. Processed

## Raw Layer

Location: data/raw/{source}/

Raw data must remain immutable.

Required metadata:

| Field | Meaning |
|---|---|
| source | Data provider |
| source_url | Endpoint or page |
| retrieved_at_utc | Retrieval timestamp |
| market | Market/region |
| unit | Original unit |
| resolution | Time resolution |
| original_timestamp_field | Source timestamp |
| normalized_timestamp_utc | UTC timestamp |
| timezone_context | Europe/Berlin or source context |
| transformation_history | Applied transformations |
| license_note | Access/license note |
| file_hash | Optional audit hash |

## Staging Layer

Expected columns:

| Column | Unit |
|---|---|
| timestamp_utc | UTC datetime |
| timestamp_local | Europe/Berlin datetime |
| market | text |
| load_mw | MW |
| wind_mw | MW |
| solar_mw | MW |
| renewable_generation_mw | MW |
| residual_load_mw | MW |
| price_eur_mwh | EUR/MWh |
| missing_flag | boolean |
| duplicate_flag | boolean |
| dst_flag | boolean |
| quality_note | text |

## Processed Layer

Expected signal columns:

| Column | Meaning |
|---|---|
| timestamp_utc | Signal timestamp |
| market | Market |
| risk_score | 0-100 |
| regime_label | NORMAL/WATCH/STRESSED/EXTREME |
| reason_codes | Triggered explanations |
| model_version | Rule version |
| created_at_utc | Signal creation timestamp |
