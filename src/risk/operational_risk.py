from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


OPERATIONAL_RISK_SCHEMA_VERSION = "1.0"

REQUIRED_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "risk_score",
    "regime_label",
    "reason_codes",
    "risk_schema_version",
]

OUTPUT_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "risk_score",
    "regime_label",
    "operational_state",
    "attention_level",
    "recommended_action",
    "risk_driver_count",
    "dominant_driver",
    "reason_codes",
    "risk_schema_version",
    "operational_risk_schema_version",
]

DRIVER_PRIORITY = [
    "HIGH_RESIDUAL_LOAD",
    "LOW_RENEWABLE_SHARE",
    "HIGH_RESIDUAL_LOAD_RAMP",
    "HIGH_LOAD_RAMP",
    "HIGH_RENEWABLE_GENERATION_RAMP",
]


def split_reason_codes(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []

    return [
        code.strip()
        for code in str(value).split("|")
        if code.strip() and code.strip() != "NO_RULE_TRIGGERED"
    ]


def operational_state_from_regime(regime: str) -> str:
    mapping = {
        "NORMAL": "STABLE",
        "WATCH": "HEIGHTENED",
        "STRESSED": "CONSTRAINED",
        "EXTREME": "CRITICAL",
    }

    try:
        return mapping[regime]
    except KeyError as exc:
        raise ValueError(f"Unsupported regime label: {regime}") from exc


def attention_level_from_regime(regime: str) -> str:
    mapping = {
        "NORMAL": "ROUTINE",
        "WATCH": "MONITOR",
        "STRESSED": "ACTIVE",
        "EXTREME": "IMMEDIATE",
    }

    try:
        return mapping[regime]
    except KeyError as exc:
        raise ValueError(f"Unsupported regime label: {regime}") from exc


def recommended_action_from_regime(regime: str) -> str:
    mapping = {
        "NORMAL": "STANDARD_MONITORING",
        "WATCH": "INCREASE_MONITORING_FREQUENCY",
        "STRESSED": "REVIEW_EXPOSURE_AND_FLEXIBILITY",
        "EXTREME": "ESCALATE_AND_ASSESS_IMMEDIATE_MITIGATION",
    }

    try:
        return mapping[regime]
    except KeyError as exc:
        raise ValueError(f"Unsupported regime label: {regime}") from exc


def select_dominant_driver(reason_codes: Iterable[str]) -> str:
    reasons = set(reason_codes)

    for driver in DRIVER_PRIORITY:
        if driver in reasons:
            return driver

    return "NONE"


def build_operational_risk(signals: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in signals.columns]

    if missing:
        raise ValueError(
            f"Risk signal frame is missing operational-risk columns: {missing}"
        )

    result = signals.copy()

    reason_lists = result["reason_codes"].apply(split_reason_codes)

    result["operational_state"] = result["regime_label"].apply(
        operational_state_from_regime
    )
    result["attention_level"] = result["regime_label"].apply(
        attention_level_from_regime
    )
    result["recommended_action"] = result["regime_label"].apply(
        recommended_action_from_regime
    )
    result["risk_driver_count"] = reason_lists.apply(len)
    result["dominant_driver"] = reason_lists.apply(select_dominant_driver)
    result["operational_risk_schema_version"] = OPERATIONAL_RISK_SCHEMA_VERSION

    return result[OUTPUT_COLUMNS].copy()


def load_risk_signals(path: str | Path) -> pd.DataFrame:
    input_path = Path(path)

    if not input_path.exists():
        raise FileNotFoundError(f"Risk-signal file not found: {input_path}")

    frame = pd.read_csv(input_path)

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"Risk-signal file is missing operational-risk columns: {missing}"
        )

    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    frame["timestamp_local"] = pd.to_datetime(
        frame["timestamp_local"], utc=True
    ).dt.tz_convert("Europe/Berlin")

    return frame.sort_values("timestamp_utc").reset_index(drop=True)


def build_operational_risk_table(
    *,
    input_file: str | Path,
    output_file: str | Path,
) -> pd.DataFrame:
    signals = load_risk_signals(input_file)
    operational_risk = build_operational_risk(signals)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    operational_risk.to_csv(output_path, index=False)

    print(
        f"OK | operational-risk rows={len(operational_risk)} "
        f"| output={output_path}"
    )

    return operational_risk
