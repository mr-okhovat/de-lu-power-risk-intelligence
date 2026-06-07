import pandas as pd

from src.core.data_availability_index import (
    attach_intake_status,
    metrics,
    parse_signal_file,
)
from pathlib import Path


def test_parse_signal_file() -> None:
    parsed = parse_signal_file(
        Path("signal_price_evaluation_DE-LU_2024-06-01_to_2024-06-30.csv"),
        adapted=False,
    )

    assert parsed == {
        "market": "DE-LU",
        "start": "2024-06-01",
        "end": "2024-06-30",
    }


def test_attach_intake_status() -> None:
    index = pd.DataFrame(
        {
            "dataset_id": ["a"],
            "registered": [True],
            "source_exists": [True],
            "adapted_exists": [True],
            "contract_report_exists": [True],
        }
    )

    intake = pd.DataFrame(
        {
            "dataset_id": ["a"],
            "status": ["PASS"],
            "row_count": [10],
        }
    )

    out = attach_intake_status(index, intake)

    assert out.iloc[0]["intake_status"] == "PASS"
    assert out.iloc[0]["analytics_ready"] is True or bool(out.iloc[0]["analytics_ready"]) is True


def test_metrics() -> None:
    df = pd.DataFrame(
        {
            "registered": [True, False],
            "analytics_ready": [True, False],
            "market": ["DE-LU", "DE-LU"],
            "start": ["2024-06-01", "2024-07-01"],
            "end": ["2024-06-30", "2024-07-31"],
        }
    )

    out = metrics(df)

    assert out["datasets"] == 2
    assert out["registered"] == 1
    assert out["unregistered"] == 1
    assert out["analytics_ready"] == 1
    assert out["period_start"] == "2024-06-01"
    assert out["period_end"] == "2024-07-31"
