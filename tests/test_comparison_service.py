import pytest

from src.overlap.comparison_service import compare_documents
from src.preprocessing.document_loader import LoadedDocument


def make_document(filename, text):
    return LoadedDocument(
        filename=filename,
        file_type="txt",
        text=text,
        char_count=len(text),
        word_count=len(text.split()),
    )


def test_compares_two_documents_with_exact_overlap():
    shared = "the quick brown fox jumps over the lazy dog"

    source = make_document(
        "source.txt",
        f"Preface. {shared}. Ending.",
    )
    target = make_document(
        "target.txt",
        f"Different opening. {shared}. Conclusion.",
    )

    results = compare_documents([source, target])

    assert len(results) == 1

    pair = results[0]

    assert pair["source_document"] == "source.txt"
    assert pair["target_document"] == "target.txt"
    assert pair["exact_match_count"] >= 1
    assert pair["near_copy_region_count"] == 0

    match = pair["exact_matches"][0]

    assert match["overlap_type"] == "exact_reuse"
    assert match["source_text"] == shared
    assert match["target_text"] == shared

    assert source.text[match["source_start"] : match["source_end"]] == shared
    assert target.text[match["target_start"] : match["target_end"]] == shared


def test_detects_near_copy_with_insertion():
    source = make_document(
        "source.txt",
        "alpha beta gamma delta epsilon zeta eta theta",
    )
    target = make_document(
        "target.txt",
        "alpha beta gamma inserted delta epsilon zeta eta theta",
    )

    results = compare_documents([source, target])

    pair = results[0]

    assert pair["near_copy_region_count"] >= 1

    match = pair["near_copy_matches"][0]

    assert match["overlap_type"] == "near_copy"
    assert match["unmatched_target_tokens"] == 1
    assert match["similarity"] < 1.0

    assert (
        target.text[match["target_start"] : match["target_end"]] == match["target_text"]
    )


def test_compares_all_unique_document_pairs():
    documents = [
        make_document("one.txt", "alpha beta gamma delta epsilon"),
        make_document("two.txt", "alpha beta gamma delta epsilon"),
        make_document("three.txt", "one two three four five"),
    ]

    results = compare_documents(documents)

    assert len(results) == 3


def test_rejects_fewer_than_two_documents():
    document = make_document("one.txt", "some text")

    with pytest.raises(ValueError, match="At least two"):
        compare_documents([document])


def test_rejects_invalid_document_items():
    with pytest.raises(TypeError, match="LoadedDocument"):
        compare_documents(["first.txt", "second.txt"])


def test_rejects_invalid_minimum_match_tokens():
    documents = [
        make_document("one.txt", "some text"),
        make_document("two.txt", "some text"),
    ]

    with pytest.raises(ValueError, match="min_match_tokens"):
        compare_documents(documents, min_match_tokens=0)


def test_rejects_invalid_maximum_gap_tokens():
    documents = [
        make_document("one.txt", "some text"),
        make_document("two.txt", "some text"),
    ]

    with pytest.raises(ValueError, match="max_gap_tokens"):
        compare_documents(documents, max_gap_tokens=-1)


def test_no_overlap_returns_empty_evidence():
    documents = [
        make_document("one.txt", "apple orange banana mango"),
        make_document("two.txt", "computer science machine learning"),
    ]

    results = compare_documents(documents)

    assert results[0]["exact_matches"] == []
    assert results[0]["near_copy_matches"] == []
    assert results[0]["exact_match_count"] == 0
    assert results[0]["near_copy_region_count"] == 0
