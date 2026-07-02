from __future__ import annotations

import argparse
from pathlib import Path

from src.data_quality.feature_release_gate import (
    run_feature_release_gate,
    write_feature_release_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run analytical release checks on an hourly feature dataset."
    )
    parser.add_argument("--features-file", required=True)
    parser.add_argument("--metadata-file", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--residual-gap-tolerance-mw", type=float, default=1.0)
    parser.add_argument("--expected-market-label", default="DE-LU")
    parser.add_argument("--expected-smard-region", default="DE")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = run_feature_release_gate(
        args.features_file,
        metadata_path=args.metadata_file,
        residual_gap_tolerance_mw=args.residual_gap_tolerance_mw,
        expected_market_label=args.expected_market_label,
        expected_smard_region=args.expected_smard_region,
    )

    write_feature_release_artifacts(
        result,
        feature_path=args.features_file,
        metadata_path=args.metadata_file,
        report_output=args.report_output,
        json_output=args.json_output,
    )

    print(
        "OK | "
        f"release_status={result.status} | "
        f"report={Path(args.report_output)} | "
        f"json={Path(args.json_output)}"
    )

    if result.status != "READY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
