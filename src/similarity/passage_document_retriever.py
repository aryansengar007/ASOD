import json
from pathlib import Path

import numpy as np
from scipy.sparse import load_npz
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize


class PassageDocumentRetriever:
    """
    Retrieve parent source documents using passage-level TF-IDF.

    Each reference document receives the maximum similarity score
    among its indexed passages.

    Does not load the large StreamingTfidfRetriever manifest.
    """

    CHUNK_SIZE = 128

    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)

        self.retriever_dir = self.index_dir / "retriever"
        self.parent_map_dir = self.index_dir / "parent_map"

        self.passage_manifest_path = self.index_dir / "passage_manifest.json"
        self.idf_path = self.retriever_dir / "idf.npy"

        self.codes_path = self.parent_map_dir / "reference_parent_codes.npy"
        self.documents_path = self.parent_map_dir / "reference_parent_documents.json"

        required_files = [
            self.passage_manifest_path,
            self.idf_path,
            self.codes_path,
            self.documents_path,
        ]

        for path in required_files:
            if not path.is_file():
                raise FileNotFoundError(path)

        with self.passage_manifest_path.open("r", encoding="utf-8") as file:
            self.manifest = json.load(file)

        with self.documents_path.open("r", encoding="utf-8") as file:
            parent_data = json.load(file)

        self.reference_count = self.manifest["reference_passage_count"]

        self.document_count = self.manifest["reference_document_count"]

        self.documents = parent_data["documents"]

        if len(self.documents) != self.document_count:
            raise ValueError("Parent document count does not match passage manifest.")

        if parent_data["reference_passage_count"] != self.reference_count:
            raise ValueError(
                "Parent map passage count does not match passage manifest."
            )

        if len(set(self.documents)) != len(self.documents):
            raise ValueError("Duplicate parent document IDs.")

        self.parent_codes = np.load(
            self.codes_path,
            mmap_mode="r",
        )

        if self.parent_codes.shape != (self.reference_count,):
            raise ValueError("Invalid parent-code array shape.")

        if self.parent_codes.dtype != np.uint32:
            raise ValueError("Parent-code array must use uint32.")

        self.idf = np.load(self.idf_path)

        if self.idf.ndim != 1:
            raise ValueError("Invalid IDF dimensions.")

        if not np.all(np.isfinite(self.idf)):
            raise ValueError("IDF contains non-finite values.")

        if np.any(self.idf <= 0):
            raise ValueError("IDF contains non-positive values.")

        self.n_features = len(self.idf)

        self.vectorizer = HashingVectorizer(
            n_features=self.n_features,
            analyzer="word",
            ngram_range=(1, 2),
            alternate_sign=False,
            norm=None,
            lowercase=False,
            strip_accents="unicode",
            dtype=np.float32,
        )

        self.chunk_count = (
            self.reference_count + self.CHUNK_SIZE - 1
        ) // self.CHUNK_SIZE

        self._validate_chunk_boundaries()

    def _validate_chunk_boundaries(self):
        """Check the first and final expected chunk files."""

        first_chunk = self.retriever_dir / "reference_0000.npz"

        last_chunk = self.retriever_dir / f"reference_{self.chunk_count - 1:04d}.npz"

        if not first_chunk.is_file():
            raise FileNotFoundError(first_chunk)

        if not last_chunk.is_file():
            raise FileNotFoundError(last_chunk)

    def retrieve(
        self,
        query_text: str,
        top_k: int = 10,
        progress: bool = True,
    ) -> list[dict]:
        """
        Retrieve parent documents for one normalized query passage.

        Query text must use normalize_for_similarity() preprocessing.

        Parent score = maximum cosine similarity across its passages.
        """

        if not isinstance(query_text, str) or not query_text.strip():
            raise ValueError("Query text must be non-empty.")

        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise ValueError("top_k must be an integer.")

        if top_k < 1:
            raise ValueError("top_k must be positive.")

        query_matrix = self.vectorizer.transform([query_text])
        query_matrix = query_matrix.multiply(self.idf).tocsr()

        query_matrix = normalize(
            query_matrix,
            norm="l2",
            copy=False,
        )

        if query_matrix.nnz == 0:
            return []

        parent_scores = np.zeros(
            self.document_count,
            dtype=np.float32,
        )

        passage_position = 0

        for chunk_number in range(self.chunk_count):
            filename = f"reference_{chunk_number:04d}.npz"

            chunk_path = self.retriever_dir / filename

            reference_matrix = load_npz(chunk_path).tocsr()

            expected_rows = min(
                self.CHUNK_SIZE,
                self.reference_count - passage_position,
            )

            if reference_matrix.shape != (
                expected_rows,
                self.n_features,
            ):
                raise ValueError(
                    f"Unexpected matrix shape in {filename}: "
                    f"{reference_matrix.shape}"
                )

            end_position = passage_position + expected_rows

            parent_codes = self.parent_codes[passage_position:end_position]

            if (
                int(parent_codes.min()) < 0
                or int(parent_codes.max()) >= self.document_count
            ):
                raise ValueError(f"Invalid parent code in {filename}")

            similarities = (query_matrix @ reference_matrix.T).toarray().ravel()

            np.clip(
                similarities,
                0.0,
                1.0,
                out=similarities,
            )

            np.maximum.at(
                parent_scores,
                parent_codes,
                similarities,
            )

            passage_position = end_position

            del reference_matrix
            del similarities
            del parent_codes

            if progress and (
                (chunk_number + 1) % 1000 == 0 or chunk_number + 1 == self.chunk_count
            ):
                print(
                    f"Passage chunks scanned: "
                    f"{chunk_number + 1:,}/{self.chunk_count:,}"
                )

        if passage_position != self.reference_count:
            raise ValueError("Scanned passage count does not match manifest.")

        matching_codes = np.flatnonzero(parent_scores > 0)

        ranked_codes = sorted(
            matching_codes.tolist(),
            key=lambda code: (
                -float(parent_scores[code]),
                self.documents[code],
            ),
        )

        return [
            {
                "document_id": self.documents[code],
                "similarity_score": float(parent_scores[code]),
            }
            for code in ranked_codes[:top_k]
        ]

    def retrieve_many(
        self,
        query_texts: list[str],
        top_k: int = 100,
        progress: bool = True,
        max_query_matrix_bytes: int = 2 * 1024**3,
    ) -> list[list[dict]]:
        """
        Retrieve parent documents for multiple normalized query passages.

        Scans each reference chunk once for the entire query collection.
        Parent score = maximum cosine similarity across its passages.

        Returns one ranked result list per query, in input order.
        """

        if not isinstance(query_texts, (list, tuple)):
            raise ValueError("query_texts must be a list or tuple.")

        if not query_texts:
            return []

        if any(not isinstance(text, str) or not text.strip() for text in query_texts):
            raise ValueError("Every query must be a non-empty string.")

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        if (
            not isinstance(max_query_matrix_bytes, int)
            or isinstance(max_query_matrix_bytes, bool)
            or max_query_matrix_bytes < 1
        ):
            raise ValueError("max_query_matrix_bytes must be positive.")

        query_count = len(query_texts)

        # Transform all queries together so the reference index
        # only needs to be scanned once.
        query_matrix = self.vectorizer.transform(query_texts).tocsr()

        # Apply IDF in-place to avoid creating a second sparse matrix.
        query_matrix.data *= self.idf[query_matrix.indices]

        query_matrix = normalize(
            query_matrix,
            norm="l2",
            copy=False,
        )

        query_matrix_bytes = (
            query_matrix.data.nbytes
            + query_matrix.indices.nbytes
            + query_matrix.indptr.nbytes
        )

        print(f"Queries: {query_count:,}")
        print(f"Query matrix non-zero entries: {query_matrix.nnz:,}")
        print(f"Query matrix memory: " f"{query_matrix_bytes / (1024 ** 2):,.2f} MiB")

        if query_matrix_bytes > max_query_matrix_bytes:
            raise MemoryError(
                "Query matrix exceeds the configured memory limit. "
                "No reference chunks have been scanned."
            )

        # Rows = queries; columns = parent reference documents.
        parent_scores = np.zeros(
            (query_count, self.document_count),
            dtype=np.float32,
        )

        query_rows = np.arange(query_count)[:, None]

        passage_position = 0

        for chunk_number in range(self.chunk_count):
            filename = f"reference_{chunk_number:04d}.npz"
            chunk_path = self.retriever_dir / filename

            reference_matrix = load_npz(chunk_path).tocsr()

            expected_rows = min(
                self.CHUNK_SIZE,
                self.reference_count - passage_position,
            )

            if reference_matrix.shape != (
                expected_rows,
                self.n_features,
            ):
                raise ValueError(
                    f"Unexpected matrix shape in {filename}: "
                    f"{reference_matrix.shape}"
                )

            end_position = passage_position + expected_rows

            parent_codes = self.parent_codes[passage_position:end_position]

            if (
                int(parent_codes.min()) < 0
                or int(parent_codes.max()) >= self.document_count
            ):
                raise ValueError(f"Invalid parent code in {filename}")

            # Similarity matrix: query_count x passages_in_chunk.
            similarities = (query_matrix @ reference_matrix.T).toarray()

            np.clip(
                similarities,
                0.0,
                1.0,
                out=similarities,
            )

            # Aggregate maximum passage score for each parent.
            np.maximum.at(
                parent_scores,
                (query_rows, parent_codes[None, :]),
                similarities,
            )

            passage_position = end_position

            del reference_matrix
            del similarities
            del parent_codes

            if progress and (
                (chunk_number + 1) % 1000 == 0 or chunk_number + 1 == self.chunk_count
            ):
                print(
                    f"Passage chunks scanned: "
                    f"{chunk_number + 1:,}/{self.chunk_count:,}"
                )

        if passage_position != self.reference_count:
            raise ValueError("Scanned passage count does not match manifest.")

        # Rank each query independently, preserving deterministic
        # document-ID tie-breaking.
        all_results = []

        for scores in parent_scores:
            matching_codes = np.flatnonzero(scores > 0)

            ranked_codes = sorted(
                matching_codes.tolist(),
                key=lambda code: (
                    -float(scores[code]),
                    self.documents[code],
                ),
            )

            all_results.append(
                [
                    {
                        "document_id": self.documents[code],
                        "similarity_score": float(scores[code]),
                    }
                    for code in ranked_codes[:top_k]
                ]
            )

        return all_results

    def get_statistics(self) -> dict:
        return {
            "reference_passages": self.reference_count,
            "reference_documents": self.document_count,
            "feature_dimensions": self.n_features,
            "chunk_size": self.CHUNK_SIZE,
            "chunk_count": self.chunk_count,
            "index_directory": str(self.index_dir),
        }
