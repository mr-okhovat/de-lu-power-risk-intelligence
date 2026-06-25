#!/usr/bin/env bash
set -Eeuo pipefail

START="2020-01-01"
END="2024-12-31"
MARKET_LABEL="DE-LU"
REGION="DE-LU"
FILTER_ID="4169"
RESOLUTION="hour"

PRICE_CSV="data/processed/hourly_prices_${MARKET_LABEL}_${START}_to_${END}.csv"
QUALITY_MD="reports/price_quality_${START}_to_${END}.md"
QUALITY_JSON="reports/price_quality_${START}_to_${END}.json"
BUILD_LOG="reports/historical_price_panel_${START}_to_${END}.log"
AUDIT_JSON="reports/historical_price_panel_${START}_to_${END}_audit.json"
AUDIT_MD="reports/historical_price_panel_${START}_to_${END}_audit.md"

mkdir -p data/processed reports

printf '\n===== HISTORICAL PRICE BUILD =====\n'
printf 'market=%s | region=%s | filter=%s | range=%s to %s\n' \
  "$MARKET_LABEL" "$REGION" "$FILTER_ID" "$START" "$END"

set +e
python -m src.prices.price_table \
  --start "$START" \
  --end "$END" \
  --market-label "$MARKET_LABEL" \
  --region "$REGION" \
  --filter-id "$FILTER_ID" \
  --resolution "$RESOLUTION" \
  --output-csv "$PRICE_CSV" \
  --output-report "$QUALITY_MD" \
  --output-json "$QUALITY_JSON" \
  >"$BUILD_LOG" 2>&1
BUILD_RC=$?
set -e

printf '\n===== PRICE TABLE LOG (LAST 50 LINES) =====\n'
tail -n 50 "$BUILD_LOG" || true

if [ "$BUILD_RC" -ne 0 ]; then
  printf '\nSTOP | historical price extraction returned exit code %s\n' "$BUILD_RC"
  printf 'Inspect: %s\n' "$BUILD_LOG"
  exit "$BUILD_RC"
fi

export START END MARKET_LABEL REGION FILTER_ID PRICE_CSV QUALITY_JSON AUDIT_JSON AUDIT_MD

python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

start = os.environ["START"]
end = os.environ["END"]
market_label = os.environ["MARKET_LABEL"]
region = os.environ["REGION"]
filter_id = os.environ["FILTER_ID"]

price_csv = Path(os.environ["PRICE_CSV"])
quality_json = Path(os.environ["QUALITY_JSON"])
audit_json = Path(os.environ["AUDIT_JSON"])
audit_md = Path(os.environ["AUDIT_MD"])

berlin = "Europe/Berlin"

if not price_csv.exists():
    raise FileNotFoundError(f"Missing price output: {price_csv}")

df = pd.read_csv(price_csv)

required = {
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "price_eur_per_mwh",
    "price_source",
    "price_filter_id",
    "price_schema_version",
}

missing_columns = sorted(required - set(df.columns))

timestamps = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
expected = pd.date_range(
    start=pd.Timestamp(start).tz_localize(berlin).tz_convert("UTC"),
    end=(pd.Timestamp(end) + pd.Timedelta(days=1))
        .tz_localize(berlin)
        .tz_convert("UTC"),
    freq="h",
    inclusive="left",
)

actual_unique = pd.DatetimeIndex(timestamps.dropna().unique()).sort_values()
expected_index = pd.DatetimeIndex(expected)

missing_expected = expected_index.difference(actual_unique)
unexpected_actual = actual_unique.difference(expected_index)

quality_payload = (
    json.loads(quality_json.read_text(encoding="utf-8"))
    if quality_json.exists()
    else {}
)

filter_ids = sorted(map(str, df["price_filter_id"].dropna().unique()))
sources = sorted(map(str, df["price_source"].dropna().unique()))
schemas = sorted(map(str, df["price_schema_version"].dropna().unique()))
markets = sorted(map(str, df["market_label"].dropna().unique()))
regions = sorted(map(str, df["smard_region"].dropna().unique()))

