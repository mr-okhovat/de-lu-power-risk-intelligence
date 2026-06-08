from pathlib import Path

import pandas as pd
import pytest

from src.core.run_selector import build, metrics, select_runs


def sample_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "run_id": ["DE-LU_2024-05", "DE-LU_2024-06", "FR_2024-06"],
            "market": ["DE-LU", "DE-LU", "FR"],
            "start": ["2024-05-01", "2024-06-01", "2024-06-01"],
            "end": ["2024-05-31", "2024-06-30", "2024-06-30"],
            "run_status": ["READY", "READY", "CHECK NEEDED"],
            "source_rows": [744, 720, 720],
            "same_hour_event_lift": [2.0, 1.5, 0.5],
            "window_next_3h_event_lift": [1.4, 1.2, 0.8],
            "evaluation_file": ["may.csv", "jun.csv", "fr.csv"],
            "behavior_report": ["may.md", "jun.md", "fr.md"],
        }
    )


def test_select_runs_defaults_to_ready_only() -> None:
    selected = select_runs(sample_catalog())

    assert list(selected["run_id"]) == ["DE-LU_2024-05", "DE-LU_2024-06"]
    assert set(selected["run_status"]) == {"READY"}


def test_select_runs_filters_market_and_period() -> None:
    selected = select_runs(
        sample_catalog(),
        market="DE-LU",
        start="2024-06-01",
        end="2024-06-30",
    )

    assert len(selected) == 1
    assert selected.iloc[0]["run_id"] == "DE-LU_2024-06"


def test_metrics_summarises_selected_runs() -> None:
    selected = select_runs(sample_catalog())
    result = metrics(selected)

    assert result["selected_runs"] == 2
    assert result["markets"] == 1
    assert result["period_start"] == "2024-05-01"
    assert result["period_end"] == "2024-06-30"
    assert result["mean_same_hour_lift"] == pytest.approx(1.75)
    assert result["mean_next_3h_window_lift"] == pytest.approx(1.3)


def test_build_writes_selection_artifacts(tmp_path: Path) -> None:
    catalog_csv = tmp_path / "catalog.csv"
    output_csv = tmp_path / "active.csv"
    output_report = tmp_path / "active.md"
    output_json = tmp_path / "active.json"

    sample_catalog().to_csv(catalog_csv, index=False)

    build(
        catalog_csv=str(catalog_csv),
        output_csv=str(output_csv),
        output_report=str(output_report),
        output_json=str(output_json),
        market="DE-LU",
        start=None,
        end=None,
        ready_only=True,
    )

    assert output_csv.exists()
    assert output_report.exists()
    assert output_json.exists()

    selected = pd.read_csv(output_csv)
    assert len(selected) == 2
    assert "# Active run selection" in output_report.read_text(encoding="utf-8")
