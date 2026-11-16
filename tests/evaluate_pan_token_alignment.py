import argparse
import random
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.pan_loader import PanPC11Loader
from src.similarity.evaluate_pan_tfidf import (
    CORPUS_ROOT,
    METADATA_DIR,
    read_jsonl,
)
from src.overlap.token_alignment import (
    find_exact_token_matches,
    find_near_copy_matches,
    tokenize_with_offsets,
)

ANNOTATIONS_PATH = METADATA_DIR / "overlap_annotations.jsonl"


def get_length_buckets(records):
    """Divide the complete annotation dataset into four length quartiles."""

    ordered = sorted(
        records,
        key=lambda record: max(
            record["source_end"] - record["source_start"],
            record["target_end"] - record["target_start"],
        ),
    )

    return [
        ordered[i * len(ordered) // 4 : (i + 1) * len(ordered) // 4] for i in range(4)
    ]


def select_stratified_sample(records, sample_size, seed):
    """Select a reproducible sample across four span-length groups."""

    if sample_size > len(records):
        raise ValueError("Sample size exceeds available annotations.")

    buckets = get_length_buckets(records)

    rng = random.Random(seed)
    base, remainder = divmod(sample_size, 4)

    selected = []

    for i, bucket in enumerate(buckets):
        count = base + (1 if i < remainder else 0)
        selected.extend(rng.sample(bucket, count))

    return selected


def build_length_group_map(records):
    """Map every annotation ID to its full-dataset length quartile."""

    buckets = get_length_buckets(records)
    group_map = {}

    for i, bucket in enumerate(buckets, start=1):
        for annotation in bucket:
            group_map[annotation["annotation_id"]] = f"Q{i}"

    return group_map


def verify_exact_matches(matches, source_doc, target_doc):
    for match in matches:
        ss = match["source_start"]
        se = match["source_end"]
        ts = match["target_start"]
        te = match["target_end"]

        source_slice = source_doc[ss:se]
        target_slice = target_doc[ts:te]

        source_tokens = tokenize_with_offsets(source_slice)
        target_tokens = tokenize_with_offsets(target_slice)

        assert source_slice == match["matched_text"]
        assert len(source_tokens) == match["matched_token_count"]
        assert len(target_tokens) == match["matched_token_count"]

        assert [token["token"] for token in source_tokens] == [
            token["token"] for token in target_tokens
        ]


def verify_near_matches(matches, source_doc, target_doc):
    for match in matches:
        source_slice = source_doc[match["source_start"] : match["source_end"]]
        target_slice = target_doc[match["target_start"] : match["target_end"]]

        source_tokens = tokenize_with_offsets(source_slice)
        target_tokens = tokenize_with_offsets(target_slice)

        assert source_slice == match["matched_text"]
        assert len(source_tokens) == match["source_token_count"]
        assert len(target_tokens) == match["target_token_count"]

        assert (
            match["matched_token_count"] + match["unmatched_source_tokens"]
            == match["source_token_count"]
        )

        assert (
            match["matched_token_count"] + match["unmatched_target_tokens"]
            == match["target_token_count"]
        )


def evaluate(
    sample,
    loader,
    min_match_tokens,
    max_gap_tokens,
    length_group_map,
):
    totals = {
        "annotations": 0,
        "source_tokens": 0,
        "target_tokens": 0,
        "exact_matched_tokens": 0,
        "near_matched_tokens": 0,
        "exact_regions": 0,
        "near_regions": 0,
    }

    source_coverages = []
    target_coverages = []
    near_similarities = []

    group_stats = {
        f"Q{i}": {
            "annotations": 0,
            "source_tokens": 0,
            "target_tokens": 0,
            "exact_matched_tokens": 0,
            "near_matched_tokens": 0,
            "exact_regions": 0,
            "near_regions": 0,
            "source_coverages": [],
            "target_coverages": [],
            "near_similarities": [],
        }
        for i in range(1, 5)
    }

    exact_time = 0.0
    near_time = 0.0

    for index, annotation in enumerate(sample, start=1):
        source_doc = loader.load_text(annotation["source_document_id"])
        target_doc = loader.load_text(annotation["target_document_id"])

        ss = annotation["source_start"]
        se = annotation["source_end"]
        ts = annotation["target_start"]
        te = annotation["target_end"]

        if not (0 <= ss < se <= len(source_doc)):
            raise ValueError(f"Invalid source offsets: {annotation['annotation_id']}")

        if not (0 <= ts < te <= len(target_doc)):
            raise ValueError(f"Invalid target offsets: {annotation['annotation_id']}")

        source_span = source_doc[ss:se]
        target_span = target_doc[ts:te]

        source_count = len(tokenize_with_offsets(source_span))
        target_count = len(tokenize_with_offsets(target_span))

        if source_count == 0 or target_count == 0:
            raise ValueError(f"Empty token span: {annotation['annotation_id']}")

        start = time.perf_counter()

        exact_matches = find_exact_token_matches(
            source_span,
            target_span,
            source_base_offset=ss,
            target_base_offset=ts,
            min_match_tokens=min_match_tokens,
        )

        exact_time += time.perf_counter() - start

        start = time.perf_counter()

        near_matches = find_near_copy_matches(
            source_span,
            target_span,
            source_base_offset=ss,
            target_base_offset=ts,
            min_match_tokens=min_match_tokens,
            max_gap_tokens=max_gap_tokens,
        )

        near_time += time.perf_counter() - start

        verify_exact_matches(exact_matches, source_doc, target_doc)
        verify_near_matches(near_matches, source_doc, target_doc)

        exact_count = sum(match["matched_token_count"] for match in exact_matches)

        near_count = sum(match["matched_token_count"] for match in near_matches)

        if exact_count > min(source_count, target_count):
            raise AssertionError("Exact matched-token count exceeds span size.")

        if near_count > min(source_count, target_count):
            raise AssertionError("Near matched-token count exceeds span size.")

        # Overall totals.
        totals["annotations"] += 1
        totals["source_tokens"] += source_count
        totals["target_tokens"] += target_count
        totals["exact_matched_tokens"] += exact_count
        totals["near_matched_tokens"] += near_count
        totals["exact_regions"] += len(exact_matches)
        totals["near_regions"] += len(near_matches)

        source_coverage = near_count / source_count
        target_coverage = near_count / target_count

        source_coverages.append(source_coverage)
        target_coverages.append(target_coverage)

        annotation_similarities = [match["similarity"] for match in near_matches]
        near_similarities.extend(annotation_similarities)

        # Per-length-group totals.
        group_name = length_group_map[annotation["annotation_id"]]
        group = group_stats[group_name]

        group["annotations"] += 1
        group["source_tokens"] += source_count
        group["target_tokens"] += target_count
        group["exact_matched_tokens"] += exact_count
        group["near_matched_tokens"] += near_count
        group["exact_regions"] += len(exact_matches)
        group["near_regions"] += len(near_matches)

        group["source_coverages"].append(source_coverage)
        group["target_coverages"].append(target_coverage)
        group["near_similarities"].extend(annotation_similarities)

        if index % 25 == 0:
            print(f"Processed {index}/{len(sample)} annotations")

    length_group_results = {}

    for name, group in group_stats.items():
        if group["annotations"] == 0:
            continue

        length_group_results[name] = {
            "annotations": group["annotations"],
            "source_tokens": group["source_tokens"],
            "target_tokens": group["target_tokens"],
            "exact_matched_tokens": group["exact_matched_tokens"],
            "near_matched_tokens": group["near_matched_tokens"],
            "exact_regions": group["exact_regions"],
            "near_regions": group["near_regions"],
            "micro_source_coverage": (
                group["near_matched_tokens"] / group["source_tokens"]
            ),
            "micro_target_coverage": (
                group["near_matched_tokens"] / group["target_tokens"]
            ),
            "mean_annotation_source_coverage": statistics.mean(
                group["source_coverages"]
            ),
            "mean_annotation_target_coverage": statistics.mean(
                group["target_coverages"]
            ),
            "mean_near_region_similarity": (
                statistics.mean(group["near_similarities"])
                if group["near_similarities"]
                else 0.0
            ),
        }

    return {
        "totals": totals,
        "exact_runtime_seconds": exact_time,
        "near_runtime_seconds": near_time,
        "near_source_coverage": (
            totals["near_matched_tokens"] / totals["source_tokens"]
        ),
        "near_target_coverage": (
            totals["near_matched_tokens"] / totals["target_tokens"]
        ),
        "mean_annotation_source_coverage": statistics.mean(source_coverages),
        "mean_annotation_target_coverage": statistics.mean(target_coverages),
        "mean_near_region_similarity": (
            statistics.mean(near_similarities) if near_similarities else 0.0
        ),
        "length_groups": length_group_results,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-match-tokens", type=int, default=5)
    parser.add_argument("--max-gap-tokens", type=int, default=5)

    args = parser.parse_args()

    if args.sample_size < 4:
        parser.error("--sample-size must be at least 4")

    print("Loading PAN overlap annotations...")

    records = read_jsonl(ANNOTATIONS_PATH)

    print(f"Available annotations: {len(records)}")

    # Both operations use the same full-dataset quartile boundaries.
    sample = select_stratified_sample(
        records,
        args.sample_size,
        args.seed,
    )

    length_group_map = build_length_group_map(records)

    print(f"Selected annotations: {len(sample)}")
    print(f"Random seed: {args.seed}")
    print("Length strata: four approximately equal-sized groups")
    print("Initializing PAN loader...")

    loader = PanPC11Loader(CORPUS_ROOT)

    print("\nStarting alignment evaluation...")

    results = evaluate(
        sample,
        loader,
        args.min_match_tokens,
        args.max_gap_tokens,
        length_group_map,
    )

    totals = results["totals"]

    print("\n" + "=" * 55)
    print("PAN TOKEN ALIGNMENT EVALUATION")
    print("=" * 55)

    print(f"Annotations evaluated: {totals['annotations']}")
    print(f"Source tokens: {totals['source_tokens']}")
    print(f"Target tokens: {totals['target_tokens']}")

    print("\nEXACT ALIGNMENT")
    print(f"Matched tokens: {totals['exact_matched_tokens']}")
    print(f"Detected regions: {totals['exact_regions']}")

    print("\nNEAR-COPY ALIGNMENT")
    print(f"Matched tokens: {totals['near_matched_tokens']}")
    print(f"Detected regions: {totals['near_regions']}")

    print(f"Micro source coverage: " f"{results['near_source_coverage']:.2%}")
    print(f"Micro target coverage: " f"{results['near_target_coverage']:.2%}")

    print(
        "Mean annotation source coverage: "
        f"{results['mean_annotation_source_coverage']:.2%}"
    )
    print(
        "Mean annotation target coverage: "
        f"{results['mean_annotation_target_coverage']:.2%}"
    )
    print(
        "Mean near-region similarity: " f"{results['mean_near_region_similarity']:.4f}"
    )

    print("\nRESULTS BY ANNOTATION LENGTH GROUP")

    for name, group in results["length_groups"].items():
        print(f"\n{name}")
        print(f"Annotations: {group['annotations']}")
        print(f"Source tokens: {group['source_tokens']}")
        print(f"Target tokens: {group['target_tokens']}")
        print(f"Exact matched tokens: {group['exact_matched_tokens']}")
        print(f"Near matched tokens: {group['near_matched_tokens']}")
        print(f"Exact regions: {group['exact_regions']}")
        print(f"Near regions: {group['near_regions']}")

        print(f"Micro source coverage: " f"{group['micro_source_coverage']:.2%}")
        print(f"Micro target coverage: " f"{group['micro_target_coverage']:.2%}")
        print(
            "Mean annotation source coverage: "
            f"{group['mean_annotation_source_coverage']:.2%}"
        )
        print(
            "Mean annotation target coverage: "
            f"{group['mean_annotation_target_coverage']:.2%}"
        )
        print(
            "Mean near-region similarity: "
            f"{group['mean_near_region_similarity']:.4f}"
        )

    print("\nRUNTIME")
    print(f"Exact: {results['exact_runtime_seconds']:.2f} seconds")
    print(f"Near-copy: {results['near_runtime_seconds']:.2f} seconds")

    print("\nOFFSET AND TOKEN-COUNT VERIFICATION")
    print("PASS: all evaluated match boundaries and counts verified.")


if __name__ == "__main__":
    main()
