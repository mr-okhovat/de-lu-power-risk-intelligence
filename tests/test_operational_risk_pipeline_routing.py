from argparse import Namespace

import run_pipeline


def base_args(**overrides) -> Namespace:
    values = {
        "start": "2024-08-01",
        "end": "2024-08-31",
        "market_label": "DE-LU",
        "smard_region": "DE",
        "phase": "",
        "risk_output": None,
        "operational_risk_output": None,
        "operational_risk_report_output": None,
        "operational_risk_json_output": None,
        "operational_state_distribution_output": None,
        "operational_attention_distribution_output": None,
        "operational_dominant_driver_output": None,
        "operational_driver_count_output": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_build_operational_risk_route_uses_default_paths(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(run_pipeline, "setup_logging", lambda: None)
    monkeypatch.setattr(
        run_pipeline,
        "parse_args",
        lambda: base_args(phase="build-operational-risk"),
    )

    def fake_build_operational_risk_table(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        run_pipeline,
        "build_operational_risk_table",
        fake_build_operational_risk_table,
    )

    run_pipeline.main()

    assert captured == {
        "input_file": (
            "data/processed/"
            "risk_signals_DE-LU_2024-08-01_to_2024-08-31.csv"
        ),
        "output_file": (
            "data/processed/"
            "operational_risk_DE-LU_2024-08-01_to_2024-08-31.csv"
        ),
    }


def test_operational_diagnostics_route_uses_explicit_paths(
    monkeypatch,
    tmp_path,
) -> None:
    captured = {}

    paths = {
        "operational_risk_output": str(tmp_path / "operational.csv"),
        "operational_risk_report_output": str(tmp_path / "report.md"),
        "operational_risk_json_output": str(tmp_path / "report.json"),
        "operational_state_distribution_output": str(tmp_path / "states.csv"),
        "operational_attention_distribution_output": str(
            tmp_path / "attention.csv"
        ),
        "operational_dominant_driver_output": str(tmp_path / "drivers.csv"),
        "operational_driver_count_output": str(
            tmp_path / "driver_counts.csv"
        ),
    }

    monkeypatch.setattr(run_pipeline, "setup_logging", lambda: None)
    monkeypatch.setattr(
        run_pipeline,
        "parse_args",
        lambda: base_args(
            phase="build-operational-risk-diagnostics",
            **paths,
        ),
    )

    def fake_build_operational_risk_diagnostics(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        run_pipeline,
        "build_operational_risk_diagnostics",
        fake_build_operational_risk_diagnostics,
    )

    run_pipeline.main()

    assert captured == {
        "input_file": paths["operational_risk_output"],
        "output_report": paths["operational_risk_report_output"],
        "output_json": paths["operational_risk_json_output"],
        "state_distribution_output": (
            paths["operational_state_distribution_output"]
        ),
        "attention_distribution_output": (
            paths["operational_attention_distribution_output"]
        ),
        "dominant_driver_output": (
            paths["operational_dominant_driver_output"]
        ),
        "driver_count_output": paths["operational_driver_count_output"],
    }
