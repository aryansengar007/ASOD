import argparse
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

DEFAULT_INDEX_DIR = Path(r"D:\ASOD_INDEXES\PAN_PC11\protocol_a_passage_tfidf")

PASSAGE_MARKER = "::PASSAGE::"
PROGRESS_INTERVAL = 250_000


def build_parent_map(index_dir: Path) -> None:
    index_dir = index_dir.resolve()

    if not index_dir.is_dir():
        raise FileNotFoundError(f"Passage index directory does not exist: {index_dir}")

    passages_path = index_dir / "passages.jsonl"
    manifest_path = index_dir / "passage_manifest.json"

    if not passages_path.is_file():
        raise FileNotFoundError(passages_path)

    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    output_dir = index_dir / "parent_map"

    if output_dir.exists():
        raise FileExistsError(
            f"Parent-map destination already exists: {output_dir}\n"
            "Nothing was overwritten."
        )

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    expected_passages = manifest.get("reference_passage_count")
    expected_documents = manifest.get("reference_document_count")

    if (
        not isinstance(expected_passages, int)
        or isinstance(expected_passages, bool)
        or expected_passages <= 0
    ):
        raise ValueError("Invalid reference_passage_count in manifest.")

    if (
        not isinstance(expected_documents, int)
        or isinstance(expected_documents, bool)
        or expected_documents <= 0
    ):
        raise ValueError("Invalid reference_document_count in manifest.")

    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=".parent_map.building-",
            dir=index_dir,
        )
    )

    codes_path = staging_dir / "reference_parent_codes.npy"
    documents_path = staging_dir / "reference_parent_documents.json"

    codes = None

    try:
        codes = np.lib.format.open_memmap(
            codes_path,
            mode="w+",
            dtype=np.uint32,
            shape=(expected_passages,),
        )

        parent_documents = []
        completed_documents = set()

        current_document_id = None
        current_document_code = None
        previous_passage_number = None

        reference_count = 0

        print("========== BUILDING PASSAGE PARENT MAP ==========")
        print(f"Reference passages expected: {expected_passages:,}")
        print(f"Reference documents expected: {expected_documents:,}")

        with passages_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON at line {line_number}") from exc

                if record.get("split") != "shared_reference":
                    continue

                passage_id = record.get("passage_id")
                document_id = record.get("document_id")

                if not isinstance(passage_id, str) or not isinstance(document_id, str):
                    raise ValueError(f"Missing or invalid IDs at line {line_number}")

                expected_prefix = document_id + PASSAGE_MARKER

                if not passage_id.startswith(expected_prefix):
                    raise ValueError(
                        f"Passage/document ID mismatch at line {line_number}: "
                        f"{passage_id}"
                    )

                passage_number_text = passage_id[len(expected_prefix) :]

                try:
                    passage_number = int(passage_number_text)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid passage number at line {line_number}: "
                        f"{passage_id}"
                    ) from exc

                if document_id != current_document_id:
                    if document_id in completed_documents:
                        raise ValueError(
                            "Reference document passages are not contiguous: "
                            f"{document_id}"
                        )

                    if current_document_id is not None:
                        completed_documents.add(current_document_id)

                    current_document_id = document_id
                    current_document_code = len(parent_documents)
                    parent_documents.append(document_id)
                    previous_passage_number = None

                if (
                    previous_passage_number is not None
                    and passage_number <= previous_passage_number
                ):
                    raise ValueError(
                        f"Passage numbering is not increasing for " f"{document_id}"
                    )

                previous_passage_number = passage_number

                if reference_count >= expected_passages:
                    raise ValueError(
                        "More reference passages found than the manifest " "declares."
                    )

                codes[reference_count] = current_document_code
                reference_count += 1

                if reference_count % PROGRESS_INTERVAL == 0:
                    print(
                        f"Processed reference passages: "
                        f"{reference_count:,}/{expected_passages:,}"
                    )

        if reference_count != expected_passages:
            raise ValueError(
                f"Reference passage count mismatch: "
                f"expected {expected_passages:,}, "
                f"found {reference_count:,}"
            )

        if len(parent_documents) != expected_documents:
            raise ValueError(
                f"Reference document count mismatch: "
                f"expected {expected_documents:,}, "
                f"found {len(parent_documents):,}"
            )

        codes.flush()
        del codes
        codes = None

        with documents_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "dataset": manifest.get("dataset"),
                    "protocol": manifest.get("protocol"),
                    "parent_document_count": len(parent_documents),
                    "reference_passage_count": reference_count,
                    "documents": parent_documents,
                },
                file,
                indent=2,
            )

        staging_dir.rename(output_dir)

        print("\n========== PARENT MAP BUILD COMPLETE ==========")
        print(f"Reference passages: {reference_count:,}")
        print(f"Parent documents: {len(parent_documents):,}")
        print(f"Output directory: {output_dir}")
        print("Existing passage index files were not modified.")

    except Exception:
        if codes is not None:
            del codes

        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Build a compact passage-to-parent mapping."
    )

    parser.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
    )

    args = parser.parse_args()
    build_parent_map(args.index_dir)


if __name__ == "__main__":
    main()
