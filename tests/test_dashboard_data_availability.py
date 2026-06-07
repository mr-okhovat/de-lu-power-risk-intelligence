import pandas as pd

from app.streamlit_app import (
    data_availability_core_table,
    data_availability_metrics,
    data_availability_status_counts,
)


def make_index() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dataset_id": ["a", "b"],
            "market": ["DE-LU", "DE-LU"],
            "start": ["2024-05-01", "2024-06-01"],
            "end": ["2024-05-31", "2024-06-30"],
            "registered": [True, True],
            "analytics_ready": [True, False],
            "intake_status": ["PASS", "CHECK NEEDED"],
            "source_rows": [744, 720],
            "adapted_rows": [744, 720],
            "source_file": ["a.csv", "b.csv"],
            "adapted_file": ["aa.csv", "bb.csv"],
        }
    )


def test_data_availability_metrics() -> None:
    out = data_availability_metrics(make_index())

    assert out["datasets"] == 2
    assert out["registered"] == 2
    assert out["analytics_ready"] == 1
    assert out["markets"] == 1
    assert out["period"] == "2024-05-01 to 2024-06-30"


def test_data_availability_status_counts() -> None:
    out = data_availability_status_counts(make_index())

    assert set(out["status"]) == {"analytics_ready", "not_ready"}


def test_data_availability_core_table() -> None:
    out = data_availability_core_table(make_index())

    assert "dataset_id" in out.columns
    assert "analytics_ready" in out.columns
