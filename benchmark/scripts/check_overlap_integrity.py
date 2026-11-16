
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
        project_root / "benchmark" / "schemas" / "overlap.schema.json"
    )
    text_dir = (
        project_root / "benchmark" / "data" / "custom" / "documents"
    )

    documents_path = metadata_dir / "documents.jsonl"
    annotations_path = metadata_dir / "overlap_annotations.jsonl"

    errors = []

    try:
        with schema_path.open("r", encoding="utf-8") as file:
            overlap_schema = json.load(file)

        Draft202012Validator.check_schema(overlap_schema)
        annotation_validator = Draft202012Validator(overlap_schema)

    except Exception as error:
        print(f"ERROR: Could not load a valid overlap schema: {error}")
        return 1

    documents = load_jsonl(documents_path, errors)
    annotations = load_jsonl(annotations_path, errors)

    document_by_id = {}

    for line_number, document in enumerate(documents, start=1):
        document_id = document.get("document_id")

        if not isinstance(document_id, str) or not document_id.strip():
            errors.append(
                f"Document line {line_number}: "
                "Missing or invalid document_id."
            )
            continue

        if document_id in document_by_id:
            errors.append(
                f"Duplicate document_id {document_id!r} "
                "in document metadata."
            )
            continue

        document_by_id[document_id] = document

    text_by_id = {}

    for document_id in document_by_id:
        text_path = text_dir / f"{document_id}.txt"

        if not text_path.is_file():
            errors.append(
                f"Text file for document {document_id!r} "
                f"not found: {text_path}"
            )
            continue

        try:
            text_by_id[document_id] = text_path.read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeError) as error:
            errors.append(
                f"Could not read text for document {document_id!r}: "
                f"{error}"
            )

    annotation_id_locations = defaultdict(list)

    for line_number, annotation in enumerate(annotations, start=1):
        for validation_error in annotation_validator.iter_errors(annotation):
            field_path = ".".join(
                str(part) for part in validation_error.absolute_path
            )
            location = f" ({field_path})" if field_path else ""

            errors.append(
                f"Annotation line {line_number}: "
                f"Schema validation error{location}: "
                f"{validation_error.message}"
            )

        annotation_id = annotation.get("annotation_id")
        source_id = annotation.get("source_document_id")
        target_id = annotation.get("target_document_id")

        if isinstance(annotation_id, str) and annotation_id.strip():
            annotation_id_locations[annotation_id].append(line_number)

        if isinstance(source_id, str):
            if source_id not in document_by_id:
                errors.append(
                    f"Annotation line {line_number}: "
                    f"Source document {source_id!r} does not exist."
                )
        else:
            errors.append(
                f"Annotation line {line_number}: "
                "source_document_id must be a string."
            )

        if isinstance(target_id, str):
            if target_id not in document_by_id:
                errors.append(
                    f"Annotation line {line_number}: "
                    f"Target document {target_id!r} does not exist."
                )
        else:
            errors.append(
                f"Annotation line {line_number}: "
                "target_document_id must be a string."
            )

        if (
            isinstance(source_id, str)
            and isinstance(target_id, str)
            and source_id == target_id
        ):
            errors.append(
                f"Annotation line {line_number}: "
                "Source and target documents must differ."
            )

        for start_field, end_field, document_id, role in (
            ("source_start", "source_end", source_id, "source"),
            ("target_start", "target_end", target_id, "target"),
        ):
            start = annotation.get(start_field)
            end = annotation.get(end_field)

            valid_integers = (
                isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
            )

            if not valid_integers:
                continue

            if start < 0:
                errors.append(
                    f"Annotation line {line_number}: "
                    f"{role.capitalize()} start offset must be non-negative; "
                    f"got {start}."
                )
                continue

            if end <= start:
                errors.append(
                    f"Annotation line {line_number}: "
                    f"{role.capitalize()} end offset must be greater than "
                    f"start offset; got start={start}, end={end}."
                )
                continue

            if not isinstance(document_id, str):
                continue

            text = text_by_id.get(document_id)

            if text is not None and end > len(text):
                errors.append(
                    f"Annotation line {line_number}: "
                    f"{role.capitalize()} end offset {end} exceeds "
                    f"document {document_id!r} length {len(text)}."
                )

    for annotation_id, lines in annotation_id_locations.items():
        if len(lines) > 1:
            errors.append(
                f"Duplicate annotation_id {annotation_id!r} "
                f"found on lines {lines}."
            )

    print(f"Documents loaded: {len(documents)}")
    print(f"Document texts loaded: {len(text_by_id)}")
    print(f"Overlap annotations loaded: {len(annotations)}")
    print(f"Integrity errors: {len(errors)}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")

        print("RESULT: Overlap integrity checks failed.")
        return 1

    print("PASS: Annotation records satisfy overlap.schema.json.")
    print("PASS: Document IDs are unique.")
    print("PASS: Document text files exist and are readable.")
    print("PASS: Annotation IDs are unique.")
    print("PASS: Source and target documents exist and differ.")
    print("PASS: Passage spans have valid lengths and boundaries.")
    print("RESULT: Overlap integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
