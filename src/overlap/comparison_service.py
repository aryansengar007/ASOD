from itertools import combinations

from src.overlap.token_alignment import (
    find_exact_token_matches,
    find_near_copy_matches,
)
from src.preprocessing.document_loader import LoadedDocument


def compare_documents(
    documents: list[LoadedDocument],
    min_match_tokens: int = 5,
    max_gap_tokens: int = 5,
) -> list[dict]:
    """
    Compare every unique pair of uploaded documents.

    Returned offsets refer to the extracted text stored in each
    LoadedDocument. Exact and near-copy evidence are kept separate.
    """

    if not isinstance(documents, list):
        raise TypeError("documents must be a list")

    if len(documents) < 2:
        raise ValueError("At least two documents are required.")

    if any(not isinstance(doc, LoadedDocument) for doc in documents):
        raise TypeError("Every item must be a LoadedDocument.")

    if (
        not isinstance(min_match_tokens, int)
        or isinstance(min_match_tokens, bool)
        or min_match_tokens < 1
    ):
        raise ValueError("min_match_tokens must be a positive integer.")

    if (
        not isinstance(max_gap_tokens, int)
        or isinstance(max_gap_tokens, bool)
        or max_gap_tokens < 0
    ):
        raise ValueError("max_gap_tokens must be a non-negative integer.")

    results = []

    for (source_index, source), (target_index, target) in combinations(
        enumerate(documents), 2
    ):
        exact_results = find_exact_token_matches(
            source.text,
            target.text,
            min_match_tokens=min_match_tokens,
        )

        near_results = find_near_copy_matches(
            source.text,
            target.text,
            min_match_tokens=min_match_tokens,
            max_gap_tokens=max_gap_tokens,
        )

        exact_evidence = []

        for match in exact_results:
            exact_evidence.append(
                {
                    **match,
                    "source_text": source.text[
                        match["source_start"] : match["source_end"]
                    ],
                    "target_text": target.text[
                        match["target_start"] : match["target_end"]
                    ],
                    "overlap_type": "exact_reuse",
                }
            )

        near_evidence = []

        for match in near_results:
            # Exact regions are already reported separately.
            if (
                match["unmatched_source_tokens"] == 0
                and match["unmatched_target_tokens"] == 0
            ):
                continue

            near_evidence.append(
                {
                    **match,
                    "source_text": source.text[
                        match["source_start"] : match["source_end"]
                    ],
                    "target_text": target.text[
                        match["target_start"] : match["target_end"]
                    ],
                    "overlap_type": "near_copy",
                }
            )

        results.append(
            {
                "pair_id": (f"PAIR-{source_index + 1:04d}-" f"{target_index + 1:04d}"),
                "source_document": source.filename,
                "target_document": target.filename,
                "source_document_index": source_index,
                "target_document_index": target_index,
                "exact_matches": exact_evidence,
                "near_copy_matches": near_evidence,
                "exact_match_count": len(exact_evidence),
                "near_copy_region_count": len(near_evidence),
            }
        )

    return results
