
from pathlib import Path
from collections import defaultdict, Counter
import csv

ROOT = Path(__file__).resolve().parents[1] / "reports"

INPUT = ROOT / "pan_pc11_relationship_inventory.csv"
OUTPUT = ROOT / "pan_pc11_suspicious_link_frequency.csv"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    links = defaultdict(set)
    annotation_counts = Counter()

    with INPUT.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            suspicious = row["suspicious_document"].strip()
            source = row["source_reference"].strip()

            if suspicious and source:
                links[suspicious].add(source)
                annotation_counts[suspicious] += 1

    summary = [
        {
            "suspicious_document": name,
            "distinct_source_documents": len(sources),
            "annotation_count": annotation_counts[name],
        }
        for name, sources in links.items()
    ]

    summary.sort(
        key=lambda row: (
            row["distinct_source_documents"],
            row["annotation_count"],
        ),
        reverse=True,
    )

    with OUTPUT.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        fields = [
            "suspicious_document",
            "distinct_source_documents",
            "annotation_count",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary)

    distribution = Counter(
        row["distinct_source_documents"] for row in summary
    )

    print("\n========== SUSPICIOUS DOCUMENT LINK ANALYSIS ==========")
    print(f"Suspicious documents analyzed: {len(summary)}")
    print(f"Total annotations: {sum(annotation_counts.values())}")

    print("\nSOURCE-LINK DISTRIBUTION")
    print(f"1 source:       {sum(n for k, n in distribution.items() if k == 1)}")
    print(f"2-5 sources:    {sum(n for k, n in distribution.items() if 2 <= k <= 5)}")
    print(f"6-10 sources:   {sum(n for k, n in distribution.items() if 6 <= k <= 10)}")
    print(f"11-20 sources:  {sum(n for k, n in distribution.items() if 11 <= k <= 20)}")
    print(f"21+ sources:    {sum(n for k, n in distribution.items() if k >= 21)}")

    print("\nTOP 15 MOST CONNECTED SUSPICIOUS DOCUMENTS")
    for i, row in enumerate(summary[:15], 1):
        print(
            f"{i}. {row['suspicious_document']} | "
            f"Sources: {row['distinct_source_documents']} | "
            f"Annotations: {row['annotation_count']}"
        )

    print(f"\nReport: {OUTPUT}")
    print("\nAnalysis completed.")

if __name__ == "__main__":
    main()
