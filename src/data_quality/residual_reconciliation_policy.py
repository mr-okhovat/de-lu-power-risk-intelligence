from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml


DEFAULT_EXCEPTION_REGISTRY_PATH = Path(
    "src/config/residual_reconciliation_exceptions.yaml"
)


@dataclass(frozen=True)
class ResidualExceptionPolicyMatch:
    registry_path: str
    policy_id: str | None
    registry_loaded: bool
    materiality_threshold_mw: float | None
    match_tolerance_mw: float | None
    observed_material_exception_count: int
    expected_exception_count_in_window: int
    unexpected_timestamp_count: int
    signed_error_mismatch_count: int
    missing_documented_exception_count: int
    duplicate_observed_timestamp_count: int
    pass_check: bool
    note: str


def _empty_result(
    *,
    registry_path: Path,
    note: str,
    observed_material_exception_count: int = 0,
    pass_check: bool = False,
) -> ResidualExceptionPolicyMatch:
    return ResidualExceptionPolicyMatch(
        registry_path=str(registry_path.as_posix()),
        policy_id=None,
        registry_loaded=False,
        materiality_threshold_mw=None,
        match_tolerance_mw=None,
        observed_material_exception_count=observed_material_exception_count,
        expected_exception_count_in_window=0,
        unexpected_timestamp_count=0,
        signed_error_mismatch_count=0,
        missing_documented_exception_count=0,
        duplicate_observed_timestamp_count=0,
        pass_check=pass_check,
        note=note,
    )


def _load_registry(path: Path) -> tuple[dict[str, object], pd.DataFrame]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Residual exception registry must be a YAML object.")

    required_fields = {
        "policy_id",
        "materiality_threshold_mw",
        "match_tolerance_mw",
        "exceptions",
    }
    missing_fields = sorted(required_fields - set(payload))

    if missing_fields:
        raise ValueError(
            "Residual exception registry is missing fields: "
            f"{missing_fields}"
        )

    raw_exceptions = payload["exceptions"]

    if not isinstance(raw_exceptions, list):
        raise ValueError("Residual exception registry field 'exceptions' must be a list.")

    rows: list[dict[str, object]] = []

    for item in raw_exceptions:
        if not isinstance(item, dict):
            raise ValueError("Each residual exception registry entry must be an object.")

        if "timestamp_utc" not in item or "expected_signed_error_mw" not in item:
            raise ValueError(
                "Each residual exception entry requires timestamp_utc and "
                "expected_signed_error_mw."
            )

        rows.append(
            {
                "timestamp_utc": pd.to_datetime(item["timestamp_utc"], utc=True),
                "expected_signed_error_mw": float(item["expected_signed_error_mw"]),
            }
        )

    exceptions = pd.DataFrame(
        rows,
        columns=["timestamp_utc", "expected_signed_error_mw"],
    )

    if exceptions["timestamp_utc"].duplicated().any():
        duplicates = exceptions.loc[
            exceptions["timestamp_utc"].duplicated(keep=False),
            "timestamp_utc",
        ].astype(str).tolist()
        raise ValueError(
            "Residual exception registry contains duplicate timestamps: "
            f"{duplicates}"
        )

    return payload, exceptions.sort_values("timestamp_utc").reset_index(drop=True)


