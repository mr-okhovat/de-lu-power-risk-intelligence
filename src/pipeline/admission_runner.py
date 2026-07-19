from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.core.market_data_admission import (
    AdmissionDecision,
    evaluate_dataframe,
    read_yaml,
)


DEFAULT_POLICY = (
    Path("src/config/admission_policies")
    / "hourly_market_dataset.yaml"
)


def run_market_data_admission(
    frame: pd.DataFrame,
    *,
    dataset_id: str,
    expected_start_utc: str | None = None,
    expected_end_utc: str | None = None,
    as_of_utc: str | pd.Timestamp | None = None,
    contract_status: str = "PASS",
    provenance_complete: bool = True,
    policy_path: str | Path = DEFAULT_POLICY,
):
    policy = read_yaml(policy_path)

    result = evaluate_dataframe(
        frame,
        dataset_id=dataset_id,
        policy=policy,
        contract_status=contract_status,
        provenance_complete=provenance_complete,
        expected_start_utc=expected_start_utc,
        expected_end_utc=expected_end_utc,
        as_of_utc=as_of_utc,
    )

    return result


def admission_passes_for_pipeline(result) -> bool:
    return result.decision in {
        AdmissionDecision.ACCEPT.value,
        AdmissionDecision.ACCEPT_WITH_WARNINGS.value,
    }


import json


def write_admission_report(
    result,
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            result.__dict__,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate an hourly market dataset for pipeline admission."
    )
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--expected-start-utc")
    parser.add_argument("--expected-end-utc")
    parser.add_argument("--as-of-utc")
    parser.add_argument("--contract-status", default="PASS")
    parser.add_argument(
        "--provenance-incomplete",
        action="store_true",
    )
    parser.add_argument(
        "--policy",
        default=str(DEFAULT_POLICY),
    )
    args = parser.parse_args()

    frame = pd.read_csv(args.input_csv)

    result = run_market_data_admission(
        frame,
        dataset_id=args.dataset_id,
        expected_start_utc=args.expected_start_utc,
        expected_end_utc=args.expected_end_utc,
        as_of_utc=args.as_of_utc,
        contract_status=args.contract_status,
        provenance_complete=not args.provenance_incomplete,
        policy_path=args.policy,
    )

    write_admission_report(
        result,
        args.output_json,
    )

    print(
        f"{result.decision} | "
        f"score={result.reliability_score:.1f} | "
        f"dataset={result.dataset_id}"
    )

    if not admission_passes_for_pipeline(result):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
