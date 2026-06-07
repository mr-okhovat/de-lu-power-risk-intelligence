# SMARD Filter Discovery Report

- SMARD region: `DE`
- Resolution: `hour`
- Checked filters: `5`
- OK: `5`
- Failed: `0`

## Results

| Filter | Name | Category | Unit | Status | Timestamps | First chunk UTC | Last chunk UTC |
|---|---|---|---|---:|---:|---|---|
| 410 | Total Load | consumption | MW | OK | 597 | 2014-12-28T23:00:00+00:00 | 2026-05-31T22:00:00+00:00 |
| 1225 | Wind Offshore Candidate | generation | MW | OK | 597 | 2014-12-28T23:00:00+00:00 | 2026-05-31T22:00:00+00:00 |
| 4067 | Wind Candidate | generation | MW | OK | 597 | 2014-12-28T23:00:00+00:00 | 2026-05-31T22:00:00+00:00 |
| 4068 | Solar Candidate | generation | MW | OK | 597 | 2014-12-28T23:00:00+00:00 | 2026-05-31T22:00:00+00:00 |
| 4359 | Residual Load | consumption | MW | OK | 597 | 2014-12-28T23:00:00+00:00 | 2026-05-31T22:00:00+00:00 |

## Next Action

Use only filters with `OK` status for multi-filter ingestion.
Failed filters must not be treated as valid market data.
