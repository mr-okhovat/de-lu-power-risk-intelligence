from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from zoneinfo import ZoneInfo


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmardFilter:
    filter_id: str
    name: str
    unit: str
    category: str


@dataclass(frozen=True)
class SmardSettings:
    name: str
    base_url: str
    default_smard_region: str
    default_market_label: str
    default_resolution: str
    timeout_seconds: int
    retries: int
    retry_sleep_seconds: int
    attribution: str
    license_note: str
    filters: dict[str, SmardFilter]


def load_smard_settings(config_path: str | Path = "src/config/sources.yaml") -> SmardSettings:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    smard = config["smard"]

    filters: dict[str, SmardFilter] = {}
    for filter_id, meta in smard["filters"].items():
        filter_id_str = str(filter_id)
        filters[filter_id_str] = SmardFilter(
            filter_id=filter_id_str,
            name=str(meta["name"]),
            unit=str(meta["unit"]),
            category=str(meta["category"]),
        )

    return SmardSettings(
        name=str(smard["name"]),
        base_url=str(smard["base_url"]).rstrip("/"),
        default_smard_region=str(smard["default_smard_region"]),
        default_market_label=str(smard["default_market_label"]),
        default_resolution=str(smard["default_resolution"]),
        timeout_seconds=int(smard["timeout_seconds"]),
        retries=int(smard["retries"]),
        retry_sleep_seconds=int(smard["retry_sleep_seconds"]),
        attribution=str(smard["attribution"]),
        license_note=str(smard["license_note"]),
        filters=filters,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def local_date_to_epoch_ms(value: str, *, end_exclusive: bool = False) -> int:
    parsed = date.fromisoformat(value)

    if end_exclusive:
        parsed = parsed + timedelta(days=1)

    berlin = ZoneInfo("Europe/Berlin")
    local_dt = datetime(parsed.year, parsed.month, parsed.day, 0, 0, 0, tzinfo=berlin)
    utc_dt = local_dt.astimezone(timezone.utc)

    return int(utc_dt.timestamp() * 1000)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)


def extract_timestamps(index_payload: Any) -> list[int]:
    if isinstance(index_payload, dict):
        raw_timestamps = index_payload.get("timestamps", [])
    elif isinstance(index_payload, list):
        raw_timestamps = index_payload
    else:
        raise ValueError("Unexpected SMARD index payload format.")

    timestamps: list[int] = []

    for item in raw_timestamps:
        if isinstance(item, dict) and "timestamp" in item:
            timestamps.append(int(item["timestamp"]))
        else:
            timestamps.append(int(item))

    return sorted(set(timestamps))


