from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd


BASE_URL = "https://www.smard.de/app/chart_data"
BERLIN = "Europe/Berlin"
VERSION = "8B.1"


@dataclass(frozen=True)
class PriceQuality:
    status: str
    row_count: int
    expected_rows: int
    missing_rows: int
    duplicate_timestamps: int
    missing_prices: int
    min_price: float | None
    max_price: float | None
    mean_price: float | None
    source_filter_id: str
    source_region: str
    notes: list[str]


def fetch_json(url: str, timeout: int = 20) -> Any:
    req = Request(url, headers={"User-Agent": "de-lu-power-risk-intelligence/0.1"})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def timestamps_from_index(payload: Any) -> list[int]:
    if isinstance(payload, dict) and isinstance(payload.get("timestamps"), list):
        return sorted({int(item) for item in payload["timestamps"] if item is not None})
    return []


def rows_from_series(payload: Any) -> list[dict[str, object]]:
    series = payload.get("series") if isinstance(payload, dict) else payload

    if not isinstance(series, list):
        return []

    rows = []
    for item in series:
        if not isinstance(item, list) or len(item) < 2:
            continue

        ts, value = item[0], item[1]
        if ts is None:
            continue

        rows.append(
            {
                "timestamp_utc": pd.to_datetime(int(ts), unit="ms", utc=True),
                "price_eur_per_mwh": None if value is None else float(value),
            }
        )

    return rows


def local_window(start: str, end: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_local = pd.Timestamp(start).tz_localize(BERLIN)
    end_local = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(BERLIN)

    return start_local.tz_convert("UTC"), end_local.tz_convert("UTC")


def chunk_candidates(timestamps: list[int], start_utc: pd.Timestamp, end_utc: pd.Timestamp) -> list[int]:
    lookback = start_utc - pd.Timedelta(days=14)

    out = []
    for ts in timestamps:
        stamp = pd.to_datetime(ts, unit="ms", utc=True)
        if lookback <= stamp < end_utc:
            out.append(ts)

    return out


def build_price_frame(
    *,
    start: str,
    end: str,
    market_label: str,
    region: str,
    filter_id: str,
    resolution: str,
) -> pd.DataFrame:
    start_utc, end_utc = local_window(start, end)

    index_url = f"{BASE_URL}/{filter_id}/{region}/index_{resolution}.json"
    index_payload = fetch_json(index_url)
    timestamps = timestamps_from_index(index_payload)
    candidates = chunk_candidates(timestamps, start_utc, end_utc)

    if not candidates:
        raise RuntimeError("No price chunks found for selected window.")

    rows: list[dict[str, object]] = []

    for chunk_ts in candidates:
        url = f"{BASE_URL}/{filter_id}/{region}/{filter_id}_{region}_{resolution}_{chunk_ts}.json"
        payload = fetch_json(url)
        rows.extend(rows_from_series(payload))

    if not rows:
        raise RuntimeError("Price chunks returned no series rows.")

    df = pd.DataFrame(rows)
    df = df.sort_values("timestamp_utc").drop_duplicates("timestamp_utc", keep="last")
    df = df[(df["timestamp_utc"] >= start_utc) & (df["timestamp_utc"] < end_utc)].copy()

    df["timestamp_local"] = df["timestamp_utc"].dt.tz_convert(BERLIN)
    df["market_label"] = market_label
    df["smard_region"] = region
    df["price_source"] = "SMARD / Bundesnetzagentur"
    df["price_filter_id"] = filter_id
    df["price_schema_version"] = VERSION

    return df[
        [
            "timestamp_utc",
            "timestamp_local",
            "market_label",
            "smard_region",
            "price_eur_per_mwh",
            "price_source",
            "price_filter_id",
            "price_schema_version",
        ]
    ].reset_index(drop=True)


def check_quality(
    df: pd.DataFrame,
    *,
    start: str,
    end: str,
    filter_id: str,
    region: str,
) -> PriceQuality:
    start_utc, end_utc = local_window(start, end)
    expected_rows = int((end_utc - start_utc) / pd.Timedelta(hours=1))

    row_count = int(len(df))
    duplicate_timestamps = int(df["timestamp_utc"].duplicated().sum())
    missing_prices = int(df["price_eur_per_mwh"].isna().sum())
    missing_rows = max(expected_rows - row_count, 0)

    notes = []

    if row_count != expected_rows:
        notes.append(f"Expected {expected_rows} hourly rows but found {row_count}.")

    if duplicate_timestamps:
        notes.append(f"Duplicate timestamps found: {duplicate_timestamps}.")

    if missing_prices:
        notes.append(f"Missing price values found: {missing_prices}.")

    if not notes:
        notes.append("Price table passed hourly completeness and value checks.")

    status = "PASS" if not (missing_rows or duplicate_timestamps or missing_prices) else "CHECK NEEDED"

    return PriceQuality(
        status=status,
        row_count=row_count,
        expected_rows=expected_rows,
        missing_rows=missing_rows,
        duplicate_timestamps=duplicate_timestamps,
        missing_prices=missing_prices,
        min_price=None if row_count == 0 else float(df["price_eur_per_mwh"].min()),
        max_price=None if row_count == 0 else float(df["price_eur_per_mwh"].max()),
        mean_price=None if row_count == 0 else float(df["price_eur_per_mwh"].mean()),
        source_filter_id=filter_id,
        source_region=region,
        notes=notes,
    )


def report_text(quality: PriceQuality, output_csv: str) -> str:
    lines = [
        "# Price table quality",
        "",
        f"Version: {VERSION}",
        f"Status: {quality.status}",
        f"Output: `{output_csv}`",
        "",
        "## Checks",
        "",
        f"- Rows: {quality.row_count}",
        f"- Expected rows: {quality.expected_rows}",
        f"- Missing rows: {quality.missing_rows}",
        f"- Duplicate timestamps: {quality.duplicate_timestamps}",
        f"- Missing prices: {quality.missing_prices}",
        f"- Min price EUR/MWh: {quality.min_price}",
        f"- Max price EUR/MWh: {quality.max_price}",
        f"- Mean price EUR/MWh: {quality.mean_price}",
        f"- Source filter: {quality.source_filter_id}",
        f"- Source region: {quality.source_region}",
        "",
        "## Notes",
        "",
    ]

    for note in quality.notes:
        lines.append(f"- {note}")

    lines += [
        "",
        "This is a clean price table only. It is not yet merged with features or risk signals.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    start: str,
    end: str,
    market_label: str,
    region: str,
    filter_id: str,
    resolution: str,
    output_csv: str,
    output_report: str,
    output_json: str,
) -> None:
    df = build_price_frame(
        start=start,
        end=end,
        market_label=market_label,
        region=region,
        filter_id=filter_id,
        resolution=resolution,
    )

    quality = check_quality(df, start=start, end=end, filter_id=filter_id, region=region)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_csv, index=False)
    Path(output_report).write_text(report_text(quality, output_csv), encoding="utf-8")
    Path(output_json).write_text(json.dumps(asdict(quality), indent=2, sort_keys=True), encoding="utf-8")

    print(f"OK | price rows={quality.row_count} | status={quality.status}")
    print(f"OK | output={output_csv}")

    if quality.status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--region", default="DE-LU")
    parser.add_argument("--filter-id", default="4169")
    parser.add_argument("--resolution", default="hour")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    build(
        start=args.start,
        end=args.end,
        market_label=args.market_label,
        region=args.region,
        filter_id=args.filter_id,
        resolution=args.resolution,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
