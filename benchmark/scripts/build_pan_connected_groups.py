
from pathlib import Path
import csv
from collections import Counter

BENCHMARK_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BENCHMARK_ROOT / "reports"
    / "pan_pc11_relationship_inventory.csv"
)

OUTPUT_FILE = (
    BENCHMARK_ROOT / "reports"
    / "pan_pc11_connected_groups.csv"
)


class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, item):
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0

        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])

        return self.parent[item]

    def union(self, a, b):
        root_a = self.find(a)
        root_b = self.find(b)

        if root_a == root_b:
            return

        if self.rank[root_a] < self.rank[root_b]:
            root_a, root_b = root_b, root_a

        self.parent[root_b] = root_a

        if self.rank[root_a] == self.rank[root_b]:
            self.rank[root_a] += 1


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    uf = UnionFind()
    documents = {}

    with INPUT_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            suspicious = row["suspicious_document"].strip()
            source = row["source_reference"].strip()

            if not suspicious or not source:
                continue

            suspicious_id = f"SUSPICIOUS::{suspicious}"
            source_id = f"SOURCE::{source}"

            uf.union(suspicious_id, source_id)

            documents[suspicious_id] = (
                suspicious, "suspicious"
            )
            documents[source_id] = (
                source, "source"
            )

    components = {}

    for document_id, (filename, role) in documents.items():
        root = uf.find(document_id)
        components.setdefault(root, []).append(
            (document_id, filename, role)
        )

    sorted_components = sorted(
        components.values(),
        key=lambda group: (-len(group), group[0][0])
    )

    rows = []
    group_sizes = []

    for index, group in enumerate(sorted_components, start=1):
        group_id = f"PAN_GROUP_{index:05d}"
        group_sizes.append(len(group))

        for document_id, filename, role in group:
            rows.append({
                "source_group_id": group_id,
                "document_id": document_id,
                "filename": filename,
                "document_role": role,
                "group_size": len(group),
            })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        fields = [
            "source_group_id",
            "document_id",
            "filename",
            "document_role",
            "group_size",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    role_counts = Counter(
    role for _, role in documents.values()
)

    print("\n========== PAN-PC-11 CONNECTED GROUPS ==========")
    print(f"Documents included:       {len(documents)}")
    print(f"Suspicious documents:     {role_counts['suspicious']}")
    print(f"Source documents:         {role_counts['source']}")
    print(f"Connected groups:         {len(components)}")
    print(f"Largest group size:       {max(group_sizes, default=0)}")
    print(f"Groups with 1 document:   {sum(s == 1 for s in group_sizes)}")
    print(f"Groups with 2 documents:  {sum(s == 2 for s in group_sizes)}")
    print(f"Groups with 3+ documents: {sum(s >= 3 for s in group_sizes)}")
    print(f"\nReport: {OUTPUT_FILE}")
    print("\nConnected-group analysis completed.")


if __name__ == "__main__":
    main()