def count_series_points(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0

    series = payload.get("series")

    if isinstance(series, list):
        return len(series)

    return 0


class SmardClient:
    def __init__(self, settings: SmardSettings):
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "de-lu-power-risk-intelligence/0.1",
                "Accept": "application/json",
            }
        )

    def build_index_url(self, filter_id: str, smard_region: str, resolution: str) -> str:
        return (
            f"{self.settings.base_url}/chart_data/"
            f"{filter_id}/{smard_region}/index_{resolution}.json"
        )

    def build_timeseries_url(
        self,
        filter_id: str,
        smard_region: str,
        resolution: str,
        timestamp_ms: int,
    ) -> str:
        return (
            f"{self.settings.base_url}/chart_data/"
            f"{filter_id}/{smard_region}/"
            f"{filter_id}_{smard_region}_{resolution}_{timestamp_ms}.json"
        )

    def request_json(self, url: str) -> Any:
        last_error: Exception | None = None

        for attempt in range(1, self.settings.retries + 1):
            try:
                LOGGER.info("GET %s [attempt %s/%s]", url, attempt, self.settings.retries)
                response = self.session.get(url, timeout=self.settings.timeout_seconds)
                response.raise_for_status()
                return response.json()

            except Exception as exc:
                last_error = exc
                LOGGER.warning("Request failed: %s", exc)

                if attempt < self.settings.retries:
                    time.sleep(self.settings.retry_sleep_seconds)

        raise RuntimeError(f"SMARD request failed after retries: {url}") from last_error

    def get_available_chunk_timestamps(
        self,
        filter_id: str,
        smard_region: str,
        resolution: str,
    ) -> list[int]:
        url = self.build_index_url(filter_id, smard_region, resolution)
        payload = self.request_json(url)
        timestamps = extract_timestamps(payload)

        if not timestamps:
            raise RuntimeError(
                f"No timestamps returned for filter={filter_id}, "
                f"region={smard_region}, resolution={resolution}"
            )

        return timestamps

    @staticmethod
    def select_chunk_timestamps(
        available_timestamps: list[int],
        start_ms: int,
        end_ms_exclusive: int,
    ) -> list[int]:
        selected = [ts for ts in available_timestamps if start_ms <= ts < end_ms_exclusive]

        previous_chunks = [ts for ts in available_timestamps if ts < start_ms]
        if previous_chunks:
            selected.insert(0, max(previous_chunks))

        if not selected:
            future_chunks = [ts for ts in available_timestamps if ts >= start_ms]
            if future_chunks:
                selected.append(min(future_chunks))

        return sorted(set(selected))

    def download_filter(
        self,
        *,
        filter_id: str,
        start: str,
        end: str,
        market_label: str,
        smard_region: str,
        resolution: str,
        output_root: str | Path = "data/raw/smard",
    ) -> dict[str, Any]:
        if filter_id not in self.settings.filters:
            known = ", ".join(sorted(self.settings.filters))
            raise ValueError(f"Unknown SMARD filter '{filter_id}'. Known filters: {known}")

        filter_meta = self.settings.filters[filter_id]
        output_root = Path(output_root)

        start_ms = local_date_to_epoch_ms(start, end_exclusive=False)
        end_ms_exclusive = local_date_to_epoch_ms(end, end_exclusive=True)

        available_timestamps = self.get_available_chunk_timestamps(
            filter_id=filter_id,
            smard_region=smard_region,
            resolution=resolution,
        )

        selected_chunk_timestamps = self.select_chunk_timestamps(
            available_timestamps=available_timestamps,
            start_ms=start_ms,
            end_ms_exclusive=end_ms_exclusive,
        )

        if not selected_chunk_timestamps:
            raise RuntimeError(
                f"No chunks selected for filter={filter_id}, start={start}, end={end}"
            )

        run_id = (
            f"{market_label}_{smard_region}_{resolution}_{filter_id}_{start}_to_{end}"
            .replace("/", "-")
        )

        manifest: dict[str, Any] = {
            "run_id": run_id,
            "source": self.settings.name,
            "attribution": self.settings.attribution,
            "license_note": self.settings.license_note,
            "retrieved_at_utc": utc_now_iso(),
            "market_label": market_label,
            "smard_region": smard_region,
            "resolution": resolution,
            "filter_id": filter_id,
            "filter_name": filter_meta.name,
            "unit": filter_meta.unit,
            "category": filter_meta.category,
            "requested_start_date": start,
            "requested_end_date": end,
            "requested_start_epoch_ms": start_ms,
            "requested_end_epoch_ms_exclusive": end_ms_exclusive,
            "selected_chunk_timestamps": selected_chunk_timestamps,
            "files": [],
        }

        for timestamp_ms in selected_chunk_timestamps:
            url = self.build_timeseries_url(
                filter_id=filter_id,
                smard_region=smard_region,
                resolution=resolution,
                timestamp_ms=timestamp_ms,
            )

            payload = self.request_json(url)

            raw_file = (
                output_root
                / filter_id
                / f"smard_{filter_id}_{smard_region}_{resolution}_{timestamp_ms}.json"
            )

            metadata_file = (
                output_root
                / filter_id
                / f"smard_{filter_id}_{smard_region}_{resolution}_{timestamp_ms}.metadata.json"
            )

            write_json(payload, raw_file)

            metadata = {
                "source": self.settings.name,
                "source_url": url,
                "retrieved_at_utc": utc_now_iso(),
                "market_label": market_label,
                "smard_region": smard_region,
                "unit": filter_meta.unit,
                "resolution": resolution,
                "filter_id": filter_id,
                "filter_name": filter_meta.name,
                "category": filter_meta.category,
                "chunk_timestamp_ms": timestamp_ms,
                "timezone_context": "Europe/Berlin",
                "canonical_timestamp_policy": "Convert source timestamps to UTC in staging layer.",
                "transformation_history": [
                    "Raw JSON downloaded from SMARD chart_data endpoint.",
                    "No cleaning or analytical transformation applied in raw layer.",
                ],
                "license_note": self.settings.license_note,
                "attribution": self.settings.attribution,
                "raw_file": str(raw_file.as_posix()),
                "series_point_count": count_series_points(payload),
            }

            metadata["file_hash_sha256"] = sha256_file(raw_file)
            write_json(metadata, metadata_file)

            manifest["files"].append(
                {
                    "chunk_timestamp_ms": timestamp_ms,
                    "source_url": url,
                    "raw_file": str(raw_file.as_posix()),
                    "metadata_file": str(metadata_file.as_posix()),
                    "series_point_count": metadata["series_point_count"],
                    "file_hash_sha256": metadata["file_hash_sha256"],
                }
            )

        manifest_file = output_root / filter_id / f"manifest_{run_id}.json"
        write_json(manifest, manifest_file)

        LOGGER.info("SMARD manifest written: %s", manifest_file)
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download raw SMARD data.")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--smard-region", default="DE")
    parser.add_argument("--resolution", default="hour")
    parser.add_argument("--filters", nargs="+", default=["410"])
    parser.add_argument("--config", default="src/config/sources.yaml")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    settings = load_smard_settings(args.config)
    client = SmardClient(settings)

    for filter_id in args.filters:
        manifest = client.download_filter(
            filter_id=str(filter_id),
            start=args.start,
            end=args.end,
            market_label=args.market_label,
            smard_region=args.smard_region,
            resolution=args.resolution,
        )

        print(
            f"OK | filter={filter_id} | files={len(manifest['files'])} | "
            f"run_id={manifest['run_id']}"
        )


if __name__ == "__main__":
    main()