def match_documented_residual_exceptions(
    timestamps_utc: Iterable[object],
    signed_errors_mw: Iterable[object],
    *,
    registry_path: str | Path = DEFAULT_EXCEPTION_REGISTRY_PATH,
) -> ResidualExceptionPolicyMatch:
    """
    Match material residual reconciliation deviations against a versioned registry.

    Signed-error convention:
        recomputed_residual_mw - residual_load_official_mw
    """
    registry_path = Path(registry_path)

    observed = pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(
                list(timestamps_utc),
                utc=True,
                errors="coerce",
            ),
            "signed_error_mw": pd.to_numeric(
                pd.Series(list(signed_errors_mw)),
                errors="coerce",
            ),
        }
    )

    invalid_observed_rows = int(
        observed["timestamp_utc"].isna().sum()
        + observed["signed_error_mw"].isna().sum()
    )

    if invalid_observed_rows > 0:
        return _empty_result(
            registry_path=registry_path,
            note=(
                "Residual exception policy could not evaluate invalid timestamp "
                "or signed-error values."
            ),
        )

    if observed.empty:
        return _empty_result(
            registry_path=registry_path,
            note="Residual exception policy received no observations.",
        )

    if not registry_path.exists():
        return _empty_result(
            registry_path=registry_path,
            note=(
                "Residual exception registry is missing. Material reconciliation "
                "deviations cannot be documented."
            ),
        )

    try:
        registry, expected = _load_registry(registry_path)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        return _empty_result(
            registry_path=registry_path,
            note=f"Residual exception registry could not be loaded: {exc}",
        )

    threshold = float(registry["materiality_threshold_mw"])
    match_tolerance = float(registry["match_tolerance_mw"])
    policy_id = str(registry["policy_id"])

    observed_material = observed[
        observed["signed_error_mw"].abs() > threshold
    ].copy()

    # Registry scope is determined by the evaluated timestamp window,
    # not by whether the current observations happen to be material.
    start = observed["timestamp_utc"].min()
    end = observed["timestamp_utc"].max()

    expected_in_window = expected[
        (expected["timestamp_utc"] >= start)
        & (expected["timestamp_utc"] <= end)
    ].copy()

    duplicate_observed_timestamp_count = int(
        observed_material["timestamp_utc"].duplicated().sum()
    )

    observed_by_timestamp = (
        observed_material
        .sort_values("timestamp_utc")
        .drop_duplicates("timestamp_utc", keep="last")
        .set_index("timestamp_utc")["signed_error_mw"]
        .to_dict()
    )

    expected_by_timestamp = (
        expected_in_window
        .set_index("timestamp_utc")["expected_signed_error_mw"]
        .to_dict()
    )

    observed_timestamps = set(observed_by_timestamp)
    expected_timestamps = set(expected_by_timestamp)

    unexpected_timestamps = observed_timestamps - expected_timestamps
    missing_documented_timestamps = expected_timestamps - observed_timestamps
    shared_timestamps = observed_timestamps & expected_timestamps

    signed_error_mismatch_count = sum(
        abs(
            float(observed_by_timestamp[timestamp])
            - float(expected_by_timestamp[timestamp])
        )
        > match_tolerance
        for timestamp in shared_timestamps
    )

    pass_check = bool(
        duplicate_observed_timestamp_count == 0
        and len(unexpected_timestamps) == 0
        and len(missing_documented_timestamps) == 0
        and signed_error_mismatch_count == 0
    )

    if pass_check and len(observed_material) == 0:
        note = (
            "No material residual reconciliation deviations were observed in "
            "the evaluated window."
        )
    elif pass_check:
        note = (
            "Material residual reconciliation deviations exactly match the "
            "documented endpoint exception profile."
        )
    else:
        note = (
            "Material residual reconciliation deviations do not match the "
            "documented endpoint exception profile."
        )

    return ResidualExceptionPolicyMatch(
        registry_path=str(registry_path.as_posix()),
        policy_id=policy_id,
        registry_loaded=True,
        materiality_threshold_mw=threshold,
        match_tolerance_mw=match_tolerance,
        observed_material_exception_count=int(len(observed_material)),
        expected_exception_count_in_window=int(len(expected_in_window)),
        unexpected_timestamp_count=int(len(unexpected_timestamps)),
        signed_error_mismatch_count=int(signed_error_mismatch_count),
        missing_documented_exception_count=int(
            len(missing_documented_timestamps)
        ),
        duplicate_observed_timestamp_count=duplicate_observed_timestamp_count,
        pass_check=pass_check,
        note=note,
    )
