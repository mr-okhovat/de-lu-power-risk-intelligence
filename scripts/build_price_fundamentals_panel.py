from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_FEATURE_COLUMNS = {
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "residual_load_official_mw",
    "renewable_share",
    "residual_load_ramp_mw",
}

REQUIRED_PRICE_COLUMNS = {
    "timestamp_utc",
    "price_eur_per_mwh",
    "price_source",
    "price_filter_id",
    "price_schema_version",
}


def write_outputs(
    *,
    report_path: Path,
    json_path: Path,
    audit: dict[str, object],
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Historical Price-Fundamentals Panel Audit",
        "",
        f"- Status: `{audit['status']}`",
        f"- Feature rows: `{audit['feature_rows']}`",
        f"- Price rows: `{audit['price_rows']}`",
        f"- Merged rows: `{audit['merged_rows']}`",
        f"- Feature duplicate timestamps: `{audit['feature_duplicate_timestamps']}`",
        f"- Price duplicate timestamps: `{audit['price_duplicate_timestamps']}`",
        f"- Missing prices after merge: `{audit['missing_prices_after_merge']}`",
        f"- Unmatched feature timestamps: `{audit['unmatched_feature_timestamps']}`",
        f"- Unmatched price timestamps: `{audit['unmatched_price_timestamps']}`",
        f"- Observed price filters: `{audit['observed_price_filter_ids']}`",
        "",
        "## Scope",
        "",
        "The merged panel is an ex-post research input. It does not establish",
        "forecastability, causality, tradability or pre-auction availability.",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--prices", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--json", required=True)
    args = parser.parse_args()

    feature_path = Path(args.features)
    price_path = Path(args.prices)
    output_path = Path(args.output)
    report_path = Path(args.report)
    json_path = Path(args.json)

    features = pd.read_csv(feature_path)
    prices = pd.read_csv(price_path)

    missing_feature_columns = sorted(
        REQUIRED_FEATURE_COLUMNS - set(features.columns)
    )
    missing_price_columns = sorted(
        REQUIRED_PRICE_COLUMNS - set(prices.columns)
    )

    for frame in (features, prices):
        frame["timestamp_utc"] = pd.to_datetime(
            frame["timestamp_utc"],
            utc=True,
            errors="coerce",
        )

    feature_ts = features["timestamp_utc"]
    price_ts = prices["timestamp_utc"]

    feature_duplicate_timestamps = int(feature_ts.duplicated().sum())
    price_duplicate_timestamps = int(price_ts.duplicated().sum())

    feature_index = pd.DatetimeIndex(feature_ts.dropna().unique())
    price_index = pd.DatetimeIndex(price_ts.dropna().unique())

    unmatched_feature_timestamps = int(
        len(feature_index.difference(price_index))
    )
    unmatched_price_timestamps = int(
        len(price_index.difference(feature_index))
    )

    price_columns = [
        "timestamp_utc",
        "price_eur_per_mwh",
        "price_source",
        "price_filter_id",
        "price_schema_version",
    ]

    merged = features.merge(
        prices[price_columns],
        on="timestamp_utc",
        how="left",
        validate="one_to_one",
    ).sort_values("timestamp_utc").reset_index(drop=True)

    missing_prices_after_merge = int(
        merged["price_eur_per_mwh"].isna().sum()
    )

    observed_price_filter_ids = sorted(
        map(str, prices["price_filter_id"].dropna().unique())
    )

    audit = {
        "status": None,
        "feature_input": str(feature_path.as_posix()),
        "price_input": str(price_path.as_posix()),
        "output": str(output_path.as_posix()),
        "feature_rows": int(len(features)),
        "price_rows": int(len(prices)),
        "merged_rows": int(len(merged)),
        "missing_feature_columns": missing_feature_columns,
        "missing_price_columns": missing_price_columns,
        "feature_invalid_timestamps": int(feature_ts.isna().sum()),
        "price_invalid_timestamps": int(price_ts.isna().sum()),
        "feature_duplicate_timestamps": feature_duplicate_timestamps,
        "price_duplicate_timestamps": price_duplicate_timestamps,
        "unmatched_feature_timestamps": unmatched_feature_timestamps,
        "unmatched_price_timestamps": unmatched_price_timestamps,
        "missing_prices_after_merge": missing_prices_after_merge,
        "observed_price_filter_ids": observed_price_filter_ids,
    }

    passed = (
        not missing_feature_columns
        and not missing_price_columns
        and audit["feature_invalid_timestamps"] == 0
        and audit["price_invalid_timestamps"] == 0
        and feature_duplicate_timestamps == 0
        and price_duplicate_timestamps == 0
        and unmatched_feature_timestamps == 0
        and unmatched_price_timestamps == 0
        and missing_prices_after_merge == 0
        and len(merged) == len(features) == len(prices)
    )

    audit["status"] = "PASS" if passed else "STOP — NEEDS VERIFICATION"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    write_outputs(
        report_path=report_path,
        json_path=json_path,
        audit=audit,
    )

    print(
        f"OK | merged rows={len(merged)} | "
        f"status={audit['status']} | output={output_path}"
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
