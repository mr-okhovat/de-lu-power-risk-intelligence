# Market Discovery Gate

## Objective

Determine whether the existing DE-LU price stack can be extended into a clean,
reproducible 2020–2024 hourly research panel before testing market hypotheses.

## Current state

The historical DE-LU day-ahead price panel has now been built for
2020-01-01 to 2024-12-31.

- 43,848 hourly observations
- SMARD / Bundesnetzagentur filter `4169`
- DE-LU endpoint
- No missing expected hours
- No duplicate timestamps
- No missing prices

The panel is suitable for ex-post calendar-controlled discovery analysis.
It is not evidence of pre-auction information availability or tradability.

## Decision rule

Do not add new market features or publish market claims before:

1. the price source/filter and timestamp convention are confirmed;
2. a multi-year hourly price panel is built and quality-checked;
3. price availability, duplicates, missing hours and source metadata are
   captured in one historical build manifest.

## Next build

Reuse the existing price-table and quality stack to construct the historical
price panel. Then test whether fundamentals add information beyond hour,
weekday, month/season and regime controls.

## Stop condition

If multi-year price coverage cannot be built reproducibly from the selected
public source, stop the discovery track and retain the project as a
fundamentals/risk-intelligence portfolio prototype rather than forcing a
price-predictive claim.
