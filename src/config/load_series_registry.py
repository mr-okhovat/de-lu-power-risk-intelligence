from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


VALID_SEMANTIC_STATUSES = {
    "endpoint_verified_semantics_locked",
    "endpoint_verified_semantics_provisional",
    "not_verified",
    "deprecated",
}

VALID_VALIDATION_STATUSES = {
    "source_endpoint_and_staging_validated",
    "validated_by_residual_load_reconciliation",
    "not_yet_validated",
}


@dataclass(frozen=True)
class SeriesDefinition:
    filter_id: str
    internal_name: str
    display_name: str
    source: str
    source_region_field: str
    default_smard_region: str
    market_label: str
    unit: str
    category: str
    semantic_status: str
    validation_status: str
    allowed_for_staging: bool
    allowed_for_final_features: bool
    expected_direction: str
    notes: str


def load_series_registry(
    path: str | Path = "src/config/series_registry.yaml",
) -> list[SeriesDefinition]:
    registry_path = Path(path)

    if not registry_path.exists():
        raise FileNotFoundError(f"Series registry not found: {registry_path}")

    with registry_path.open("r", encoding="utf-8") as f:
        payload: dict[str, Any] = yaml.safe_load(f)

    raw_series = payload.get("series")

    if not isinstance(raw_series, list) or not raw_series:
        raise ValueError("Series registry must contain a non-empty 'series' list.")

    series = [SeriesDefinition(**item) for item in raw_series]
    validate_series_registry(series)

    return series


def validate_series_registry(series: list[SeriesDefinition]) -> None:
    filter_ids = [item.filter_id for item in series]
    internal_names = [item.internal_name for item in series]

    if len(filter_ids) != len(set(filter_ids)):
        raise ValueError("Duplicate filter_id found in series registry.")

    if len(internal_names) != len(set(internal_names)):
        raise ValueError("Duplicate internal_name found in series registry.")

    for item in series:
        if item.semantic_status not in VALID_SEMANTIC_STATUSES:
            raise ValueError(
                f"Invalid semantic_status for {item.filter_id}: {item.semantic_status}"
            )

        if item.validation_status not in VALID_VALIDATION_STATUSES:
            raise ValueError(
                f"Invalid validation_status for {item.filter_id}: {item.validation_status}"
            )

        if not item.unit:
            raise ValueError(f"Missing unit for {item.filter_id}")

        if item.allowed_for_final_features:
            if item.semantic_status != "endpoint_verified_semantics_locked":
                raise ValueError(
                    f"Series {item.filter_id} cannot be allowed for final features "
                    f"unless semantic_status is endpoint_verified_semantics_locked."
                )

            if item.validation_status == "not_yet_validated":
                raise ValueError(
                    f"Series {item.filter_id} cannot be allowed for final features "
                    f"while validation_status is not_yet_validated."
                )


def get_staging_series(series: list[SeriesDefinition]) -> list[SeriesDefinition]:
    return [item for item in series if item.allowed_for_staging]


def get_final_feature_series(series: list[SeriesDefinition]) -> list[SeriesDefinition]:
    return [item for item in series if item.allowed_for_final_features]
