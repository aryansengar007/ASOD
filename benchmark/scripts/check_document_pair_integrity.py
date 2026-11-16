
import json
import sys
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator


def load_jsonl(path: Path, errors: list[str]) -> list[dict]:
    records = []

    if not path.is_file():
        errors.append(f"Required file not found: {path}")
        return records

    try:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    errors.append(
                        f"{path.name}, line {line_number}: "
                        f"Invalid JSON: {error.msg}"
                    )
                    continue

                if not isinstance(record, dict):
                    errors.append(
                        f"{path.name}, line {line_number}: "
                        "Record must be a JSON object."
                    )
                    continue

                records.append(record)

    except (OSError, UnicodeError) as error:
        errors.append(f"Could not read {path}: {error}")

    return records


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    metadata_dir = project_root / "benchmark" / "metadata"
    schema_path = (
        project_root
        / "benchmark"
        / "schemas"
        / "document_pair.schema.json"
    )

    documents_path = metadata_dir / "documents.jsonl"
    pairs_path = metadata_dir / "document_pairs.jsonl"
    errors = []

    try:
        with schema_path.open("r", encoding="utf-8") as file:
            pair_schema = json.load(file)

        Draft202012Validator.check_schema(pair_schema)
        pair_validator = Draft202012Validator(pair_schema)

    except (OSError, UnicodeError, json.JSONDecodeError,
            ValueError, TypeError) as error:
        print(f"ERROR: Could not load a valid document-pair schema: {error}")
        return 1

    documents = load_jsonl(documents_path, errors)
    pairs = load_jsonl(pairs_path, errors)

    document_ids = set()

    for line_number, document in enumerate(documents, start=1):
        document_id = document.get("document_id")

        if not isinstance(document_id, str) or not document_id.strip():
            errors.append(
                f"Document line {line_number}: "
                "Missing or invalid document_id."
            )
            continue

        if document_id in document_ids:
            errors.append(
                f"Duplicate document_id {document_id!r} "
                "in document metadata."
            )
            continue

        document_ids.add(document_id)

    pair_id_locations = defaultdict(list)

    for line_number, pair in enumerate(pairs, start=1):
        for validation_error in pair_validator.iter_errors(pair):
            field_path = ".".join(
                str(part) for part in validation_error.absolute_path
            )
            location = f" ({field_path})" if field_path else ""

            errors.append(
                f"Pair line {line_number}: "
                f"Schema validation error{location}: "
                f"{validation_error.message}"
            )

        pair_id = pair.get("pair_id")
        source_id = pair.get("source_document_id")
        target_id = pair.get("target_document_id")

        if isinstance(pair_id, str) and pair_id.strip():
            pair_id_locations[pair_id].append(line_number)

        if isinstance(source_id, str):
            if source_id not in document_ids:
                errors.append(
                    f"Pair line {line_number}: "
                    f"Source document {source_id!r} does not exist."
                )
        else:
            errors.append(
                f"Pair line {line_number}: "
                "source_document_id must be a string."
            )

        if isinstance(target_id, str):
            if target_id not in document_ids:
                errors.append(
                    f"Pair line {line_number}: "
                    f"Target document {target_id!r} does not exist."
                )
        else:
            errors.append(
                f"Pair line {line_number}: "
                "target_document_id must be a string."
            )

        if (
            isinstance(source_id, str)
            and isinstance(target_id, str)
            and source_id == target_id
        ):
            errors.append(
                f"Pair line {line_number}: "
                "Source and target documents must differ."
            )

    for pair_id, lines in pair_id_locations.items():
        if len(lines) > 1:
            errors.append(
                f"Duplicate pair_id {pair_id!r} found on lines {lines}."
            )

    print(f"Documents loaded: {len(documents)}")
    print(f"Unique document IDs: {len(document_ids)}")
    print(f"Document-pair annotations loaded: {len(pairs)}")
    print(f"Integrity errors: {len(errors)}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")

        print("RESULT: Document-pair integrity checks failed.")
        return 1

    print("PASS: Pair records satisfy document_pair.schema.json.")
    print("PASS: Document IDs are unique.")
    print("PASS: Pair IDs are unique.")
    print("PASS: Source and target documents exist and differ.")
    print("RESULT: Document-pair integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
