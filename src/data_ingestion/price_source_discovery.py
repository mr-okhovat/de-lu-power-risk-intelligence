from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://www.smard.de/app/chart_data"
VERSION = "8A.1"


@dataclass(frozen=True)
class ProbeResult:
    filter_id: str
    label: str
    region: str
    resolution: str
    index_url: str
    sample_url: str | None
    status: str
    timestamp_count: int
    sample_points: int
    non_null_points: int
    min_value: float | None
    max_value: float | None
    error: str | None


DEFAULT_CANDIDATES = [
    ("4169", "day_ahead_price_candidate"),
]


DEFAULT_REGIONS = ["DE-LU", "DE"]


def fetch_json(url: str, timeout: int = 20) -> Any:
    request = Request(url, headers={"User-Agent": "de-lu-power-risk-intelligence/0.1"})

    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_timestamps(payload: Any) -> list[int]:
    if isinstance(payload, dict):
        values = payload.get("timestamps")
        if isinstance(values, list):
            return [int(item) for item in values if item is not None]

        series = payload.get("series")
        if isinstance(series, list):
            out = []
            for item in series:
                if isinstance(item, list) and item:
                    out.append(int(item[0]))
            return out

    if isinstance(payload, list):
        out = []
        for item in payload:
            if isinstance(item, int):
                out.append(item)
            elif isinstance(item, list) and item:
                out.append(int(item[0]))
        return out

    return []


def extract_numeric_values(payload: Any) -> list[float]:
    series = payload.get("series") if isinstance(payload, dict) else payload

    if not isinstance(series, list):
        return []

    values = []

    for item in series:
        if not isinstance(item, list) or len(item) < 2:
            continue

        value = item[1]
        if value is None:
            continue

        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue

    return values


def probe(filter_id: str, label: str, region: str, resolution: str) -> ProbeResult:
    index_url = f"{BASE_URL}/{filter_id}/{region}/index_{resolution}.json"

    try:
        index_payload = fetch_json(index_url)
        timestamps = extract_timestamps(index_payload)

        if not timestamps:
            return ProbeResult(
                filter_id=filter_id,
                label=label,
                region=region,
                resolution=resolution,
                index_url=index_url,
                sample_url=None,
                status="FAIL",
                timestamp_count=0,
                sample_points=0,
                non_null_points=0,
                min_value=None,
                max_value=None,
                error="index returned no timestamps",
            )

        sample_timestamp = timestamps[-1]
        sample_url = f"{BASE_URL}/{filter_id}/{region}/{filter_id}_{region}_{resolution}_{sample_timestamp}.json"

        sample_payload = fetch_json(sample_url)
        values = extract_numeric_values(sample_payload)

        if not values:
            return ProbeResult(
                filter_id=filter_id,
                label=label,
                region=region,
                resolution=resolution,
                index_url=index_url,
                sample_url=sample_url,
                status="FAIL",
                timestamp_count=len(timestamps),
                sample_points=0,
                non_null_points=0,
                min_value=None,
                max_value=None,
                error="sample returned no numeric values",
            )

        return ProbeResult(
            filter_id=filter_id,
            label=label,
            region=region,
            resolution=resolution,
            index_url=index_url,
            sample_url=sample_url,
            status="PASS",
            timestamp_count=len(timestamps),
            sample_points=len(values),
            non_null_points=len(values),
            min_value=min(values),
            max_value=max(values),
            error=None,
        )

    except HTTPError as exc:
        error = f"HTTP {exc.code}"
    except URLError as exc:
        error = str(exc.reason)
    except Exception as exc:
        error = str(exc)

    return ProbeResult(
        filter_id=filter_id,
        label=label,
        region=region,
        resolution=resolution,
        index_url=index_url,
        sample_url=None,
        status="FAIL",
        timestamp_count=0,
        sample_points=0,
        non_null_points=0,
        min_value=None,
        max_value=None,
        error=error,
    )


def choose(results: list[ProbeResult]) -> ProbeResult | None:
    passing = [item for item in results if item.status == "PASS"]

    if not passing:
        return None

    for region in DEFAULT_REGIONS:
        for item in passing:
            if item.region == region:
                return item

    return passing[0]


def make_report(results: list[ProbeResult], selected: ProbeResult | None) -> str:
    lines = [
        "# Price source discovery",
        "",
        f"Version: {VERSION}",
        "",
        "## Result",
        "",
    ]

    if selected:
        lines += [
            f"Selected candidate: `{selected.label}`",
            f"Filter ID: `{selected.filter_id}`",
            f"Region: `{selected.region}`",
            f"Resolution: `{selected.resolution}`",
            f"Index URL: `{selected.index_url}`",
            f"Sample URL: `{selected.sample_url}`",
            "",
        ]
    else:
        lines.append("No usable price source was found.")

    lines += [
        "## Probes",
        "",
        "| filter | label | region | status | timestamps | sample points | min | max | error |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for item in results:
        lines.append(
            f"| {item.filter_id} | {item.label} | {item.region} | {item.status} | "
            f"{item.timestamp_count} | {item.sample_points} | {item.min_value} | {item.max_value} | {item.error or ''} |"
        )

    lines += [
        "",
        "## Next",
        "",
        "Use the selected candidate to build a clean hourly price table. Do not merge prices into the risk model until the price table has its own quality report.",
        "",
    ]

    return "\n".join(lines)


def run(output_report: str, output_json: str, resolution: str) -> None:
    results = []

    for filter_id, label in DEFAULT_CANDIDATES:
        for region in DEFAULT_REGIONS:
            results.append(probe(filter_id, label, region, resolution))

    selected = choose(results)

    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    Path(output_report).write_text(make_report(results, selected), encoding="utf-8")

    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "selected": asdict(selected) if selected else None,
                "results": [asdict(item) for item in results],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    if not selected:
        print(f"STOP | no price source found | report={output_report}")
        raise SystemExit(1)

    print(f"OK | selected price source filter={selected.filter_id} region={selected.region}")
    print(f"OK | report={output_report}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", default="hour")
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    run(
        output_report=args.output_report,
        output_json=args.output_json,
        resolution=args.resolution,
    )


if __name__ == "__main__":
    main()
