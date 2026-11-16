import re
from typing import Any

DEFAULT_PASSAGE_SIZE = 200
DEFAULT_OVERLAP = 50
DEFAULT_MIN_LAST_PASSAGE = 50


def segment_document(
    document_id: str,
    text: str,
    passage_size: int = DEFAULT_PASSAGE_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    min_last_passage: int = DEFAULT_MIN_LAST_PASSAGE,
) -> list[dict[str, Any]]:
    """
    Segment original document text into overlapping passages.

    Character offsets are zero-based and end-exclusive.
    A short final increment is merged into the preceding passage.
    """

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("document_id must be a non-empty string")

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if passage_size <= 0:
        raise ValueError("passage_size must be positive")

    if overlap < 0 or overlap >= passage_size:
        raise ValueError("overlap must be non-negative and smaller than passage_size")

    if min_last_passage <= 0 or min_last_passage > passage_size:
        raise ValueError("min_last_passage must be between 1 and passage_size")

    tokens = list(re.finditer(r"\S+", text))

    if not tokens:
        return []

    stride = passage_size - overlap
    windows = []

    for start in range(0, len(tokens), stride):
        end = min(start + passage_size, len(tokens))
        windows.append([start, end])

        if end == len(tokens):
            break

    # Measure newly covered tokens, excluding overlap.
    if len(windows) > 1:
        previous_end = windows[-2][1]
        final_start, final_end = windows[-1]

        new_token_count = final_end - max(
            final_start,
            previous_end,
        )

        if new_token_count < min_last_passage:
            windows[-2][1] = final_end
            windows.pop()

    passages = []

    for start, end in windows:
        start_offset = tokens[start].start()
        end_offset = tokens[end - 1].end()

        passages.append(
            {
                "passage_id": (f"{document_id}::PASSAGE::{len(passages) + 1:06d}"),
                "document_id": document_id,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "token_count": end - start,
                "text": text[start_offset:end_offset],
            }
        )

    return passages
