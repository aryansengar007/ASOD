
from pathlib import Path
import csv
from collections import defaultdict, Counter

BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
REPORTS = BENCHMARK_ROOT / "reports"

INVENTORY_FILE = REPORTS / "pan_pc11_relationship_inventory.csv"
GROUPS_FILE = REPORTS / "pan_pc11_connected_groups.csv"

LARGEST_GROUPS_FILE = REPORTS / "pan_pc11_largest_groups.csv"
SOURCE_LINKS_FILE = REPORTS / "pan_pc11_source_link_frequency.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    for path in (INVENTORY_FILE, GROUPS_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required report not found: {path}")

    inventory = read_csv(INVENTORY_FILE)
    group_rows = read_csv(GROUPS_FILE)

    # Map every document to its connected component.
    document_to_group = {}
    group_members = defaultdict(list)

    for row in group_rows:
        document_id = row["document_id"]
        group_id = row["source_group_id"]
        role = row["document_role"]

        document_to_group[document_id] = group_id
        group_members[group_id].append((document_id, role))

    # Summarize each connected component.
    group_summary = []

    for group_id, members in group_members.items():
        source_count = sum(role == "source" for _, role in members)
        suspicious_count = sum(
            role == "suspicious" for _, role in members
        )

        group_summary.append({
            "source_group_id": group_id,
            "total_documents": len(members),
            "source_documents": source_count,
            "suspicious_documents": suspicious_count,
        })

    group_summary.sort(
        key=lambda row: row["total_documents"],
        reverse=True
    )

    with LARGEST_GROUPS_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        fields = [
            "source_group_id",
            "total_documents",
            "source_documents",
            "suspicious_documents",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(group_summary[:20])

    # Count distinct suspicious documents linked to each source.
    source_to_suspicious = defaultdict(set)
    source_annotation_counts = Counter()

    for row in inventory:
        source = row["source_reference"].strip()
        suspicious = row["suspicious_document"].strip()

        if not source or not suspicious:
            continue

        source_to_suspicious[source].add(suspicious)
        source_annotation_counts[source] += 1

    source_summary = []

    for source, suspicious_docs in source_to_suspicious.items():
        group_id = document_to_group.get(f"SOURCE::{source}", "")

        source_summary.append({
            "source_document": source,
            "connected_group": group_id,
            "distinct_suspicious_documents": len(suspicious_docs),
            "annotation_count": source_annotation_counts[source],
        })

    source_summary.sort(
        key=lambda row: (
            row["distinct_suspicious_documents"],
            row["annotation_count"]
        ),
        reverse=True
    )

    with SOURCE_LINKS_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        fields = [
            "source_document",
            "connected_group",
            "distinct_suspicious_documents",
            "annotation_count",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(source_summary[:50])

    # Inspect the largest component.
    largest = group_summary[0] if group_summary else None

    print("\n========== PAN-PC-11 DIAGNOSTIC ==========")
    print(f"Connected groups: {len(group_summary)}")
    print(f"Source documents with links: {len(source_summary)}")

    if largest:
        print("\nLARGEST CONNECTED COMPONENT")
        print(f"Group ID: {largest['source_group_id']}")
        print(f"Total documents: {largest['total_documents']}")
        print(f"Source documents: {largest['source_documents']}")
        print(f"Suspicious documents: {largest['suspicious_documents']}")

    print("\nTOP 10 LARGEST GROUPS")
    for index, group in enumerate(group_summary[:10], start=1):
        print(
            f"{index}. {group['source_group_id']} | "
            f"Total: {group['total_documents']} | "
            f"Sources: {group['source_documents']} | "
            f"Suspicious: {group['suspicious_documents']}"
        )

    print("\nTOP 10 MOST LINKED SOURCE DOCUMENTS")
    for index, source in enumerate(source_summary[:10], start=1):
        print(
            f"{index}. {source['source_document']} | "
            f"Distinct suspicious docs: "
            f"{source['distinct_suspicious_documents']} | "
            f"Annotations: {source['annotation_count']} | "
            f"Group: {source['connected_group']}"
        )

    print("\nGENERATED REPORTS")
    print(LARGEST_GROUPS_FILE)
    print(SOURCE_LINKS_FILE)
    print("\nDiagnostic completed.")


if __name__ == "__main__":
    main()
