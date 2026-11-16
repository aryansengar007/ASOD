import argparse
import json
import shutil
import tempfile
from pathlib import Path

from src.preprocessing.pan_loader import (
    PanPC11Loader,
    normalize_for_similarity,
)
from src.similarity.passage_segmentation import segment_document
from src.similarity.streaming_tfidf_retriever import (
    StreamingTfidfRetriever,
)
from src.similarity.build_pan_tfidf_index import (
    PROJECT_ROOT,
    DEFAULT_CORPUS_ROOT,
    METADATA_PATH,
    load_metadata,
    validate_selection,
    validate_corpus_paths,
)

DEFAULT_INDEX_DIR = Path(r"D:\ASOD_INDEXES\PAN_PC11\protocol_a_passage_tfidf")

PASSAGE_SIZE = 200
OVERLAP = 50
MIN_LAST_PASSAGE = 50

N_FEATURES = 2**22
BATCH_SIZE = 4
CHUNK_SIZE = 128


class PassageTextLoader:
    """Load normalized passage text with a one-document cache."""

    def __init__(self, corpus_loader):
        self.corpus_loader = corpus_loader
        self.current_document_id = None
        self.current_passages = []

    def __call__(self, passage_id):
        marker = "::PASSAGE::"

        if marker not in passage_id:
            raise ValueError(f"Invalid passage ID: {passage_id}")

        document_id, passage_number = passage_id.rsplit(marker, 1)

        try:
            passage_index = int(passage_number) - 1
        except ValueError as error:
            raise ValueError(f"Invalid passage number: {passage_id}") from error

        if passage_index < 0:
            raise ValueError(f"Invalid passage number: {passage_id}")

        if document_id != self.current_document_id:
            original_text = self.corpus_loader.load_text(document_id)

            self.current_passages = segment_document(
                document_id,
                original_text,
                passage_size=PASSAGE_SIZE,
                overlap=OVERLAP,
                min_last_passage=MIN_LAST_PASSAGE,
            )

            self.current_document_id = document_id

        if passage_index >= len(self.current_passages):
            raise IndexError(f"Passage does not exist: {passage_id}")

        passage = self.current_passages[passage_index]

        if passage["passage_id"] != passage_id:
            raise ValueError(f"Passage ID mismatch: {passage_id}")

        normalized = normalize_for_similarity(passage["text"])

        if not normalized:
            raise ValueError(f"Normalized passage is empty: {passage_id}")

        return normalized


