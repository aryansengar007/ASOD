import pytest
from fastapi.testclient import TestClient

from src.api.main import app, MAX_FILE_SIZE_BYTES

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_compare_endpoint_with_exact_overlap():
    shared = b"the quick brown fox jumps over the lazy dog"

    files = [
        (
            "files",
            (
                "first.txt",
                b"Preface. " + shared + b". Ending.",
                "text/plain",
            ),
        ),
        (
            "files",
            (
                "second.txt",
                b"Different opening. " + shared + b". Conclusion.",
                "text/plain",
            ),
        ),
    ]

    response = client.post("/api/compare", files=files)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["document_count"] == 2
    assert data["pair_count"] == 1
    assert len(data["documents"]) == 2

    pair = data["comparisons"][0]

    assert pair["exact_match_count"] >= 1
    assert pair["near_copy_region_count"] == 0
    assert pair["exact_matches"][0]["source_text"] == shared.decode()


def test_compare_endpoint_rejects_one_document():
    response = client.post(
        "/api/compare",
        files=[
            (
                "files",
                ("first.txt", b"some document text", "text/plain"),
            )
        ],
    )

    assert response.status_code == 400
    assert "at least two" in response.json()["detail"].lower()


def test_compare_endpoint_rejects_unsupported_file():
    files = [
        (
            "files",
            ("first.txt", b"some document text", "text/plain"),
        ),
        (
            "files",
            ("second.pdf", b"fake pdf content", "application/pdf"),
        ),
    ]

    response = client.post("/api/compare", files=files)

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_compare_endpoint_rejects_oversized_file():
    oversized_content = b"a" * (MAX_FILE_SIZE_BYTES + 1)

    files = [
        (
            "files",
            ("first.txt", oversized_content, "text/plain"),
        ),
        (
            "files",
            ("second.txt", b"some document text", "text/plain"),
        ),
    ]

    response = client.post("/api/compare", files=files)

    assert response.status_code == 413
    assert "10 MB" in response.json()["detail"]


def test_compare_endpoint_rejects_more_than_maximum_files():
    files = [
        (
            "files",
            (
                f"document_{index}.txt",
                b"alpha beta gamma delta epsilon",
                "text/plain",
            ),
        )
        for index in range(11)
    ]

    response = client.post("/api/compare", files=files)

    assert response.status_code == 400
    assert "maximum of 10" in response.json()["detail"]
