from src.orchestration.pipeline_steps import build_pipeline_steps, load_pipeline_config, output_paths


def test_load_pipeline_config() -> None:
    config = load_pipeline_config("config/pipeline_sample.yaml")

    assert config.market_label == "DE-LU"
    assert config.smard_region == "DE"
    assert "410" in config.filters
    assert config.include_reviewer_pack is True
    assert config.include_event_study is False
    assert config.include_signal_event_evaluation is False


def test_output_paths() -> None:
    config = load_pipeline_config("config/pipeline_sample.yaml")
    paths = output_paths(config)

    assert paths["staging"].endswith("clean_hourly_DE-LU_2024-06-01_to_2024-06-03.csv")
    assert paths["risk_signals"].endswith("risk_signals_DE-LU_2024-06-01_to_2024-06-03.csv")
    assert paths["reviewer_pack"].endswith("reviewer_pack_2024-06-01_to_2024-06-03.md")


def test_pipeline_has_current_steps() -> None:
    config = load_pipeline_config("config/pipeline_sample.yaml")
    names = [step.name for step in build_pipeline_steps(config)]

    assert "smard_ingestion" in names
    assert "build_staging" in names
    assert "build_features" in names
    assert "build_dashboard_exports" in names
    assert "build_risk_signals" in names
    assert "build_risk_diagnostics" in names
    assert "build_reviewer_pack" in names


def test_pipeline_excludes_future_backtest_steps() -> None:
    config = load_pipeline_config("config/pipeline_sample.yaml")
    names = [step.name for step in build_pipeline_steps(config)]

    assert "build_event_study_skeleton" not in names
    assert "build_signal_event_evaluation" not in names
