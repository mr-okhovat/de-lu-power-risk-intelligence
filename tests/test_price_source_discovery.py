from src.data_ingestion.price_source_discovery import (
    ProbeResult,
    choose,
    extract_numeric_values,
    extract_timestamps,
)


def test_extract_timestamps_from_index_payload() -> None:
    assert extract_timestamps({"timestamps": [1, 2, 3]}) == [1, 2, 3]


def test_extract_timestamps_from_series_payload() -> None:
    assert extract_timestamps({"series": [[10, 1.5], [20, 2.5]]}) == [10, 20]


def test_extract_numeric_values() -> None:
    payload = {"series": [[1, 10.5], [2, None], [3, -5]]}

    assert extract_numeric_values(payload) == [10.5, -5.0]


def test_choose_prefers_first_passing_region_order() -> None:
    failed = ProbeResult("x", "bad", "DE-LU", "hour", "u", None, "FAIL", 0, 0, 0, None, None, "bad")
    passing = ProbeResult("4169", "price", "DE", "hour", "u", "s", "PASS", 1, 1, 1, 1.0, 2.0, None)

    assert choose([failed, passing]) == passing
