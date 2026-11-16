
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]

    schema_path = (
        project_root / "benchmark" / "schemas" / "document.schema.json"
    )
    data_path = (
        project_root / "benchmark" / "metadata" / "documents.jsonl"
    )

    if not schema_path.is_file():
        print(f"ERROR: Schema not found: {schema_path}")
        return 1

    if not data_path.is_file():
        print(f"ERROR: Document data file not found: {data_path}")
        return 1

    try:
        with schema_path.open("r", encoding="utf-8") as file:
            schema = json.load(file)

        validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )

    except (json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: Could not load the schema: {error}")
        return 1

    errors_found = 0
    records_checked = 0

    with data_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                errors_found += 1
                print(
                    f"FAIL: Line {line_number}: Invalid JSON "
                    f"(column {error.colno}: {error.msg})"
                )
                continue

            records_checked += 1
            errors = sorted(
                validator.iter_errors(record),
                key=lambda error: list(map(str, error.absolute_path)),
            )

            if errors:
                errors_found += len(errors)
                for error in errors:
                    location = ".".join(
                        str(part) for part in error.absolute_path
                    ) or "<record>"
                    print(
                        f"FAIL: Line {line_number}, {location}: "
                        f"{error.message}"
                    )
            else:
                print(
                    f"PASS: Line {line_number}, "
                    f"document_id={record.get('document_id', '<missing>')}"
                )

    print(f"\nRecords checked: {records_checked}")
    print(f"Validation errors: {errors_found}")

    if records_checked == 0:
        print("ERROR: No document records were found.")
        return 1

    if errors_found:
        print("RESULT: Document validation failed.")
        return 1

    print("RESULT: All document records satisfy the schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
