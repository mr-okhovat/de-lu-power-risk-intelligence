from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.data_ingestion.smard_client import SmardClient, load_smard_settings


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilterProbeResult:
    filter_id: str
    filter_name: str
    unit: str
    category: str
    ok: bool
    index_url: str
    timestamp_count: int
    first_chunk_utc: str | None
    last_chunk_utc: str | None
    error: str | None


def epoch_ms_to_utc_iso(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).replace(
        microsecond=0
    ).isoformat()


def probe_filter(
    *,
    client: SmardClient,
    filter_id: str,
    smard_region: str,
    resolution: str,
) -> FilterProbeResult:
    meta = client.settings.filters[filter_id]
    index_url = client.build_index_url(
        filter_id=filter_id,
        smard_region=smard_region,
        resolution=resolution,
    )

    try:
        timestamps = client.get_available_chunk_timestamps(
            filter_id=filter_id,
            smard_region=smard_region,
            resolution=resolution,
        )

        return FilterProbeResult(
            filter_id=filter_id,
            filter_name=meta.name,
            unit=meta.unit,
            category=meta.category,
            ok=True,
            index_url=index_url,
            timestamp_count=len(timestamps),
            first_chunk_utc=epoch_ms_to_utc_iso(min(timestamps)),
            last_chunk_utc=epoch_ms_to_utc_iso(max(timestamps)),
            error=None,
        )

    except Exception as exc:
        LOGGER.warning("Filter probe failed for %s: %s", filter_id, exc)

        return FilterProbeResult(
            filter_id=filter_id,
            filter_name=meta.name,
            unit=meta.unit,
            category=meta.category,
            ok=False,
            index_url=index_url,
            timestamp_count=0,
            first_chunk_utc=None,
            last_chunk_utc=None,
            error=str(exc),
        )


def render_markdown_report(
    *,
    results: list[FilterProbeResult],
    smard_region: str,
    resolution: str,
) -> str:
    ok_count = sum(1 for item in results if item.ok)
    fail_count = len(results) - ok_count

    lines: list[str] = [
        "# SMARD Filter Discovery Report",
        "",
        f"- SMARD region: `{smard_region}`",
        f"- Resolution: `{resolution}`",
        f"- Checked filters: `{len(results)}`",
        f"- OK: `{ok_count}`",
        f"- Failed: `{fail_count}`",
        "",
        "## Results",
        "",
        "| Filter | Name | Category | Unit | Status | Timestamps | First chunk UTC | Last chunk UTC |",
        "|---|---|---|---|---:|---:|---|---|",
    ]

    for item in results:
        status = "OK" if item.ok else "FAIL"
        lines.append(
            "| "
            f"{item.filter_id} | "
            f"{item.filter_name} | "
            f"{item.category} | "
            f"{item.unit} | "
            f"{status} | "
            f"{item.timestamp_count} | "
            f"{item.first_chunk_utc or ''} | "
            f"{item.last_chunk_utc or ''} |"
        )

    failed = [item for item in results if not item.ok]

    if failed:
        lines.extend(["", "## Failed Filters", ""])

        for item in failed:
            lines.extend(
                [
                    f"### {item.filter_id} — {item.filter_name}",
                    "",
                    f"- URL: `{item.index_url}`",
                    f"- Error: `{item.error}`",
                    "",
                ]
            )

    lines.extend(
        [
            "",
            "## Next Action",
            "",
            "Use only filters with `OK` status for multi-filter ingestion.",
            "Failed filters must not be treated as valid market data.",
            "",
        ]
    )

    return "\n".join(lines)


def write_outputs(
    *,
    results: list[FilterProbeResult],
    json_path: str | Path = "reports/smard_filter_discovery.json",
    markdown_path: str | Path = "reports/smard_filter_discovery.md",
    smard_region: str,
    resolution: str,
) -> None:
    json_output = Path(json_path)
    markdown_output = Path(markdown_path)

    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    with json_output.open("w", encoding="utf-8") as f:
        json.dump([asdict(item) for item in results], f, ensure_ascii=False, indent=2)

    markdown_output.write_text(
        render_markdown_report(
            results=results,
            smard_region=smard_region,
            resolution=resolution,
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe configured SMARD filter endpoints.")

    parser.add_argument("--config", default="src/config/sources.yaml")
    parser.add_argument("--smard-region", default="DE")
    parser.add_argument("--resolution", default="hour")
    parser.add_argument(
        "--filters",
        nargs="*",
        default=None,
        help="Optional filter IDs. If omitted, all configured filters are probed.",
    )
    parser.add_argument("--json-output", default="reports/smard_filter_discovery.json")
    parser.add_argument("--markdown-output", default="reports/smard_filter_discovery.md")

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    args = parse_args()
    settings = load_smard_settings(args.config)
    client = SmardClient(settings)

    filter_ids = args.filters or sorted(settings.filters.keys(), key=int)

    results: list[FilterProbeResult] = []

    for filter_id in filter_ids:
        if filter_id not in settings.filters:
            LOGGER.warning("Skipping unknown configured filter: %s", filter_id)
            continue

        results.append(
            probe_filter(
                client=client,
                filter_id=filter_id,
                smard_region=args.smard_region,
                resolution=args.resolution,
            )
        )

    write_outputs(
        results=results,
        json_path=args.json_output,
        markdown_path=args.markdown_output,
        smard_region=args.smard_region,
        resolution=args.resolution,
    )

    ok_filters = [item.filter_id for item in results if item.ok]
    failed_filters = [item.filter_id for item in results if not item.ok]

    print(f"OK filters: {' '.join(ok_filters) if ok_filters else 'NONE'}")
    print(f"Failed filters: {' '.join(failed_filters) if failed_filters else 'NONE'}")
    print(f"Report written: {args.markdown_output}")


if __name__ == "__main__":
    main()
