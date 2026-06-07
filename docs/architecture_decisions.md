# Architecture Decisions

## ADR-001 — Use SMARD as the First Data Foundation

Status: Accepted

Reason:

SMARD is the first source because it provides public German electricity market data and allows the project to build a real ingestion and metadata layer before adding more complex sources.

Consequence:

The project starts with SMARD raw JSON ingestion, metadata files, manifest files, and filter discovery before adding ENTSO-E, weather, balancing, SQL, or Power BI.

## ADR-002 — Keep Raw Data Immutable

Status: Accepted

Reason:

Raw market data must remain traceable and reproducible.

Consequence:

Raw data is stored under `data/raw/{source}/`. Staging and processed outputs must be generated from raw data and must not overwrite raw files.

## ADR-003 — Separate Source Region from Analytical Market Label

Status: Accepted

Reason:

SMARD endpoint region codes and the analytical DE-LU market label are not necessarily the same thing.

Consequence:

The code stores both:

- `smard_region`
- `market_label`

Reports must not collapse these fields into one ambiguous label.

## ADR-004 — Add Source Semantics Before Staging

Status: Accepted

Reason:

Endpoint availability is not equal to semantic correctness.

Consequence:

Before building staging tables, the project must maintain a series registry with semantic status, units, category, and usage rules.

## ADR-005 — Do Not Commit Large Raw Data as Portfolio Evidence

Status: Accepted

Reason:

Raw data can be regenerated and may become large. The repository should stay clean and reviewable.

Consequence:

Large generated raw/staging/processed files are ignored by `.gitignore`. Small reports, metadata samples, and documentation may be committed when useful.

## ADR-006 — SQL and Power BI Are Downstream Layers

Status: Accepted

Reason:

SQL schemas and Power BI dashboards should be built from clean staging/processed outputs, not directly from raw JSON.

Consequence:

SQL and Power BI are reserved for later phases after staging, feature engineering, and signal tables are stable.
