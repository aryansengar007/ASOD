
from pathlib import Path
import csv
from collections import defaultdict, Counter

REPORTS = Path(__file__).resolve().parents[1] / "reports"
INPUT = REPORTS / "pan_pc11_split_manifest.csv"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    errors = []
    document_ids = [row["document_id"] for row in rows]

    if len(document_ids) != len(set(document_ids)):
        errors.append("Duplicate document IDs found.")

    group_splits = defaultdict(set)
    protocol_a = Counter()
    protocol_b = Counter()

    for row in rows:
        role = row["document_role"]
        group = row["source_group_id"]
        split_b = row["protocol_b_split"]

        protocol_a[(role, row["protocol_a_split"])] += 1
        protocol_b[(role, split_b)] += 1

        if group and row["protocol_b_status"] == "included":
            group_splits[group].add(split_b)

    leakage_groups = {
        group: splits
        for group, splits in group_splits.items()
        if len(splits) > 1
    }

    if leakage_groups:
        errors.append(
            f"{len(leakage_groups)} connected groups cross Protocol B splits."
        )

    print("\n========== SPLIT MANIFEST VALIDATION ==========")
    print(f"Total manifest rows: {len(rows)}")
    print(f"Unique document IDs: {len(set(document_ids))}")
    print(f"Protocol B groups checked: {len(group_splits)}")
    print(f"Groups crossing splits: {len(leakage_groups)}")

    print("\nPROTOCOL A COUNTS")
    for role in ("suspicious", "source"):
        for split in ("train", "validation", "test", "shared_reference"):
            print(f"{role} / {split}: {protocol_a[(role, split)]}")

    print("\nPROTOCOL B COUNTS")
    for role in ("suspicious", "source"):
        for split in (
            "train",
            "validation",
            "test",
            "excluded_largest_component",
            "not_in_annotated_graph",
        ):
            print(f"{role} / {split}: {protocol_b[(role, split)]}")

    if errors:
        print("\nVALIDATION FAILED")
        for error in errors:
            print("-", error)
    else:
        print("\nVALIDATION PASSED")
        print("No duplicate IDs or Protocol B group leakage detected.")

if __name__ == "__main__":
    main()
