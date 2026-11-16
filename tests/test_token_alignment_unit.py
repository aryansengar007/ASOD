import pytest

from src.overlap.token_alignment import (
    tokenize_with_offsets,
    find_exact_token_matches,
    find_near_copy_matches,
)

# ---------------------------------------------------------
# TOKENIZATION TESTS
# ---------------------------------------------------------


def test_tokenization_preserves_original_offsets():
    text = "Hello, WORLD! 123"

    tokens = tokenize_with_offsets(text)

    assert [item["token"] for item in tokens] == [
        "hello",
        "world",
        "123",
    ]

    assert text[tokens[0]["start"] : tokens[0]["end"]] == "Hello"
    assert text[tokens[1]["start"] : tokens[1]["end"]] == "WORLD"
    assert text[tokens[2]["start"] : tokens[2]["end"]] == "123"


def test_tokenization_normalizes_unicode():
    tokens = tokenize_with_offsets("CAFÉ ＡＢＣ")

    assert [item["token"] for item in tokens] == [
        "café",
        "abc",
    ]


def test_tokenization_rejects_non_string():
    with pytest.raises(TypeError):
        tokenize_with_offsets(123)


def test_tokenization_empty_text():
    assert tokenize_with_offsets("") == []


# ---------------------------------------------------------
# EXACT MATCH TESTS
# ---------------------------------------------------------


def test_exact_matching_identical_text():
    text = "alpha beta gamma delta epsilon"

    matches = find_exact_token_matches(
        text,
        text,
        min_match_tokens=3,
    )

    assert len(matches) == 1
    assert matches[0]["matched_token_count"] == 5
    assert matches[0]["matched_text"] == text


def test_exact_matching_with_base_offsets():
    source = "prefix alpha beta gamma suffix"
    target = "other alpha beta gamma ending"

    matches = find_exact_token_matches(
        source,
        target,
        source_base_offset=100,
        target_base_offset=200,
        min_match_tokens=3,
    )

    assert len(matches) == 1

    match = matches[0]

    assert match["source_start"] == 107
    assert match["source_end"] == 123
    assert match["target_start"] == 206
    assert match["target_end"] == 222
    assert match["matched_token_count"] == 3


def test_exact_matching_ignores_short_matches():
    matches = find_exact_token_matches(
        "alpha beta gamma delta",
        "alpha beta gamma delta",
        min_match_tokens=5,
    )

    assert matches == []


def test_exact_matching_empty_input():
    assert (
        find_exact_token_matches(
            "",
            "alpha beta gamma",
        )
        == []
    )


# ---------------------------------------------------------
# NEAR-COPY TESTS
# ---------------------------------------------------------


def test_near_copy_exact_sequence():
    text = "alpha beta gamma delta epsilon"

    matches = find_near_copy_matches(
        text,
        text,
        min_match_tokens=3,
    )

    assert len(matches) == 1

    match = matches[0]

    assert match["matched_token_count"] == 5
    assert match["source_token_count"] == 5
    assert match["target_token_count"] == 5
    assert match["similarity"] == 1.0


def test_near_copy_small_insertion():
    matches = find_near_copy_matches(
        "alpha beta gamma delta epsilon",
        "alpha beta extra gamma delta epsilon",
        min_match_tokens=3,
        max_gap_tokens=2,
    )

    assert len(matches) == 1

    match = matches[0]

    assert match["matched_token_count"] == 5
    assert match["source_token_count"] == 5
    assert match["target_token_count"] == 6
    assert match["unmatched_source_tokens"] == 0
    assert match["unmatched_target_tokens"] == 1


def test_near_copy_large_gap_splits_regions():
    matches = find_near_copy_matches(
        "alpha beta gamma one two three four five delta epsilon zeta",
        "alpha beta gamma x y z u v delta epsilon zeta",
        min_match_tokens=3,
        max_gap_tokens=2,
    )

    assert len(matches) == 2


def test_near_copy_repeated_tokens():
    text = "the the the alpha beta gamma the the the"

    matches = find_near_copy_matches(
        text,
        text,
        min_match_tokens=3,
        max_gap_tokens=2,
    )

    assert len(matches) == 1
    assert matches[0]["matched_token_count"] == 9
    assert matches[0]["similarity"] == 1.0


def test_near_copy_no_matching_content():
    matches = find_near_copy_matches(
        "alpha beta gamma delta",
        "one two three four",
        min_match_tokens=3,
    )

    assert matches == []


def test_near_copy_preserves_base_offsets():
    matches = find_near_copy_matches(
        "prefix alpha beta gamma suffix",
        "other alpha beta gamma ending",
        source_base_offset=100,
        target_base_offset=200,
        min_match_tokens=3,
    )

    assert len(matches) == 1

    match = matches[0]

    assert match["source_start"] == 107
    assert match["source_end"] == 123
    assert match["target_start"] == 206
    assert match["target_end"] == 222


# ---------------------------------------------------------
# MATCH ALIGNMENT VERIFICATION
# ---------------------------------------------------------


def test_exact_match_tokens_agree_at_reported_offsets():
    source = "start alpha beta gamma end"
    target = "other alpha beta gamma ending"

    matches = find_exact_token_matches(
        source,
        target,
        min_match_tokens=3,
    )

    assert matches

    for match in matches:
        source_tokens = tokenize_with_offsets(
            source[match["source_start"] : match["source_end"]]
        )

        target_tokens = tokenize_with_offsets(
            target[match["target_start"] : match["target_end"]]
        )

        assert [item["token"] for item in source_tokens] == [
            item["token"] for item in target_tokens
        ]


def test_near_copy_region_counts_match_reported_offsets():
    source = "alpha beta gamma delta epsilon"
    target = "alpha beta extra gamma delta epsilon"

    matches = find_near_copy_matches(
        source,
        target,
        min_match_tokens=3,
    )

    assert matches

    for match in matches:
        source_region = tokenize_with_offsets(
            source[match["source_start"] : match["source_end"]]
        )

        target_region = tokenize_with_offsets(
            target[match["target_start"] : match["target_end"]]
        )

        assert len(source_region) == match["source_token_count"]
        assert len(target_region) == match["target_token_count"]

        assert (
            match["unmatched_source_tokens"]
            == match["source_token_count"] - match["matched_token_count"]
        )

        assert (
            match["unmatched_target_tokens"]
            == match["target_token_count"] - match["matched_token_count"]
        )


# ---------------------------------------------------------
# ARGUMENT VALIDATION
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [-1, 1.5, True, "5"],
)
def test_exact_matching_rejects_invalid_minimum(value):
    with pytest.raises(ValueError):
        find_exact_token_matches(
            "alpha beta gamma",
            "alpha beta gamma",
            min_match_tokens=value,
        )


@pytest.mark.parametrize(
    "value",
    [-1, 1.5, True, "5"],
)
def test_near_copy_rejects_invalid_gap(value):
    with pytest.raises(ValueError):
        find_near_copy_matches(
            "alpha beta gamma",
            "alpha beta gamma",
            max_gap_tokens=value,
        )


@pytest.mark.parametrize(
    "value",
    [-1, 1.5, True, "100"],
)
def test_near_copy_rejects_invalid_base_offset(value):
    with pytest.raises(ValueError):
        find_near_copy_matches(
            "alpha beta gamma",
            "alpha beta gamma",
            source_base_offset=value,
        )
