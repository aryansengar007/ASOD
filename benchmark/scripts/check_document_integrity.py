
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    data_path = (
        project_root / "benchmark" / "metadata" / "documents.jsonl"
    )

    if not data_path.is_file():
        print(f"ERROR: Document file not found: {data_path}")
        return 1

    records = []
    errors = []

    with data_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(
                    f"Line {line_number}: Invalid JSON: {error.msg}"
                )
                continue

            if not isinstance(record, dict):
                errors.append(
                    f"Line {line_number}: Record must be a JSON object."
                )
                continue

            records.append((line_number, record))

    # Check document ID uniqueness.
    id_locations = defaultdict(list)

    for line_number, record in records:
        document_id = record.get("document_id")

        if isinstance(document_id, str) and document_id.strip():
            id_locations[document_id].append(line_number)
        else:
            errors.append(
                f"Line {line_number}: Missing or invalid document_id."
            )

    for document_id, lines in id_locations.items():
        if len(lines) > 1:
            errors.append(
                f"Duplicate document_id {document_id!r} "
                f"found on lines {lines}."
            )

    # Check parent references and prevent self-parenting.
    known_ids = set(id_locations)

    for line_number, record in records:
        document_id = record.get("document_id")
        parent_id = record.get("parent_document_id")

        if parent_id is None:
            continue

        if not isinstance(parent_id, str) or not parent_id.strip():
            errors.append(
                f"Line {line_number}: parent_document_id must be "
                "a non-empty string or null."
            )
            continue

        if parent_id == document_id:
            errors.append(
                f"Line {line_number}: A document cannot be its own parent."
            )
        elif parent_id not in known_ids:
            errors.append(
                f"Line {line_number}: Parent document "
                f"{parent_id!r} does not exist."
            )

    print(f"Documents inspected: {len(records)}")
    print(f"Integrity errors: {len(errors)}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")

        print("RESULT: Document integrity checks failed.")
        return 1

    print("PASS: Document IDs are unique.")
    print("PASS: All non-null parent references exist.")
    print("PASS: No document references itself as its parent.")
    print("RESULT: Document integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())