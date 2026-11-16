import re

from src.similarity.passage_segmentation import segment_document

cases = [40, 200, 201, 350, 351, 451, 501, 1000]

total_passages = 0

for n in cases:
    text = " ".join(f"word{i}" for i in range(n))
    tokens = list(re.finditer(r"\S+", text))

    passages = segment_document(
        f"TEST::{n}",
        text,
    )

    assert passages[0]["start_offset"] == 0
    assert passages[-1]["end_offset"] == tokens[-1].end()

    for passage in passages:
        start = passage["start_offset"]
        end = passage["end_offset"]

        assert text[start:end] == passage["text"]

        actual_count = sum(1 for token in tokens if start <= token.start() < end)

        assert actual_count == passage["token_count"]

    for first, second in zip(passages, passages[1:]):
        overlap_count = sum(
            1
            for token in tokens
            if (
                first["start_offset"] <= token.start() < first["end_offset"]
                and second["start_offset"] <= token.start() < second["end_offset"]
            )
        )

        assert overlap_count == 50, f"Incorrect overlap for {n} tokens: {overlap_count}"

    print(
        f"PASS: {n} tokens | "
        f"{len(passages)} passages | "
        "offsets and overlap valid"
    )

    total_passages += len(passages)

print(f"\nTotal passages tested: {total_passages}")
print("ALL SEGMENTATION TESTS PASSED")
