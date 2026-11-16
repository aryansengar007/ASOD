
import json
from itertools import chain
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from scipy.sparse import csr_matrix, load_npz, save_npz
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize


class StreamingTfidfRetriever:
    """
    Memory-aware TF-IDF retrieval using feature hashing.

    Document frequency is calculated incrementally.
    Reference vectors are stored as sparse disk-backed chunks.

    Original PAN text must be supplied through a loader that returns
    normalized text. Never use normalized text for PAN span offsets.
    """

    def __init__(
        self,
        n_features: int = 2**22,
        batch_size: int = 4,
        chunk_size: int = 128,
    ):
        if n_features < 1:
            raise ValueError("n_features must be positive")

        if batch_size < 1 or chunk_size < 1:
            raise ValueError("Batch and chunk sizes must be positive")

        self.n_features = n_features
        self.batch_size = batch_size
        self.chunk_size = chunk_size

        self.vectorizer = HashingVectorizer(
            n_features=n_features,
            analyzer="word",
            ngram_range=(1, 2),
            alternate_sign=False,
            norm=None,
            lowercase=False,
            strip_accents="unicode",
            dtype=np.float32,
        )

        self.idf = None
        self.index_dir = None
        self.chunks = []
        self.reference_ids = []
        self.is_fitted = False

    def fit(
        self,
        reference_ids: Sequence[str],
        training_ids: Sequence[str],
        load_text: Callable[[str], str],
        index_dir: Path,
    ) -> "StreamingTfidfRetriever":
        """
        Calculate IDF from reference + training documents.

        Build the reference index in sparse chunks.

        load_text(document_id) must return normalized text.
        Validation and test IDs must not be included.
        """

        reference_ids = list(reference_ids)
        training_ids = list(training_ids)

        if not reference_ids:
            raise ValueError("Reference corpus cannot be empty")

        if not training_ids:
            raise ValueError("Training documents cannot be empty")

        all_ids = reference_ids + training_ids

        if any(not isinstance(doc_id, str) or not doc_id for doc_id in all_ids):
            raise ValueError("Document IDs must be non-empty strings")

        if len(set(reference_ids)) != len(reference_ids):
            raise ValueError("Reference document IDs must be unique")

        if len(set(training_ids)) != len(training_ids):
            raise ValueError("Training document IDs must be unique")

        if set(reference_ids).intersection(training_ids):
            raise ValueError("Reference and training IDs must be disjoint")

        index_dir = Path(index_dir)

        if index_dir.exists() and any(index_dir.iterdir()):
            raise FileExistsError(
                f"Index directory is not empty: {index_dir}"
            )

        index_dir.mkdir(parents=True, exist_ok=True)

        # PASS 1: Calculate document frequency incrementally.
        document_frequency = np.zeros(
            self.n_features,
            dtype=np.uint32,
        )

        document_count = len(all_ids)

        for position, document_id in enumerate(all_ids, start=1):
            text = load_text(document_id)

            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"Empty or invalid text: {document_id}"
                )

            document_vector = self.vectorizer.transform([text])

            # Each occupied feature contributes once per document.
            document_frequency[document_vector.indices] += 1

            if position % 500 == 0:
                print(
                    f"Document-frequency pass: "
                    f"{position}/{document_count}"
                )

        # Smoothed IDF.
        self.idf = (
            np.log(
                (1.0 + document_count)
                / (1.0 + document_frequency)
            ) + 1.0
        ).astype(np.float32)

        np.save(index_dir / "idf.npy", self.idf)

        # PASS 2: Build reference vectors in sparse chunks.
        self.chunks = []
        self.reference_ids = list(reference_ids)

        for chunk_number, start in enumerate(
            range(0, len(reference_ids), self.chunk_size)
        ):
            chunk_ids = reference_ids[
                start:start + self.chunk_size
            ]

            chunk_texts = [
                load_text(document_id)
                for document_id in chunk_ids
            ]

            if any(
                not isinstance(text, str) or not text.strip()
                for text in chunk_texts
            ):
                raise ValueError(
                    f"Invalid text in reference chunk {chunk_number}"
                )

            matrix = self.vectorizer.transform(chunk_texts).tocsr()

            matrix = matrix.multiply(self.idf).tocsr()
            matrix = normalize(matrix, norm="l2", copy=False)

            filename = f"reference_{chunk_number:04d}.npz"

            save_npz(
                index_dir / filename,
                matrix,
                compressed=True,
            )

            self.chunks.append({
                "filename": filename,
                "document_ids": chunk_ids,
            })

            print(
                f"Reference index: "
                f"{min(start + len(chunk_ids), len(reference_ids))}"
                f"/{len(reference_ids)}"
            )

        # Persist configuration and document ordering.
        manifest = {
            "n_features": self.n_features,
            "batch_size": self.batch_size,
            "chunk_size": self.chunk_size,
            "document_count": document_count,
            "reference_count": len(reference_ids),
            "training_count": len(training_ids),
            "reference_ids": reference_ids,
            "chunks": self.chunks,
        }

        with (index_dir / "manifest.json").open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(manifest, file, indent=2)

        self.index_dir = index_dir
        self.is_fitted = True

        return self

    @classmethod
    def load(cls, index_dir: Path) -> "StreamingTfidfRetriever":
        """Load an existing persisted reference index."""

        index_dir = Path(index_dir)

        manifest_path = index_dir / "manifest.json"
        idf_path = index_dir / "idf.npy"

        if not manifest_path.is_file() or not idf_path.is_file():
            raise FileNotFoundError("Incomplete TF-IDF index")

        with manifest_path.open(encoding="utf-8") as file:
            manifest = json.load(file)

        retriever = cls(
            n_features=manifest["n_features"],
            batch_size=manifest["batch_size"],
            chunk_size=manifest["chunk_size"],
        )

        retriever.idf = np.load(idf_path)
        retriever.chunks = manifest["chunks"]
        retriever.reference_ids = manifest["reference_ids"]
        retriever.index_dir = index_dir

        retriever.is_fitted = True

        return retriever

    def retrieve(
        self,
        query_texts: Sequence[str],
        top_k: int = 10,
    ) -> list[list[dict]]:
        """
        Retrieve the highest-scoring reference documents.

        Only positive-similarity candidates are returned.
        Ties are resolved deterministically by document ID.
        """

        if not self.is_fitted:
            raise RuntimeError("Retriever must be fitted or loaded")

        if top_k < 1:
            raise ValueError("top_k must be positive")

        if any(
            not isinstance(text, str) or not text.strip()
            for text in query_texts
        ):
            raise ValueError("Query texts must be non-empty strings")

        results = []

        for start in range(0, len(query_texts), self.batch_size):
            batch_texts = query_texts[
                start:start + self.batch_size
            ]

            query_matrix = self.vectorizer.transform(batch_texts)
            query_matrix = query_matrix.multiply(self.idf).tocsr()
            query_matrix = normalize(
                query_matrix,
                norm="l2",
                copy=False,
            )

            batch_candidates = [
                [] for _ in batch_texts
            ]

            for chunk in self.chunks:
                reference_matrix = load_npz(
                    self.index_dir / chunk["filename"]
                ).tocsr()

                similarity = (
                    query_matrix @ reference_matrix.T
                ).toarray()

                for row_index, scores in enumerate(similarity):
                    for column_index, score in enumerate(scores):
                        if score > 0:
                            batch_candidates[row_index].append({
                                "document_id": chunk["document_ids"][
                                    column_index
                                ],
                                "similarity_score": float(
                                    np.clip(score, 0.0, 1.0)
                                ),
                            })

                del reference_matrix
                del similarity

            for candidates in batch_candidates:
                candidates.sort(
                    key=lambda item: (
                        -item["similarity_score"],
                        item["document_id"],
                    )
                )

                results.append(candidates[:top_k])

        return results

    def get_statistics(self) -> dict:
        """Return persisted index statistics."""

        if not self.is_fitted:
            raise RuntimeError("Retriever has not been fitted")

        return {
            "reference_documents": len(self.reference_ids),
            "feature_dimensions": self.n_features,
            "reference_chunks": len(self.chunks),
            "chunk_size": self.chunk_size,
            "batch_size": self.batch_size,
            "index_directory": str(self.index_dir),
        }
