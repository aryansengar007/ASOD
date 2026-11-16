
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TfidfRetriever:
    """
    Sparse TF-IDF document retrieval using word unigrams and bigrams.

    Fit the vocabulary and IDF weights on reference documents and
    training documents only. Validation and test documents must be
    transformed, not included during fitting.
    """

    def __init__(
        self,
        min_df: int = 2,
        max_df: float = 0.95,
        batch_size: int = 16,
    ):
        if min_df < 1:
            raise ValueError("min_df must be at least 1")

        if not 0 < max_df <= 1:
            raise ValueError("max_df must be in the range (0, 1]")

        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        self.vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            min_df=min_df,
            max_df=max_df,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=False,
            norm="l2",
            dtype=np.float32,
        )

        self.batch_size = batch_size
        self.reference_ids: list[str] = []
        self.reference_matrix: csr_matrix | None = None
        self.is_fitted = False

    def fit(
        self,
        reference_ids: Sequence[str],
        reference_texts: Sequence[str],
        training_texts: Sequence[str],
    ) -> "TfidfRetriever":
        """
        Fit TF-IDF on shared reference documents and training queries.

        Validation/test text must not be passed to this method.
        """

        if len(reference_ids) != len(reference_texts):
            raise ValueError(
                "Reference IDs and texts must have equal lengths"
            )

        if not reference_ids:
            raise ValueError("Reference corpus cannot be empty")

        if len(set(reference_ids)) != len(reference_ids):
            raise ValueError("Reference document IDs must be unique")

        if any(not isinstance(text, str) or not text.strip()
               for text in reference_texts):
            raise ValueError("Reference texts must be non-empty strings")

        if any(not isinstance(text, str) or not text.strip()
               for text in training_texts):
            raise ValueError("Training texts must be non-empty strings")

        if not training_texts:
            raise ValueError("Training texts cannot be empty")

        fitting_texts = list(reference_texts) + list(training_texts)

        self.vectorizer.fit(fitting_texts)

        self.reference_matrix = self.vectorizer.transform(
            reference_texts
        ).tocsr()

        self.reference_ids = list(reference_ids)
        self.is_fitted = True

        return self

    def retrieve(
        self,
        query_texts: Sequence[str],
        top_k: int = 10,
    ) -> list[list[dict]]:
        """
        Retrieve the top-k reference documents for each query.

        Results are ranked by cosine similarity in descending order.
        """

        if not self.is_fitted or self.reference_matrix is None:
            raise RuntimeError("Retriever must be fitted before retrieval")

        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        if top_k > len(self.reference_ids):
            raise ValueError(
                "top_k cannot exceed the number of reference documents"
            )

        if any(not isinstance(text, str) or not text.strip()
               for text in query_texts):
            raise ValueError("Query texts must be non-empty strings")

        results = []

        for start in range(0, len(query_texts), self.batch_size):
            batch_texts = query_texts[
                start:start + self.batch_size
            ]

            query_matrix = self.vectorizer.transform(batch_texts)

            similarity_matrix = cosine_similarity(
                query_matrix,
                self.reference_matrix,
                dense_output=True,
            )

            for row in similarity_matrix:
                candidate_indices = np.argpartition(
                    row,
                    -top_k
                )[-top_k:]

                ranked_indices = candidate_indices[
                    np.argsort(row[candidate_indices])[::-1]
                ]

                query_results = [
                    {
                        "document_id": self.reference_ids[index],
                        "similarity_score": float(np.clip(row[index], 0.0, 1.0)),
                    }
                    for index in ranked_indices
                ]

                results.append(query_results)

        return results

    def get_statistics(self) -> dict:
        """Return basic information about the fitted TF-IDF index."""

        if not self.is_fitted or self.reference_matrix is None:
            raise RuntimeError("Retriever has not been fitted")

        return {
            "reference_documents": len(self.reference_ids),
            "vocabulary_size": len(self.vectorizer.vocabulary_),
            "matrix_shape": self.reference_matrix.shape,
            "non_zero_entries": self.reference_matrix.nnz,
            "sparsity": (
                1.0
                - self.reference_matrix.nnz
                / (
                    self.reference_matrix.shape[0]
                    * self.reference_matrix.shape[1]
                )
            ),
        }
