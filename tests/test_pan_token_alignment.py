import sys
from pathlib import Path

# Make the ASOD project root available for imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.pan_loader import PanPC11Loader
from src.similarity.evaluate_pan_tfidf import CORPUS_ROOT, read_jsonl
from src.overlap.token_alignment import (
    find_exact_token_matches,
    find_near_copy_matches,
    tokenize_with_offsets,
)

ANNOTATIONS_PATH = (
    PROJECT_ROOT / "benchmark" / "metadata" / "pan_pc11" / "overlap_annotations.jsonl"
)

ANNOTATION_ID = "PAN_PC11::suspicious-document05894.txt::0001"
MIN_MATCH_TOKENS = 5


def main():
    annotations = read_jsonl(ANNOTATIONS_PATH)

    annotation = next(
        (item for item in annotations if item["annotation_id"] == ANNOTATION_ID),
        None,
    )

    if annotation is None:
        raise RuntimeError(f"PAN annotation not found: {ANNOTATION_ID}")

    loader = PanPC11Loader(CORPUS_ROOT)

    source_text = loader.load_text(annotation["source_document_id"])
    target_text = loader.load_text(annotation["target_document_id"])

    source_start = annotation["source_start"]
    source_end = annotation["source_end"]
    target_start = annotation["target_start"]
    target_end = annotation["target_end"]

    source_span = source_text[source_start:source_end]
    target_span = target_text[target_start:target_end]

    matches = find_exact_token_matches(
        source_span,
        target_span,
        source_base_offset=source_start,
        target_base_offset=target_start,
        min_match_tokens=MIN_MATCH_TOKENS,
    )
    near_matches = find_near_copy_matches(
        source_span,
        target_span,
        source_base_offset=source_start,
        target_base_offset=target_start,
        min_match_tokens=5,
        max_gap_tokens=5,
    )

    print("\nNEAR-COPY RESULTS")
    print("Detected regions:", len(near_matches))

    for index, match in enumerate(near_matches, start=1):
        print(f"\nNear-copy region {index}")
        print("Matched tokens:", match["matched_token_count"])
        print("Similarity:", match["similarity"])
        print("Unmatched source tokens:", match["unmatched_source_tokens"])
        print("Unmatched target tokens:", match["unmatched_target_tokens"])
        print("Source offsets:", match["source_start"], match["source_end"])
        print("Target offsets:", match["target_start"], match["target_end"])

    source_token_count = len(tokenize_with_offsets(source_span))
    target_token_count = len(tokenize_with_offsets(target_span))

    matched_token_count = sum(match["matched_token_count"] for match in matches)

    print(f"PAN annotation: {ANNOTATION_ID}")
    print(f"Detected exact token sequences: {len(matches)}")
    print(f"Matched tokens: {matched_token_count}")

    for index, match in enumerate(matches, start=1):
        print(f"\nMatch {index}")
        print("Tokens:", match["matched_token_count"])
        print("Source offsets:", match["source_start"], match["source_end"])
        print("Target offsets:", match["target_start"], match["target_end"])
        print("Text:", repr(match["matched_text"]))

    print("\nCoverage")
    print("Source tokens:", source_token_count)
    print("Target tokens:", target_token_count)
    print("Matched tokens:", matched_token_count)

    if source_token_count:
        print(
            "Source coverage:",
            round(matched_token_count / source_token_count * 100, 2),
            "%",
        )

    if target_token_count:
        print(
            "Target coverage:",
            round(matched_token_count / target_token_count * 100, 2),
            "%",
        )

    print("\nOffset verification")

    for match in matches:
        ss = match["source_start"] - source_start
        se = match["source_end"] - source_start
        ts = match["target_start"] - target_start
        te = match["target_end"] - target_start

        source_tokens = [
            item["token"] for item in tokenize_with_offsets(source_span[ss:se])
        ]

        target_tokens = [
            item["token"] for item in tokenize_with_offsets(target_span[ts:te])
        ]

        assert source_tokens == target_tokens, f"Token mismatch in match: {match}"

    print(
        "PASS: all matched token sequences agree "
        "at their reported original-text offsets."
    )
    print("\nNear-copy offset verification")

    for match in near_matches:
        ss = match["source_start"] - source_start
        se = match["source_end"] - source_start
        ts = match["target_start"] - target_start
        te = match["target_end"] - target_start

        source_region = tokenize_with_offsets(source_span[ss:se])
        target_region = tokenize_with_offsets(target_span[ts:te])

        assert source_region
        assert target_region

        assert len(source_region) == match["source_token_count"]
        assert len(target_region) == match["target_token_count"]

        assert source_start + ss + source_region[0]["start"] == match["source_start"]
        assert target_start + ts + target_region[0]["start"] == match["target_start"]

        assert source_start + ss + source_region[-1]["end"] == match["source_end"]
        assert target_start + ts + target_region[-1]["end"] == match["target_end"]

    print("PASS: all near-copy region boundaries and token counts verified.")


if __name__ == "__main__":
    main()
