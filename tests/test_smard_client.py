from pathlib import Path

from src.data_ingestion.smard_client import (
    SmardClient,
    SmardFilter,
    SmardSettings,
    extract_timestamps,
    local_date_to_epoch_ms,
    sha256_file,
)


def make_settings() -> SmardSettings:
    return SmardSettings(
        name="SMARD / Bundesnetzagentur",
        base_url="https://www.smard.de/app",
        default_smard_region="DE",
        default_market_label="DE-LU",
        default_resolution="hour",
        timeout_seconds=60,
        retries=3,
        retry_sleep_seconds=1,
        attribution="Bundesnetzagentur | SMARD.de",
        license_note="CC BY 4.0 where applicable.",
        filters={
            "410": SmardFilter(
                filter_id="410",
                name="Total Load",
                unit="MW",
                category="consumption",
            )
        },
    )


def test_index_url_builder() -> None:
    client = SmardClient(make_settings())

    url = client.build_index_url(
        filter_id="410",
        smard_region="DE",
        resolution="hour",
    )

    assert url == "https://www.smard.de/app/chart_data/410/DE/index_hour.json"


def test_timeseries_url_builder() -> None:
    client = SmardClient(make_settings())

    url = client.build_timeseries_url(
        filter_id="410",
        smard_region="DE",
        resolution="hour",
        timestamp_ms=1717192800000,
    )

    assert (
        url
        == "https://www.smard.de/app/chart_data/410/DE/410_DE_hour_1717192800000.json"
    )


def test_extract_timestamps_from_dict() -> None:
    payload = {"timestamps": [3000, 1000, 2000, 2000]}

    assert extract_timestamps(payload) == [1000, 2000, 3000]


def test_extract_timestamps_from_list() -> None:
    payload = [3000, 1000, 2000, 2000]

    assert extract_timestamps(payload) == [1000, 2000, 3000]


def test_select_chunk_timestamps_includes_previous_chunk() -> None:
    available = [1000, 2000, 3000, 4000, 5000]

    selected = SmardClient.select_chunk_timestamps(
        available_timestamps=available,
        start_ms=2500,
        end_ms_exclusive=4500,
    )

    assert selected == [2000, 3000, 4000]


def test_local_date_to_epoch_ms_returns_int() -> None:
    value = local_date_to_epoch_ms("2024-06-01")

    assert isinstance(value, int)
    assert value > 0


def test_sha256_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("abc", encoding="utf-8")

    assert (
        sha256_file(file_path)
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
