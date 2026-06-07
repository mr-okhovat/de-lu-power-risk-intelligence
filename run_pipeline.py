from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.data_ingestion.smard_client import SmardClient, load_smard_settings


def setup_logging() -> None:
    Path("logs").mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/pipeline.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DE-LU Power Risk Intelligence pipeline entrypoint."
    )

    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--smard-region", default="DE")
    parser.add_argument("--phase", default="smard-ingest", choices=["smard-ingest"])
    parser.add_argument("--filters", nargs="+", default=["410"])
    parser.add_argument("--resolution", default="hour")
    parser.add_argument("--config", default="src/config/sources.yaml")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue ingestion when one configured filter fails.",
    )

    return parser.parse_args()


def run_smard_ingestion(args: argparse.Namespace) -> None:
    settings = load_smard_settings(args.config)
    client = SmardClient(settings)

    succeeded: list[str] = []
    failed: list[str] = []

    for filter_id in args.filters:
        try:
            manifest = client.download_filter(
                filter_id=str(filter_id),
                start=args.start,
                end=args.end,
                market_label=args.market_label,
                smard_region=args.smard_region,
                resolution=args.resolution,
            )

            succeeded.append(str(filter_id))

            print(
                f"OK | SMARD filter={filter_id} | raw_files={len(manifest['files'])} | "
                f"run_id={manifest['run_id']}"
            )

        except Exception as exc:
            failed.append(str(filter_id))
            logging.exception("SMARD ingestion failed for filter=%s", filter_id)

            if not args.continue_on_error:
                raise

            print(f"FAIL | SMARD filter={filter_id} | error={exc}")

    print(f"SUMMARY | succeeded={succeeded} | failed={failed}")

    if failed and not succeeded:
        raise SystemExit(1)


def main() -> None:
    setup_logging()
    args = parse_args()

    if args.phase == "smard-ingest":
        run_smard_ingestion(args)
        return

    raise ValueError(f"Unsupported phase: {args.phase}")


if __name__ == "__main__":
    main()