audit = {
    "status": None,
    "scope": "Historical DE-LU day-ahead price source panel only; no prediction claim.",
    "source_contract": {
        "market_label": market_label,
        "region": region,
        "filter_id": filter_id,
        "resolution": "hour",
    },
    "row_count": int(len(df)),
    "expected_hour_count": int(len(expected_index)),
    "duplicate_timestamp_count": int(timestamps.duplicated().sum()),
    "invalid_timestamp_count": int(timestamps.isna().sum()),
    "missing_expected_hour_count": int(len(missing_expected)),
    "unexpected_hour_count": int(len(unexpected_actual)),
    "missing_price_count": int(df["price_eur_per_mwh"].isna().sum()),
    "first_timestamp_utc": (
        str(timestamps.min()) if not timestamps.dropna().empty else None
    ),
    "last_timestamp_utc": (
        str(timestamps.max()) if not timestamps.dropna().empty else None
    ),
    "price_min_eur_per_mwh": (
        float(df["price_eur_per_mwh"].min())
        if df["price_eur_per_mwh"].notna().any()
        else None
    ),
    "price_max_eur_per_mwh": (
        float(df["price_eur_per_mwh"].max())
        if df["price_eur_per_mwh"].notna().any()
        else None
    ),
    "price_mean_eur_per_mwh": (
        float(df["price_eur_per_mwh"].mean())
        if df["price_eur_per_mwh"].notna().any()
        else None
    ),
    "observed_market_labels": markets,
    "observed_regions": regions,
    "observed_filter_ids": filter_ids,
    "observed_sources": sources,
    "observed_schema_versions": schemas,
    "missing_required_columns": missing_columns,
    "price_table_quality_status": quality_payload.get("status"),
    "price_table_quality": quality_payload,
}

pass_check = (
    not missing_columns
    and audit["row_count"] == audit["expected_hour_count"]
    and audit["duplicate_timestamp_count"] == 0
    and audit["invalid_timestamp_count"] == 0
    and audit["missing_expected_hour_count"] == 0
    and audit["unexpected_hour_count"] == 0
    and audit["missing_price_count"] == 0
    and filter_ids == [filter_id]
    and markets == [market_label]
    and regions == [region]
    and audit["price_table_quality_status"] == "PASS"
)

audit["status"] = "PASS" if pass_check else "STOP — NEEDS VERIFICATION"

audit_json.write_text(
    json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True),
    encoding="utf-8",
)

lines = [
    "# Historical Price Panel Audit",
    "",
    f"- Status: `{audit['status']}`",
    f"- Range: `{start}` to `{end}` Europe/Berlin delivery dates",
    f"- Rows: `{audit['row_count']}` / expected `{audit['expected_hour_count']}`",
    f"- Missing expected hours: `{audit['missing_expected_hour_count']}`",
    f"- Unexpected hours: `{audit['unexpected_hour_count']}`",
    f"- Duplicate timestamps: `{audit['duplicate_timestamp_count']}`",
    f"- Missing prices: `{audit['missing_price_count']}`",
    f"- Filter IDs: `{filter_ids}`",
    f"- Sources: `{sources}`",
    f"- Price-table quality status: `{audit['price_table_quality_status']}`",
    "",
    "## Scope",
    "",
    "This panel is an ex-post research input. It does not establish a tradable",
    "signal or confirm that realised fundamentals were known before the",
    "day-ahead auction.",
    "",
]

audit_md.write_text("\n".join(lines), encoding="utf-8")

print(json.dumps(
    {
        key: audit[key]
        for key in (
            "status",
            "row_count",
            "expected_hour_count",
            "missing_expected_hour_count",
            "unexpected_hour_count",
            "duplicate_timestamp_count",
            "missing_price_count",
            "observed_filter_ids",
            "price_table_quality_status",
        )
    },
    indent=2,
))

if not pass_check:
    raise SystemExit(1)
PY

printf '\n===== HISTORICAL PRICE AUDIT =====\n'
cat "$AUDIT_MD"

printf '\n===== OUTPUT FILES =====\n'
ls -lh "$PRICE_CSV" "$QUALITY_MD" "$QUALITY_JSON" "$AUDIT_JSON" "$AUDIT_MD"

printf '\nPASS | historical price panel is ready for the discovery gate.\n'
