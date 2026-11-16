
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    schema_dir = project_root / "benchmark" / "schemas"

    schema_files = sorted(schema_dir.glob("*.schema.json"))

    if not schema_files:
        print(f"ERROR: No schema files found in {schema_dir}")
        return 1

    failed = False

    print(f"Checking schemas in: {schema_dir}\n")

    for schema_path in schema_files:
        try:
            with schema_path.open("r", encoding="utf-8") as file:
                schema = json.load(file)

            Draft202012Validator.check_schema(schema)

            print(f"PASS: {schema_path.name}")

        except json.JSONDecodeError as error:
            failed = True
            print(
                f"FAIL: {schema_path.name} contains invalid JSON "
                f"at line {error.lineno}, column {error.colno}: "
                f"{error.msg}"
            )

        except Exception as error:
            failed = True
            print(f"FAIL: {schema_path.name}: {error}")

    if failed:
        print("\nSchema verification failed.")
        return 1

    print(f"\nSUCCESS: All {len(schema_files)} schema files are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
