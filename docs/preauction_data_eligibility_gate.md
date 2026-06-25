# Pre-Auction Data Eligibility Gate

## Auction reference time

For the current research design, the reference point is the coupled day-ahead
auction gate closure at D-1 12:00 CET/CEST.

A variable is not eligible for an ex-ante study merely because it is public.
It must have a timestamped publication or decision time before auction gate
closure for the relevant delivery day.

## Current eligibility matrix

| Variable family | Current research status | Eligibility decision |
|---|---|---|
| Realised load | Ex-post explanatory only | Exclude from pre-auction model |
| Realised wind / solar generation | Ex-post explanatory only | Exclude from pre-auction model |
| ENTSO-E standard D-1 wind / solar forecast published by 18:00 | Potentially too late for D-1 noon auction | Exclude unless an earlier archived vintage is found |
| Forecast residual load | No source/vintage selected yet | Required candidate; audit before use |
| Planned generation unavailability | May be published after plan approval | Conditional candidate; require event-level timestamps |
| Actual generation unavailability | Published after actual change | Exclude unless publication is demonstrably pre-auction |
| Cross-zonal capacity | Economic relevance established | Conditional candidate; require archived D-1 snapshot and publication timing |
| Imports / net position | Realised values are ex-post | Exclude as direct pre-auction predictor unless forecast/vintage exists |
| Gas / coal / EU ETS | Potentially relevant but data may be licensed or timestamp-sensitive | Conditional candidate; daily settlements are insufficient |
| Weather data | Potentially pre-auction | Candidate only with forecast issuance/vintage evidence |

## Source-audit requirements

Every potential feature must record:

1. source owner and licence;
2. delivery-zone coverage;
3. historical depth;
4. frequency and timezone;
5. event timestamp;
6. publication timestamp;
7. revision policy;
8. whether the value was observable before D-1 12:00;
9. whether the source is reproducible without a proprietary data subscription.

## Stop rule

Do not construct a predictive or tradability claim unless a minimum
pre-auction feature set can be verified with timestamp evidence.

If no reproducible forecast-residual-load source exists before D-1 12:00,
the project remains an ex-post market-risk intelligence framework.
