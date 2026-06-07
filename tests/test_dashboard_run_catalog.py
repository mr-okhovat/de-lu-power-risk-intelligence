import pandas as pd

from app.streamlit_app import (
    run_catalog_core_table,
    run_catalog_lift_frame,
    run_catalog_metrics,
)


def make_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "run_id": ["DE-LU_2024-05", "DE-LU_2024-06"],
            "market": ["DE-LU", "DE-LU"],
            "start": ["2024-05-01", "2024-06-01"],
            "end": ["2024-05-31", "2024-06-30"],
            "run_status": ["READY", "CHECK NEEDED"],
            "source_rows": [744, 720],
            "same_hour_event_lift": [2.0, 1.5],
            "exact_next_1h_event_lift": [2.2, 2.1],
            "window_next_3h_event_lift": [1.4, 1.3],
            "window_next_6h_event_lift": [1.1, 1.0],
            "evaluation_file": ["a.csv", "b.csv"],
            "behavior_report": ["a.md", "b.md"],
        }
    )


def test_run_catalog_metrics() -> None:
    out = run_catalog_metrics(make_catalog())

    assert out["runs"] == 2
    assert out["ready_runs"] == 1
    assert out["check_needed_runs"] == 1
    assert out["markets"] == 1
    assert out["mean_same_hour_lift"] == 1.75


def test_run_catalog_core_table() -> None:
    out = run_catalog_core_table(make_catalog())

    assert "run_id" in out.columns
    assert "same_hour_event_lift" in out.columns


def test_run_catalog_lift_frame() -> None:
    out = run_catalog_lift_frame(make_catalog())

    assert "same_hour_event_lift" in out.columns
    assert out.index.name == "run_id"
