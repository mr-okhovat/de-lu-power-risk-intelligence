from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


VERSION = "12B.1"


@dataclass(frozen=True)
class AdapterResult:
    status: str
    adapter_name: str
    adapter_version: str
    input_file: str
    output_file: str
    row_count: int
    output_columns: list[str]
    missing_source_columns: list[str]
    conversion_errors: dict[str, int]
    notes: list[str]


def read_yaml(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing adapter file: {p}")

    with p.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid adapter file: {p}")

    if "name" not in data or "fields" not in data:
        raise ValueError("Adapter must contain name and fields.")

    return data


def read_input(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing input file: {p}")

    suffix = p.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(p)

    if suffix in {".json", ".jsonl"}:
        return pd.read_json(p, lines=suffix == ".jsonl")

    raise ValueError(f"Unsupported input format: {suffix}")


def to_bool(value: object) -> object:
    if pd.isna(value):
        return None

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n"}:
        return False

    return pd.NA


def convert_series(series: pd.Series, dtype: str) -> tuple[pd.Series, int]:
    if dtype == "string":
        return series.astype("string"), 0

    if dtype == "numeric":
        converted = pd.to_numeric(series, errors="coerce")
        errors = int((series.notna() & converted.isna()).sum())
        return converted, errors

    if dtype == "datetime":
        converted = pd.to_datetime(series, errors="coerce", utc=True)
        errors = int((series.notna() & converted.isna()).sum())
        return converted.astype("string"), errors

    if dtype == "boolean":
        converted = series.map(to_bool)
        errors = int((series.notna() & converted.isna()).sum())
        return converted.astype("boolean"), errors

    raise ValueError(f"Unsupported adapter dtype: {dtype}")


def constant_series(value: object, rows: int) -> pd.Series:
    return pd.Series([value] * rows)


def adapt_frame(df: pd.DataFrame, adapter: dict[str, Any]) -> tuple[pd.DataFrame, AdapterResult]:
    fields = adapter.get("fields", [])
    missing: list[str] = []
    conversion_errors: dict[str, int] = {}
    output = pd.DataFrame(index=df.index)

    for field in fields:
        source = field.get("source")
        target = field.get("target")
        dtype = field.get("dtype")
        required = bool(field.get("required", True))

        if not target:
            raise ValueError("Every adapter field must define target.")

        if source is None and "constant" not in field:
            raise ValueError(f"Field {target} must define source or constant.")

        if source is not None:
            if source not in df.columns:
                if required:
                    missing.append(str(source))
                continue

            series = df[source]
        else:
            series = constant_series(field.get("constant"), len(df))

        if dtype:
            converted, errors = convert_series(series, dtype)
            if errors:
                conversion_errors[target] = errors
            output[target] = converted
        else:
            output[target] = series

    sort_by = adapter.get("sort_by")
    if sort_by and sort_by in output.columns:
        output = output.sort_values(sort_by).reset_index(drop=True)

    notes = []

    if missing:
        notes.append("Required source columns are missing.")

    if conversion_errors:
        notes.append("Some fields could not be converted cleanly.")

    if not notes:
        notes.append("Dataset adapted successfully.")

    status = "PASS" if not missing and not conversion_errors else "CHECK NEEDED"

    result = AdapterResult(
        status=status,
        adapter_name=str(adapter["name"]),
        adapter_version=str(adapter.get("version", VERSION)),
        input_file="",
        output_file="",
        row_count=int(len(output)),
        output_columns=list(output.columns),
        missing_source_columns=missing,
        conversion_errors=conversion_errors,
        notes=notes,
    )

    return output, result


def report_text(result: AdapterResult) -> str:
    lines = [
        "# Dataset adapter run",
        "",
        f"Adapter: `{result.adapter_name}`",
        f"Adapter version: `{result.adapter_version}`",
        f"Status: `{result.status}`",
        f"Input: `{result.input_file}`",
        f"Output: `{result.output_file}`",
        f"Rows: `{result.row_count}`",
        "",
        "## Output columns",
        "",
    ]

    for col in result.output_columns:
        lines.append(f"- `{col}`")

    lines += [
        "",
        "## Checks",
        "",
        f"- Missing source columns: `{result.missing_source_columns}`",
        f"- Conversion errors: `{result.conversion_errors}`",
        "",
        "## Notes",
        "",
    ]

    for note in result.notes:
        lines.append(f"- {note}")

    lines.append("")

    return "\n".join(lines)


def run(adapter_file: str, input_file: str, output_file: str, report_output: str, json_output: str) -> None:
    adapter = read_yaml(adapter_file)
    df = read_input(input_file)

    adapted, result = adapt_frame(df, adapter)

    result = AdapterResult(
        status=result.status,
        adapter_name=result.adapter_name,
        adapter_version=result.adapter_version,
        input_file=input_file,
        output_file=output_file,
        row_count=result.row_count,
        output_columns=result.output_columns,
        missing_source_columns=result.missing_source_columns,
        conversion_errors=result.conversion_errors,
        notes=result.notes,
    )

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(report_output).parent.mkdir(parents=True, exist_ok=True)
    Path(json_output).parent.mkdir(parents=True, exist_ok=True)

    adapted.to_csv(output_file, index=False)
    Path(report_output).write_text(report_text(result), encoding="utf-8")
    Path(json_output).write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")

    print(f"OK | adapter={result.adapter_name} | status={result.status}")
    print(f"OK | output={output_file}")

    if result.status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--json-output", required=True)
    args = parser.parse_args()

    run(
        adapter_file=args.adapter,
        input_file=args.input,
        output_file=args.output,
        report_output=args.report_output,
        json_output=args.json_output,
    )


if __name__ == "__main__":
    main()
