from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


VERSION = "12A.1"


@dataclass(frozen=True)
class ContractResult:
    status: str
    contract_name: str
    contract_version: str
    input_file: str
    row_count: int
    missing_required_columns: list[str]
    duplicate_key_rows: int
    null_violations: dict[str, int]
    dtype_violations: dict[str, int]
    range_violations: dict[str, int]
    allowed_value_violations: dict[str, int]
    notes: list[str]


def read_contract(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing contract file: {p}")

    with p.open("r", encoding="utf-8") as handle:
        contract = yaml.safe_load(handle)

    if not isinstance(contract, dict):
        raise ValueError(f"Invalid contract file: {p}")

    if "name" not in contract or "fields" not in contract:
        raise ValueError("Contract must contain name and fields.")

    return contract


def read_input(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing input file: {p}")

    return pd.read_csv(p)


def bool_mask(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return pd.Series(True, index=series.index)

    allowed = {"true", "false", "1", "0", "yes", "no"}
    return series.astype(str).str.lower().isin(allowed) | series.isna()


def dtype_violation_count(series: pd.Series, dtype: str) -> int:
    if dtype == "numeric":
        parsed = pd.to_numeric(series, errors="coerce")
        return int((series.notna() & parsed.isna()).sum())

    if dtype == "datetime":
        parsed = pd.to_datetime(series, errors="coerce", utc=True)
        return int((series.notna() & parsed.isna()).sum())

    if dtype == "boolean":
        return int((~bool_mask(series)).sum())

    if dtype == "string":
        return 0

    raise ValueError(f"Unsupported dtype in contract: {dtype}")


def range_violation_count(series: pd.Series, field: dict[str, Any]) -> int:
    if field.get("dtype") != "numeric":
        return 0

    parsed = pd.to_numeric(series, errors="coerce")
    mask = pd.Series(False, index=series.index)

    if "min_value" in field:
        mask = mask | (parsed < float(field["min_value"]))

    if "max_value" in field:
        mask = mask | (parsed > float(field["max_value"]))

    return int(mask.fillna(False).sum())


def allowed_value_violation_count(series: pd.Series, field: dict[str, Any]) -> int:
    allowed = field.get("allowed_values")

    if not allowed:
        return 0

    allowed_set = {str(item) for item in allowed}
    values = series.dropna().astype(str)

    return int((~values.isin(allowed_set)).sum())


def validate_frame(df: pd.DataFrame, contract: dict[str, Any], input_file: str) -> ContractResult:
    fields = contract.get("fields", [])
    required = [field["name"] for field in fields if field.get("required", True)]

    missing_required = [col for col in required if col not in df.columns]

    primary_key = contract.get("primary_key", [])
    duplicate_key_rows = 0

    if primary_key and all(col in df.columns for col in primary_key):
        duplicate_key_rows = int(df.duplicated(primary_key).sum())

    null_violations: dict[str, int] = {}
    dtype_violations: dict[str, int] = {}
    range_violations: dict[str, int] = {}
    allowed_violations: dict[str, int] = {}

    for field in fields:
        name = field["name"]

        if name not in df.columns:
            continue

        if field.get("nullable", True) is False:
            count = int(df[name].isna().sum())
            if count:
                null_violations[name] = count

        dtype = field.get("dtype")
        if dtype:
            count = dtype_violation_count(df[name], dtype)
            if count:
                dtype_violations[name] = count

        count = range_violation_count(df[name], field)
        if count:
            range_violations[name] = count

        count = allowed_value_violation_count(df[name], field)
        if count:
            allowed_violations[name] = count

    notes = []

    if missing_required:
        notes.append("Required columns are missing.")

    if duplicate_key_rows:
        notes.append("Primary-key duplicates were found.")

    if null_violations:
        notes.append("Non-null fields contain missing values.")

    if dtype_violations:
        notes.append("Field dtype checks failed.")

    if range_violations:
        notes.append("Numeric range checks failed.")

    if allowed_violations:
        notes.append("Allowed-value checks failed.")

    if not notes:
        notes.append("Dataset passed the contract checks.")

    blocking = any(
        [
            missing_required,
            duplicate_key_rows,
            null_violations,
            dtype_violations,
            range_violations,
            allowed_violations,
        ]
    )

    return ContractResult(
        status="PASS" if not blocking else "CHECK NEEDED",
        contract_name=str(contract["name"]),
        contract_version=str(contract.get("version", VERSION)),
        input_file=input_file,
        row_count=int(len(df)),
        missing_required_columns=missing_required,
        duplicate_key_rows=duplicate_key_rows,
        null_violations=null_violations,
        dtype_violations=dtype_violations,
        range_violations=range_violations,
        allowed_value_violations=allowed_violations,
        notes=notes,
    )


def report_text(result: ContractResult) -> str:
    lines = [
        "# Dataset contract check",
        "",
        f"Contract: `{result.contract_name}`",
        f"Contract version: `{result.contract_version}`",
        f"Status: `{result.status}`",
        f"Input: `{result.input_file}`",
        f"Rows: `{result.row_count}`",
        "",
        "## Checks",
        "",
        f"- Missing required columns: `{result.missing_required_columns}`",
        f"- Duplicate key rows: `{result.duplicate_key_rows}`",
        f"- Null violations: `{result.null_violations}`",
        f"- Dtype violations: `{result.dtype_violations}`",
        f"- Range violations: `{result.range_violations}`",
        f"- Allowed-value violations: `{result.allowed_value_violations}`",
        "",
        "## Notes",
        "",
    ]

    for note in result.notes:
        lines.append(f"- {note}")

    lines.append("")
    return "\n".join(lines)


def run(contract_file: str, input_file: str, report_output: str, json_output: str) -> None:
    contract = read_contract(contract_file)
    df = read_input(input_file)
    result = validate_frame(df, contract, input_file)

    Path(report_output).parent.mkdir(parents=True, exist_ok=True)
    Path(json_output).parent.mkdir(parents=True, exist_ok=True)

    Path(report_output).write_text(report_text(result), encoding="utf-8")
    Path(json_output).write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")

    print(f"OK | contract={result.contract_name} | status={result.status}")
    print(f"OK | report={report_output}")

    if result.status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--json-output", required=True)
    args = parser.parse_args()

    run(
        contract_file=args.contract,
        input_file=args.input,
        report_output=args.report_output,
        json_output=args.json_output,
    )


if __name__ == "__main__":
    main()
