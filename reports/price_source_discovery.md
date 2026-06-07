# Price source discovery

Version: 8A.1

## Result

Selected candidate: `day_ahead_price_candidate`
Filter ID: `4169`
Region: `DE-LU`
Resolution: `hour`
Index URL: `https://www.smard.de/app/chart_data/4169/DE-LU/index_hour.json`
Sample URL: `https://www.smard.de/app/chart_data/4169/DE-LU/4169_DE-LU_hour_1780869600000.json`

## Probes

| filter | label | region | status | timestamps | sample points | min | max | error |
|---|---|---|---:|---:|---:|---:|---:|---|
| 4169 | day_ahead_price_candidate | DE-LU | PASS | 402 | 24 | 54.48 | 208.9 |  |
| 4169 | day_ahead_price_candidate | DE | PASS | 402 | 24 | 54.48 | 208.9 |  |

## Next

Use the selected candidate to build a clean hourly price table. Do not merge prices into the risk model until the price table has its own quality report.
