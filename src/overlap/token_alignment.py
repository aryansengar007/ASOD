import re
import unicodedata
from difflib import SequenceMatcher

TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


def tokenize_with_offsets(text: str) -> list[dict]:
    """
    Tokenize text while preserving character offsets into the original text.

    Token values are normalized using NFKC and casefold.
    Start and end offsets refer to the original, unmodified input.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    tokens = []

    for match in TOKEN_PATTERN.finditer(text):
        normalized = unicodedata.normalize(
            "NFKC",
            match.group(),
        ).casefold()

        tokens.append(
            {
                "token": normalized,
                "start": match.start(),
                "end": match.end(),
            }
        )

    return tokens


def find_exact_token_matches(
    source_text: str,
    target_text: str,
    source_base_offset: int = 0,
    target_base_offset: int = 0,
    min_match_tokens: int = 5,
) -> list[dict]:
    """
    Find matching contiguous token sequences between two text spans.

    Returned offsets are relative to the original documents when base
    offsets are supplied.

    This is an exact token-sequence baseline, not fuzzy alignment.
    """
    if (
        not isinstance(source_base_offset, int)
        or isinstance(source_base_offset, bool)
        or source_base_offset < 0
    ):
        raise ValueError("source_base_offset must be a non-negative integer")

    if (
        not isinstance(target_base_offset, int)
        or isinstance(target_base_offset, bool)
        or target_base_offset < 0
    ):
        raise ValueError("target_base_offset must be a non-negative integer")

    if (
        not isinstance(min_match_tokens, int)
        or isinstance(min_match_tokens, bool)
        or min_match_tokens < 1
    ):
        raise ValueError("min_match_tokens must be a positive integer")

    source_tokens = tokenize_with_offsets(source_text)
    target_tokens = tokenize_with_offsets(target_text)

    if not source_tokens or not target_tokens:
        return []

    source_values = [item["token"] for item in source_tokens]
    target_values = [item["token"] for item in target_tokens]

    matcher = SequenceMatcher(
        None,
        source_values,
        target_values,
        autojunk=False,
    )

    matches = []

    for block in matcher.get_matching_blocks():
        if block.size < min_match_tokens:
            continue

        source_first = source_tokens[block.a]
        source_last = source_tokens[block.a + block.size - 1]

        target_first = target_tokens[block.b]
        target_last = target_tokens[block.b + block.size - 1]

        matches.append(
            {
                "source_start": (source_base_offset + source_first["start"]),
                "source_end": (source_base_offset + source_last["end"]),
                "target_start": (target_base_offset + target_first["start"]),
                "target_end": (target_base_offset + target_last["end"]),
                "matched_token_count": block.size,
                "matched_text": source_text[source_first["start"] : source_last["end"]],
            }
        )

    return matches


def find_near_copy_matches(
    source_text: str,
    target_text: str,
    source_base_offset: int = 0,
    target_base_offset: int = 0,
    min_match_tokens: int = 5,
    max_gap_tokens: int = 5,
) -> list[dict]:
    """
    Find near-copy regions by grouping exact matching token blocks.

    Small insertions, deletions, and substitutions between matching
    blocks are permitted.

    Returned character offsets refer to the original documents when
    base offsets are supplied.

    This is a lexical near-copy baseline, not semantic paraphrase detection.
    """
    for name, value in (
        ("source_base_offset", source_base_offset),
        ("target_base_offset", target_base_offset),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")

    if (
        not isinstance(min_match_tokens, int)
        or isinstance(min_match_tokens, bool)
        or min_match_tokens < 1
    ):
        raise ValueError("min_match_tokens must be a positive integer")

    if (
        not isinstance(max_gap_tokens, int)
        or isinstance(max_gap_tokens, bool)
        or max_gap_tokens < 0
    ):
        raise ValueError("max_gap_tokens must be a non-negative integer")

    source_tokens = tokenize_with_offsets(source_text)
    target_tokens = tokenize_with_offsets(target_text)

    if not source_tokens or not target_tokens:
        return []

    source_values = [item["token"] for item in source_tokens]
    target_values = [item["token"] for item in target_tokens]

    matcher = SequenceMatcher(
        None,
        source_values,
        target_values,
        autojunk=False,
    )

    blocks = [block for block in matcher.get_matching_blocks() if block.size > 0]

    if not blocks:
        return []

    # Group matching blocks when only a small number of unmatched
    # tokens separates them in both documents.
    groups = []
    current_group = [blocks[0]]

    for block in blocks[1:]:
        previous = current_group[-1]

        source_gap = block.a - (previous.a + previous.size)
        target_gap = block.b - (previous.b + previous.size)

        if source_gap <= max_gap_tokens and target_gap <= max_gap_tokens:
            current_group.append(block)
        else:
            groups.append(current_group)
            current_group = [block]

    groups.append(current_group)

    results = []

    for group in groups:
        first = group[0]
        last = group[-1]

        source_token_start = first.a
        source_token_end = last.a + last.size

        target_token_start = first.b
        target_token_end = last.b + last.size

        matched_count = sum(block.size for block in group)

        if matched_count < min_match_tokens:
            continue

        source_region_count = source_token_end - source_token_start
        target_region_count = target_token_end - target_token_start

        unmatched_source = source_region_count - matched_count
        unmatched_target = target_region_count - matched_count

        source_first = source_tokens[source_token_start]
        source_last = source_tokens[source_token_end - 1]

        target_first = target_tokens[target_token_start]
        target_last = target_tokens[target_token_end - 1]

        denominator = max(
            source_region_count,
            target_region_count,
        )

        similarity = matched_count / denominator if denominator else 0.0

        results.append(
            {
                "source_start": (source_base_offset + source_first["start"]),
                "source_end": (source_base_offset + source_last["end"]),
                "target_start": (target_base_offset + target_first["start"]),
                "target_end": (target_base_offset + target_last["end"]),
                "matched_token_count": matched_count,
                "source_token_count": source_region_count,
                "target_token_count": target_region_count,
                "unmatched_source_tokens": unmatched_source,
                "unmatched_target_tokens": unmatched_target,
                "similarity": round(similarity, 4),
                "matched_text": source_text[source_first["start"] : source_last["end"]],
            }
        )

    return results
