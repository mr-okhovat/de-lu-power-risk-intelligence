import pandas as pd

from src.prices.price_table import check_quality, chunk_candidates, local_window, rows_from_series


def test_rows_from_series() -> None:
    payload = {"series": [[1717200000000, 50.5], [1717203600000, None]]}
    rows = rows_from_series(payload)

    assert len(rows) == 2
    assert rows[0]["price_eur_per_mwh"] == 50.5
    assert rows[1]["price_eur_per_mwh"] is None


def test_local_window_has_expected_hours_for_june_2024() -> None:
    start, end = local_window("2024-06-01", "2024-06-30")

    assert int((end - start) / pd.Timedelta(hours=1)) == 720


def test_chunk_candidates_uses_lookback() -> None:
    start, end = local_window("2024-06-01", "2024-06-30")
    timestamps = [
        int((start - pd.Timedelta(days=20)).timestamp() * 1000),
        int((start - pd.Timedelta(days=7)).timestamp() * 1000),
        int((end + pd.Timedelta(days=1)).timestamp() * 1000),
    ]

    out = chunk_candidates(timestamps, start, end)

    assert len(out) == 1


def test_check_quality_passes() -> None:
    start, end = local_window("2024-06-01", "2024-06-01")
    timestamps = pd.date_range(start=start, end=end - pd.Timedelta(hours=1), freq="h")

    df = pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "price_eur_per_mwh": [10.0] * len(timestamps),
        }
    )

    quality = check_quality(df, start="2024-06-01", end="2024-06-01", filter_id="4169", region="DE-LU")

    assert quality.status == "PASS"
    assert quality.row_count == 24
