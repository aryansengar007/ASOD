
import json
import sys
from collections import defaultdict
from pathlib import Path


VALID_SPLITS = {"train", "validation", "test"}


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    data_path = (
        project_root / "benchmark" / "metadata" / "documents.jsonl"
    )

    if not data_path.is_file():
        print(f"ERROR: Document file not found: {data_path}")
        return 1

    group_splits = defaultdict(set)
    errors = []
    records_checked = 0

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
                    f"Line {line_number}: Expected a JSON object."
                )
                continue

            records_checked += 1

            group_id = record.get("source_group_id")
            split = record.get("split")

            if not isinstance(group_id, str) or not group_id.strip():
                errors.append(
                    f"Line {line_number}: Missing or invalid "
                    "source_group_id."
                )
                continue

            if split not in VALID_SPLITS:
                errors.append(
                    f"Line {line_number}: Invalid split {split!r}."
                )
                continue

            group_splits[group_id].add(split)

    leakage_groups = {
        group_id: sorted(splits)
        for group_id, splits in group_splits.items()
        if len(splits) > 1
    }

    print(f"Documents inspected: {records_checked}")
    print(f"Source groups inspected: {len(group_splits)}")

    if leakage_groups:
        for group_id, splits in sorted(leakage_groups.items()):
            errors.append(
                f"Source group {group_id!r} occurs across "
                f"multiple splits: {splits}."
            )

    if errors:
        print(f"Audit errors: {len(errors)}")
        for error in errors:
            print(f"FAIL: {error}")

        print("RESULT: Split-leakage audit failed.")
        return 1

    print("PASS: Every source group belongs to exactly one split.")
    print("RESULT: Split-leakage audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
