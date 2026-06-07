import pytest

from src.config.load_series_registry import (
    SeriesDefinition,
    get_final_feature_series,
    get_staging_series,
    load_series_registry,
    validate_series_registry,
)


def test_series_registry_loads() -> None:
    series = load_series_registry()

    assert len(series) >= 5
    assert {item.filter_id for item in series} >= {"410", "4359", "4067", "4068", "1225"}


def test_series_registry_has_unique_filter_ids() -> None:
    series = load_series_registry()
    filter_ids = [item.filter_id for item in series]

    assert len(filter_ids) == len(set(filter_ids))


def test_final_feature_series_are_semantically_locked() -> None:
    series = load_series_registry()
    final_series = get_final_feature_series(series)

    assert final_series

    for item in final_series:
        assert item.semantic_status == "endpoint_verified_semantics_locked"


def test_provisional_series_not_allowed_for_final_features() -> None:
    series = load_series_registry()
    provisional = [
        item for item in series
        if item.semantic_status == "endpoint_verified_semantics_provisional"
    ]

    assert provisional

    for item in provisional:
        assert item.allowed_for_final_features is False


def test_staging_series_exist() -> None:
    series = load_series_registry()
    staging_series = get_staging_series(series)

    assert len(staging_series) >= 5


def test_registry_rejects_duplicate_filter_ids() -> None:
    duplicate = SeriesDefinition(
        filter_id="410",
        internal_name="x",
        display_name="X",
        source="SMARD",
        source_region_field="smard_region",
        default_smard_region="DE",
        market_label="DE-LU",
        unit="MW",
        category="test",
        semantic_status="endpoint_verified_semantics_locked",
        allowed_for_staging=True,
        allowed_for_final_features=True,
        expected_direction="positive",
        notes="test",
    )

    with pytest.raises(ValueError, match="Duplicate filter_id"):
        validate_series_registry([duplicate, duplicate])


def test_registry_rejects_provisional_final_feature_series() -> None:
    invalid = SeriesDefinition(
        filter_id="9999",
        internal_name="invalid",
        display_name="Invalid",
        source="SMARD",
        source_region_field="smard_region",
        default_smard_region="DE",
        market_label="DE-LU",
        unit="MW",
        category="test",
        semantic_status="endpoint_verified_semantics_provisional",
        allowed_for_staging=True,
        allowed_for_final_features=True,
        expected_direction="positive",
        notes="invalid",
    )

    with pytest.raises(ValueError, match="cannot be allowed for final features"):
        validate_series_registry([invalid])
