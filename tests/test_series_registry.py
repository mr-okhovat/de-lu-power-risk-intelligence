import pytest

from src.config.load_series_registry import (
    SeriesDefinition,
    get_final_feature_series,
    get_staging_series,
    load_series_registry,
    validate_series_registry,
)


def make_series(
    *,
    filter_id: str = "9999",
    internal_name: str = "test_series",
    semantic_status: str = "endpoint_verified_semantics_locked",
    validation_status: str = "source_endpoint_and_staging_validated",
    allowed_for_final_features: bool = True,
) -> SeriesDefinition:
    return SeriesDefinition(
        filter_id=filter_id,
        internal_name=internal_name,
        display_name="Test Series",
        source="SMARD",
        source_region_field="smard_region",
        default_smard_region="DE",
        market_label="DE-LU",
        unit="MW",
        category="test",
        semantic_status=semantic_status,
        validation_status=validation_status,
        allowed_for_staging=True,
        allowed_for_final_features=allowed_for_final_features,
        expected_direction="positive",
        notes="test",
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

    assert len(final_series) >= 5

    for item in final_series:
        assert item.semantic_status == "endpoint_verified_semantics_locked"
        assert item.validation_status != "not_yet_validated"


def test_no_provisional_series_allowed_for_final_features() -> None:
    series = load_series_registry()
    provisional = [
        item for item in series
        if item.semantic_status == "endpoint_verified_semantics_provisional"
    ]

    for item in provisional:
        assert item.allowed_for_final_features is False


def test_staging_series_exist() -> None:
    series = load_series_registry()
    staging_series = get_staging_series(series)

    assert len(staging_series) >= 5


def test_registry_rejects_duplicate_filter_ids() -> None:
    first = make_series(filter_id="410", internal_name="x")
    second = make_series(filter_id="410", internal_name="y")

    with pytest.raises(ValueError, match="Duplicate filter_id"):
        validate_series_registry([first, second])


def test_registry_rejects_provisional_final_feature_series() -> None:
    invalid = make_series(
        semantic_status="endpoint_verified_semantics_provisional",
        validation_status="validated_by_residual_load_reconciliation",
        allowed_for_final_features=True,
    )

    with pytest.raises(ValueError, match="cannot be allowed for final features"):
        validate_series_registry([invalid])


def test_registry_rejects_unvalidated_final_feature_series() -> None:
    invalid = make_series(
        semantic_status="endpoint_verified_semantics_locked",
        validation_status="not_yet_validated",
        allowed_for_final_features=True,
    )

    with pytest.raises(ValueError, match="not_yet_validated"):
        validate_series_registry([invalid])
