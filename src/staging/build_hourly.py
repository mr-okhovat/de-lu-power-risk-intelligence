from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.config.load_series_registry import (
    SeriesDefinition,
    get_staging_series,
    load_series_registry,
)
from src.data_ingestion.smard_client import local_date_to_epoch_ms
from src.data_quality.staging_validators import (
    render_quality_report,
    validate_staging_frame,
)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_series_points(payload: Any) -> list[tuple[int, float | None]]:
    if not isinstance(payload, dict):
        raise ValueError("Expected SMARD payload to be a JSON object.")

    raw_series = payload.get("series")

    if not isinstance(raw_series, list):
        raise ValueError("SMARD payload does not contain a list field named 'series'.")

    points: list[tuple[int, float | None]] = []

    for item in raw_series:
        timestamp_ms: int
        value: float | None

        if isinstance(item, list) and len(item) >= 2:
            timestamp_ms = int(item[0])
            value = None if item[1] is None else float(item[1])

        elif isinstance(item, dict):
            if "timestamp" not in item:
                raise ValueError("Series item dict is missing 'timestamp'.")

            timestamp_ms = int(item["timestamp"])
            raw_value = item.get("value")
            value = None if raw_value is None else float(raw_value)

        else:
            raise ValueError(f"Unsupported SMARD series item format: {item!r}")

        points.append((timestamp_ms, value))

    return points


def load_smard_series_from_raw(
    *,
    raw_root: str | Path,
    series_definition: SeriesDefinition,
    smard_region: str,
    resolution: str,
    start_ms: int,
    end_ms_exclusive: int,
) -> pd.DataFrame:
    raw_root = Path(raw_root)

    pattern = (
        f"smard_{series_definition.filter_id}_{smard_region}_{resolution}_*.json"
    )

    files = sorted(
        path
        for path in (raw_root / series_definition.filter_id).glob(pattern)
        if not path.name.endswith(".metadata.json")
        and not path.name.startswith("manifest_")
    )

    if not files:
        raise FileNotFoundError(
            f"No raw files found for filter_id={series_definition.filter_id} "
            f"under {raw_root / series_definition.filter_id}"
        )

    rows: list[dict[str, Any]] = []

    for file in files:
        payload = read_json(file)
        points = extract_series_points(payload)

        for timestamp_ms, value in points:
            if start_ms <= timestamp_ms < end_ms_exclusive:
                rows.append(
                    {
                        "timestamp_utc": pd.to_datetime(timestamp_ms, unit="ms", utc=True),
                        f"{series_definition.internal_name}_mw": value,
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=["timestamp_utc", f"{series_definition.internal_name}_mw"]
        )

    df = pd.DataFrame(rows)

    value_column = f"{series_definition.internal_name}_mw"

    df = (
        df.sort_values("timestamp_utc")
        .groupby("timestamp_utc", as_index=False)[value_column]
        .last()
    )

    return df


def build_expected_hourly_index(*, start: str, end: str) -> pd.DataFrame:
    start_ms = local_date_to_epoch_ms(start, end_exclusive=False)
    end_ms_exclusive = local_date_to_epoch_ms(end, end_exclusive=True)

    start_utc = pd.to_datetime(start_ms, unit="ms", utc=True)
    end_utc_exclusive = pd.to_datetime(end_ms_exclusive, unit="ms", utc=True)

    timestamp_index = pd.date_range(
        start=start_utc,
        end=end_utc_exclusive - pd.Timedelta(hours=1),
        freq="h",
    )

    return pd.DataFrame({"timestamp_utc": timestamp_index})


def build_staging_hourly(
    *,
    start: str,
    end: str,
    market_label: str = "DE-LU",
    smard_region: str = "DE",
    resolution: str = "hour",
    raw_root: str | Path = "data/raw/smard",
    output_path: str | Path | None = None,
    quality_report_path: str | Path | None = None,
    registry_path: str | Path = "src/config/series_registry.yaml",
) -> pd.DataFrame:
    series = load_series_registry(registry_path)
    staging_series = get_staging_series(series)

    start_ms = local_date_to_epoch_ms(start, end_exclusive=False)
    end_ms_exclusive = local_date_to_epoch_ms(end, end_exclusive=True)

    staging = build_expected_hourly_index(start=start, end=end)

    for item in staging_series:
        series_df = load_smard_series_from_raw(
            raw_root=raw_root,
            series_definition=item,
            smard_region=smard_region,
            resolution=resolution,
            start_ms=start_ms,
            end_ms_exclusive=end_ms_exclusive,
        )

        staging = staging.merge(series_df, on="timestamp_utc", how="left")

    staging.insert(1, "timestamp_local", staging["timestamp_utc"].dt.tz_convert("Europe/Berlin"))
    staging.insert(2, "market_label", market_label)
    staging.insert(3, "smard_region", smard_region)

    value_columns = [
        f"{item.internal_name}_mw"
        for item in staging_series
    ]

    positive_only_columns = [
        f"{item.internal_name}_mw"
        for item in staging_series
        if item.expected_direction == "positive"
    ]

    provisional_columns = [
        f"{item.internal_name}_mw"
        for item in staging_series
        if item.semantic_status == "endpoint_verified_semantics_provisional"
    ]

    staging["missing_any_flag"] = staging[value_columns].isna().any(axis=1)

    quality_result = validate_staging_frame(
        staging,
        value_columns=value_columns,
        positive_only_columns=positive_only_columns,
        provisional_columns=provisional_columns,
    )

    if output_path is None:
        output_path = f"data/staging/clean_hourly_{market_label}_{start}_to_{end}.csv"

    if quality_report_path is None:
        quality_report_path = f"reports/data_quality_{start}_to_{end}.md"

    output_path = Path(output_path)
    quality_report_path = Path(quality_report_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    quality_report_path.parent.mkdir(parents=True, exist_ok=True)

    staging.to_csv(output_path, index=False)

    report = render_quality_report(
        result=quality_result,
        market_label=market_label,
        smard_region=smard_region,
        start=start,
        end=end,
        value_columns=value_columns,
        provisional_columns=provisional_columns,
    )

    quality_report_path.write_text(report, encoding="utf-8")

    metadata_path = output_path.with_suffix(".metadata.json")
    metadata_payload = {
        "stage": "staging",
        "output_path": str(output_path.as_posix()),
        "quality_report_path": str(quality_report_path.as_posix()),
        "market_label": market_label,
        "smard_region": smard_region,
        "resolution": resolution,
        "start": start,
        "end": end,
        "series": [asdict(item) for item in staging_series],
        "quality_result": asdict(quality_result),
    }

    metadata_path.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"OK | staging rows={len(staging)} | output={output_path}")
    print(f"OK | quality status={quality_result.status} | report={quality_report_path}")

    return staging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build clean hourly staging table.")

    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--smard-region", default="DE")
    parser.add_argument("--resolution", default="hour")
    parser.add_argument("--raw-root", default="data/raw/smard")
    parser.add_argument("--output", default=None)
    parser.add_argument("--quality-report", default=None)
    parser.add_argument("--registry", default="src/config/series_registry.yaml")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_staging_hourly(
        start=args.start,
        end=args.end,
        market_label=args.market_label,
        smard_region=args.smard_region,
        resolution=args.resolution,
        raw_root=args.raw_root,
        output_path=args.output,
        quality_report_path=args.quality_report,
        registry_path=args.registry,
    )


if __name__ == "__main__":
    main()
