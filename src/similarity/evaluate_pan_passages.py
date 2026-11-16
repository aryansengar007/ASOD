from pathlib import Path
import argparse

from src.preprocessing.pan_loader import PanPC11Loader
from src.similarity.passage_document_retriever import (
    PassageDocumentRetriever,
)
from src.similarity.evaluate_pan_tfidf import (
    CORPUS_ROOT,
    load_evaluation_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INDEX_DIR = Path(r"D:\ASOD_INDEXES\PAN_PC11\protocol_a_passage_tfidf")

K_VALUES = (1, 5, 10, 20, 50, 100)
TOP_K = 100


def evaluate(retriever, loader, targets, positive_sources):
    """Evaluate passage retrieval using the existing Protocol A metrics."""

    total_targets = len(targets)
    total_positive_pairs = sum(len(sources) for sources in positive_sources.values())

    print("\n========== PASSAGE RETRIEVAL EVALUATION ==========")
    print(f"Evaluation targets: {total_targets:,}")
    print(f"Known-positive pairs: {total_positive_pairs:,}")
    print(f"Reference documents: {retriever.document_count:,}")
    print(f"Retrieval cutoff: {TOP_K}")

    # Load and normalize each query once.
    query_texts = []

    for position, target_id in enumerate(targets, start=1):
        query_texts.append(loader.load_normalized_text(target_id))

        if position % 100 == 0 or position == total_targets:
            print(f"Prepared queries: {position:,}/{total_targets:,}")

    # One complete passage-index scan for all queries.
    results = retriever.retrieve_many(
        query_texts=query_texts,
        top_k=TOP_K,
        progress=True,
    )

    if len(results) != total_targets:
        raise RuntimeError("Retriever returned an unexpected number of result lists.")

    target_hits = {k: 0 for k in K_VALUES}
    pair_hits = {k: 0 for k in K_VALUES}
    reciprocal_rank_sums = {k: 0.0 for k in K_VALUES}

    for target_id, ranked_results in zip(targets, results):
        positives = positive_sources[target_id]

        retrieved_ids = [item["document_id"] for item in ranked_results]

        for k in K_VALUES:
            top_ids = retrieved_ids[:k]
            retrieved_positive_count = sum(
                source_id in positives for source_id in top_ids
            )

            if retrieved_positive_count:
                target_hits[k] += 1

            pair_hits[k] += retrieved_positive_count

            first_positive_rank = next(
                (
                    rank
                    for rank, source_id in enumerate(
                        retrieved_ids,
                        start=1,
                    )
                    if source_id in positives
                ),
                None,
            )

            if first_positive_rank is not None and first_positive_rank <= k:
                reciprocal_rank_sums[k] += 1.0 / first_positive_rank

    print("\nK\tTarget Recall\tPair Recall\tMRR")

    for k in K_VALUES:
        target_recall = target_hits[k] / total_targets

        pair_recall = (
            pair_hits[k] / total_positive_pairs if total_positive_pairs else 0.0
        )

        mrr = reciprocal_rank_sums[k] / total_targets

        print(
            f"@{k}\t" f"{target_recall:.4f}\t\t" f"{pair_recall:.4f}\t\t" f"{mrr:.4f}"
        )

    print("\n========== EVALUATION COMPLETE ==========")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate PAN-PC-11 passage-level retrieval."
    )

    parser.add_argument(
        "--split",
        choices=("validation", "test"),
        default="validation",
        help="Evaluation split.",
    )

    args = parser.parse_args()

    if not INDEX_DIR.is_dir():
        raise FileNotFoundError(f"Passage index not found: {INDEX_DIR}")

    print("Loading passage document retriever...")

    retriever = PassageDocumentRetriever(INDEX_DIR)

    print("Loading PAN-PC-11 corpus...")

    loader = PanPC11Loader(CORPUS_ROOT)

    print("Loading Protocol A evaluation data...")

    targets, positive_sources = load_evaluation_data(
        args.split,
        set(retriever.documents),
    )

    if not targets:
        raise RuntimeError("No evaluation targets were selected.")

    print(f"Selected validation targets: {len(targets):,}")

    evaluate(
        retriever,
        loader,
        targets,
        positive_sources,
    )


if __name__ == "__main__":
    main()
