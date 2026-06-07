import pandas as pd

from src.core.run_catalog import (
    add_run_status,
    build_base_catalog,
    enrich_with_lead_time,
    enrich_with_same_hour,
    metrics,
    month_key,
)


def availability() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dataset_id": ["signal_price_evaluation_2024_06"],
            "market": ["DE-LU"],
            "start": ["2024-06-01"],
            "end": ["2024-06-30"],
            "registered": [True],
            "analytics_ready": [True],
            "intake_status": ["PASS"],
            "source_rows": [720],
            "adapted_rows": [720],
            "intake_row_count": [720],
            "source_file": ["data/processed/demo.csv"],
            "adapted_file": ["data/adapted/demo.csv"],
            "contract_report": ["reports/contract.md"],
        }
    )


def test_month_key() -> None:
    assert month_key("2024-06-01", "2024-06-30") == "2024-06-01_to_2024-06-30"


def test_build_base_catalog() -> None:
    out = build_base_catalog(availability())

    assert len(out) == 1
    assert out.iloc[0]["run_id"] == "DE-LU_2024-06-01_to_2024-06-30"


def test_enrich_with_same_hour() -> None:
    catalog = build_base_catalog(availability())
    cross = pd.DataFrame(
        {
            "start": ["2024-06-01"],
            "end": ["2024-06-30"],
            "precision": [0.5],
            "recall": [0.1],
            "event_lift": [2.0],
            "signal_rows": [7],
            "price_event_rows": [181],
            "tp": [4],
            "fp": [3],
            "fn": [177],
        }
    )

    out = enrich_with_same_hour(catalog, cross)

    assert out.iloc[0]["same_hour_event_lift"] == 2.0


def test_enrich_with_lead_time() -> None:
    catalog = build_base_catalog(availability())
    lead = pd.DataFrame(
        {
            "start": ["2024-06-01", "2024-06-01"],
            "end": ["2024-06-30", "2024-06-30"],
            "mode": ["exact_hour", "future_window"],
            "horizon_hours": [1, 3],
            "precision": [0.6, 0.5],
            "recall": [0.03, 0.02],
            "event_lift": [2.3, 1.5],
        }
    )

    out = enrich_with_lead_time(catalog, lead)

    assert out.iloc[0]["exact_next_1h_event_lift"] == 2.3
    assert out.iloc[0]["window_next_3h_event_lift"] == 1.5


def test_add_run_status() -> None:
    catalog = build_base_catalog(availability())
    catalog["evaluation_file_exists"] = True
    catalog["adapted_file_exists"] = True
    catalog["contract_report_exists"] = True
    catalog["analytics_ready"] = True

    out = add_run_status(catalog)

    assert out.iloc[0]["run_status"] == "READY"


def test_metrics() -> None:
    catalog = pd.DataFrame(
        {
            "run_status": ["READY", "CHECK NEEDED"],
            "market": ["DE-LU", "DE-LU"],
            "start": ["2024-05-01", "2024-06-01"],
            "end": ["2024-05-31", "2024-06-30"],
            "same_hour_event_lift": [2.0, 1.5],
            "window_next_3h_event_lift": [1.2, 1.4],
        }
    )

    out = metrics(catalog)

    assert out["runs"] == 2
    assert out["ready_runs"] == 1
    assert out["check_needed_runs"] == 1
    assert out["mean_same_hour_lift"] == 1.75
