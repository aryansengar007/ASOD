import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.overlap.token_alignment import (
    find_near_copy_matches,
    tokenize_with_offsets,
)


def run_case(
    name,
    source,
    target,
    expected_regions,
    min_match_tokens=3,
    max_gap_tokens=2,
):
    matches = find_near_copy_matches(
        source,
        target,
        min_match_tokens=min_match_tokens,
        max_gap_tokens=max_gap_tokens,
    )

    print(f"\n{name}")
    print("Detected regions:", len(matches))
    print("Expected regions:", expected_regions)

    for index, match in enumerate(matches, start=1):
        print(
            f"  Region {index}: "
            f"matched={match['matched_token_count']}, "
            f"source={match['source_token_count']}, "
            f"target={match['target_token_count']}, "
            f"similarity={match['similarity']}"
        )

    assert len(matches) == expected_regions, (
        f"{name}: expected {expected_regions} regions, " f"got {len(matches)}"
    )

    for match in matches:
        source_region = source[match["source_start"] : match["source_end"]]
        target_region = target[match["target_start"] : match["target_end"]]

        source_count = len(tokenize_with_offsets(source_region))
        target_count = len(tokenize_with_offsets(target_region))

        assert source_count == match["source_token_count"]
        assert target_count == match["target_token_count"]

    print("PASS")


def main():
    # One continuous exact match.
    run_case(
        "CASE 1 - Exact sequence",
        "alpha beta gamma delta epsilon zeta",
        "alpha beta gamma delta epsilon zeta",
        expected_regions=1,
    )

    # A small insertion between matching blocks.
    run_case(
        "CASE 2 - Small insertion",
        "alpha beta gamma delta epsilon zeta",
        "alpha beta gamma extra delta epsilon zeta",
        expected_regions=1,
    )

    # A gap larger than the configured limit should split regions.
    run_case(
        "CASE 3 - Large gap",
        "alpha beta gamma one two three four five delta epsilon zeta",
        "alpha beta gamma x y z u v delta epsilon zeta",
        expected_regions=2,
    )

    # Different gap lengths, both within the configured limit.
    # This exposes potentially over-permissive grouping.
    run_case(
        "CASE 4 - Unequal gaps",
        "alpha beta gamma delta epsilon zeta",
        "alpha beta gamma x y delta epsilon zeta",
        expected_regions=1,
    )

    # Several short matching blocks can collectively pass the
    # minimum matched-token threshold.
    run_case(
        "CASE 5 - Combined short blocks",
        "a b c d e f g h i",
        "a x c y e z g w i",
        expected_regions=1,
        min_match_tokens=5,
        max_gap_tokens=1,
    )

    # No sufficiently long matching sequence.
    run_case(
        "CASE 6 - Insufficient matches",
        "alpha beta gamma delta epsilon",
        "one two three four five",
        expected_regions=0,
    )

    # Repeated tokens with an insertion.
    run_case(
        "CASE 8 - Repeated tokens with insertion",
        "the the alpha beta the the gamma delta",
        "the the alpha extra beta the the gamma delta",
        expected_regions=1,
        min_match_tokens=3,
        max_gap_tokens=2,
    )

    # Repeated tokens with a deletion.
    run_case(
        "CASE 9 - Repeated tokens with deletion",
        "the the alpha beta the the gamma delta",
        "the alpha beta the the gamma delta",
        expected_regions=1,
        min_match_tokens=3,
        max_gap_tokens=2,
    )

    print("\nAll synthetic alignment cases passed.")


if __name__ == "__main__":
    main()