def build_passage_catalog(
    documents,
    loader,
    output_path,
):
    reference_ids = []
    training_ids = []

    reference_count = 0
    training_count = 0
    total_tokens = 0

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output:

        for document in documents:
            split = document["split"]

            if split not in ("shared_reference", "train"):
                continue

            document_id = document["document_id"]
            original_text = loader.load_text(document_id)

            passages = segment_document(
                document_id,
                original_text,
                passage_size=PASSAGE_SIZE,
                overlap=OVERLAP,
                min_last_passage=MIN_LAST_PASSAGE,
            )

            if not passages:
                raise ValueError(f"No passages generated: {document_id}")

            for passage in passages:
                record = {
                    "passage_id": passage["passage_id"],
                    "document_id": document_id,
                    "split": split,
                    "start_offset": passage["start_offset"],
                    "end_offset": passage["end_offset"],
                    "token_count": passage["token_count"],
                }

                output.write(json.dumps(record, ensure_ascii=False) + "\n")

                if split == "shared_reference":
                    reference_ids.append(passage["passage_id"])
                    reference_count += 1
                else:
                    training_ids.append(passage["passage_id"])
                    training_count += 1

                total_tokens += passage["token_count"]

            if (reference_count + training_count) % 10000 < len(passages):
                print("Passages catalogued: " f"{reference_count + training_count}")

    if not reference_ids:
        raise ValueError("No reference passages generated")

    if not training_ids:
        raise ValueError("No training passages generated")

    if len(reference_ids) != len(set(reference_ids)):
        raise ValueError("Duplicate reference passage IDs")

    if len(training_ids) != len(set(training_ids)):
        raise ValueError("Duplicate training passage IDs")

    if set(reference_ids).intersection(training_ids):
        raise ValueError("Reference and training passage IDs overlap")

    return {
        "reference_ids": reference_ids,
        "training_ids": training_ids,
        "reference_count": reference_count,
        "training_count": training_count,
        "total_tokens": total_tokens,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build the ASOD PAN-PC-11 Protocol A " "passage-level TF-IDF index."
        )
    )

    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=DEFAULT_CORPUS_ROOT,
    )

    parser.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
    )

    parser.add_argument(
        "--build",
        action="store_true",
        help="Build the index. Without this flag, run preflight only.",
    )

    args = parser.parse_args()

    corpus_root = args.corpus_root.resolve()
    index_dir = args.index_dir.resolve()

    print("\n========== ASOD PAN PASSAGE INDEX BUILDER ==========")

    if not corpus_root.is_dir():
        raise FileNotFoundError(f"PAN corpus directory not found: {corpus_root}")

    if index_dir.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Index directory must be outside the ASOD project.")

    if index_dir.exists():
        raise FileExistsError(f"Index destination already exists: {index_dir}")

    documents = load_metadata()

    references, training, validation, testing = validate_selection(documents)

    print(f"Total metadata documents: {len(documents)}")
    print(f"Reference documents: {len(references)}")
    print(f"Training documents: {len(training)}")
    print(f"Validation documents: {len(validation)}")
    print(f"Test documents: {len(testing)}")

    loader = PanPC11Loader(corpus_root)

    validate_corpus_paths(loader, documents)

    print("\nPASS: All metadata document IDs resolve to PAN files.")

    sample_documents = [
        references[0],
        training[0],
        validation[0],
        testing[0],
    ]

    for document in sample_documents:
        original_text = loader.load_text(document["document_id"])

        passages = segment_document(
            document["document_id"],
            original_text,
            passage_size=PASSAGE_SIZE,
            overlap=OVERLAP,
            min_last_passage=MIN_LAST_PASSAGE,
        )

        if not passages:
            raise ValueError(f"No passages generated: " f"{document['document_id']}")

        print(f"PASS: {document['document_id']} " f"({len(passages)} passages)")

    print(f"\nIndex destination: {index_dir}")
    print(f"Passage size: {PASSAGE_SIZE}")
    print(f"Overlap: {OVERLAP}")
    print(f"Minimum final increment: {MIN_LAST_PASSAGE}")

    if not args.build:
        print("\nPREFLIGHT PASSED.")
        print("No index was built.")
        print("No corpus or existing index files were modified.")
        print("Run again with --build to start indexing.")
        return

    index_dir.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{index_dir.name}.building-",
            dir=index_dir.parent,
        )
    )

    try:
        print("\n========== BUILDING PASSAGE CATALOG ==========")

        catalog = build_passage_catalog(
            documents=documents,
            loader=loader,
            output_path=staging_dir / "passages.jsonl",
        )

        reference_ids = catalog["reference_ids"]
        training_ids = catalog["training_ids"]

        print("\n========== PASSAGE COUNTS ==========")
        print(f"Reference passages: " f"{catalog['reference_count']}")
        print(f"Training passages: " f"{catalog['training_count']}")
        print(f"Total passage tokens: " f"{catalog['total_tokens']}")

        print("\n========== BUILDING TF-IDF INDEX ==========")
        print("IDF fitting: reference + training passages only")
        print("Validation and test passages are excluded.")

        retriever = StreamingTfidfRetriever(
            n_features=N_FEATURES,
            batch_size=BATCH_SIZE,
            chunk_size=CHUNK_SIZE,
        )

        passage_loader = PassageTextLoader(loader)

        retriever.fit(
            reference_ids=reference_ids,
            training_ids=training_ids,
            load_text=passage_loader,
            index_dir=staging_dir / "retriever",
        )

        passage_manifest = {
            "dataset": "PAN-PC-11",
            "protocol": "A",
            "granularity": "passage",
            "passage_size": PASSAGE_SIZE,
            "overlap": OVERLAP,
            "min_last_passage": MIN_LAST_PASSAGE,
            "idf_unit": "passage",
            "reference_document_count": len(references),
            "training_document_count": len(training),
            "validation_document_count": len(validation),
            "test_document_count": len(testing),
            "reference_passage_count": catalog["reference_count"],
            "training_passage_count": catalog["training_count"],
            "total_passage_tokens": catalog["total_tokens"],
            "passage_metadata_file": "passages.jsonl",
            "retriever_directory": "retriever",
        }

        with (staging_dir / "passage_manifest.json").open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(
                passage_manifest,
                file,
                indent=2,
            )

        if index_dir.exists():
            raise FileExistsError(f"Final destination already exists: {index_dir}")

        staging_dir.rename(index_dir)

        print("\n========== PASSAGE INDEX BUILD COMPLETE ==========")
        print(f"Published index: {index_dir}")

    except Exception:
        shutil.rmtree(
            staging_dir,
            ignore_errors=True,
        )
        raise


if __name__ == "__main__":
    main()
