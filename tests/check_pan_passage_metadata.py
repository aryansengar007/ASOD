import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

METADATA_PATH = PROJECT_ROOT / "benchmark" / "metadata" / "pan_pc11" / "documents.jsonl"

INDEX_DIR = Path(r"D:\ASOD_INDEXES\PAN_PC11\protocol_a_passage_tfidf")

PASSAGES_PATH = INDEX_DIR / "passages.jsonl"
MANIFEST_PATH = INDEX_DIR / "passage_manifest.json"

EXPECTED_REFERENCES = 7990
EXPECTED_TRAINING = 7765


def load_expected_documents():
    expected = {}

    with METADATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            document = json.loads(line)
            split = document["split"]

            if split in ("shared_reference", "train"):
                document_id = document["document_id"]

                if document_id in expected:
                    raise ValueError(f"Duplicate document ID: {document_id}")

                expected[document_id] = split

    return expected


def main():
    print("========== PASSAGE METADATA INTEGRITY ==========")

    if not PASSAGES_PATH.is_file():
        raise FileNotFoundError(PASSAGES_PATH)

    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(MANIFEST_PATH)

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    expected_documents = load_expected_documents()

    expected_reference_docs = {
        doc_id
        for doc_id, split in expected_documents.items()
        if split == "shared_reference"
    }

    expected_training_docs = {
        doc_id for doc_id, split in expected_documents.items() if split == "train"
    }

    counts = Counter()
    documents_seen = set()
    last_passage_number = {}
    last_offsets = {}

    with PASSAGES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                raise ValueError(f"Empty line at {line_number}")

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON at line {line_number}: {error}"
                ) from error

            passage_id = record["passage_id"]
            document_id = record["document_id"]
            split = record["split"]
            start = record["start_offset"]
            end = record["end_offset"]
            token_count = record["token_count"]

            if document_id not in expected_documents:
                raise ValueError(
                    f"Unexpected document at line {line_number}: " f"{document_id}"
                )

            if split != expected_documents[document_id]:
                raise ValueError(
                    f"Incorrect split at line {line_number}: " f"{document_id}"
                )

            if not isinstance(start, int) or not isinstance(end, int):
                raise ValueError(f"Non-integer offsets at line {line_number}")

            if start < 0 or end <= start:
                raise ValueError(f"Invalid offsets at line {line_number}")

            if (
                not isinstance(token_count, int)
                or isinstance(token_count, bool)
                or token_count < 1
            ):
                raise ValueError(f"Invalid token count at line {line_number}")

            expected_number = last_passage_number.get(document_id, 0) + 1

            expected_id = f"{document_id}::PASSAGE::{expected_number:06d}"

            if passage_id != expected_id:
                raise ValueError(
                    f"Passage ID or sequence error at line "
                    f"{line_number}: {passage_id}"
                )

            previous_offsets = last_offsets.get(document_id)

            if previous_offsets is not None:
                previous_start, previous_end = previous_offsets

                if start <= previous_start or end <= previous_end:
                    raise ValueError(
                        f"Non-increasing offsets at line {line_number}: "
                        f"{passage_id}"
                    )

            last_passage_number[document_id] = expected_number
            last_offsets[document_id] = (start, end)

            documents_seen.add(document_id)
            counts[split] += 1

            if line_number % 250000 == 0:
                print(f"Checked {line_number:,} passage records...")

    missing_documents = set(expected_documents) - documents_seen

    if missing_documents:
        raise ValueError(f"Documents without passages: " f"{len(missing_documents)}")

    if counts["shared_reference"] != manifest["reference_passage_count"]:
        raise ValueError("Reference passage count mismatch")

    if counts["train"] != manifest["training_passage_count"]:
        raise ValueError("Training passage count mismatch")

    if len(expected_reference_docs) != EXPECTED_REFERENCES:
        raise ValueError("Unexpected reference document count")

    if len(expected_training_docs) != EXPECTED_TRAINING:
        raise ValueError("Unexpected training document count")

    print("\n========== VERIFICATION RESULTS ==========")
    print(f"Total passages: {sum(counts.values()):,}")
    print(f"Reference passages: " f"{counts['shared_reference']:,}")
    print(f"Training passages: {counts['train']:,}")
    print(f"Reference documents represented: " f"{len(expected_reference_docs):,}")
    print(f"Training documents represented: " f"{len(expected_training_docs):,}")
    print(f"Documents missing passages: " f"{len(missing_documents)}")

    print("\nPASS: All passage records are valid.")
    print("PASS: Passage IDs and numbering are consistent.")
    print("PASS: Parent document IDs and splits are valid.")
    print("PASS: Character offsets are positive and increasing.")
    print("PASS: Passage counts match the index manifest.")
    print("ALL PASSAGE METADATA CHECKS PASSED")


if __name__ == "__main__":
    main()
