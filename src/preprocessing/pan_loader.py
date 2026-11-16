from pathlib import Path
import unicodedata


class PanPC11Loader:
    """
    Loads original PAN-PC-11 documents using ASOD document IDs.

    Original text is returned without normalization so that PAN
    character offsets remain applicable.
    """

    def __init__(self, corpus_root: Path):
        self.corpus_root = Path(corpus_root)

        self.suspicious_dir = (
            self.corpus_root / "suspicious-document"
        )
        self.source_dir = (
            self.corpus_root / "source-document"
        )

        for directory in (
            self.suspicious_dir,
            self.source_dir,
        ):
            if not directory.is_dir():
                raise FileNotFoundError(
                    f"PAN corpus directory not found: {directory}"
                )

        self._suspicious_index = self._index_files(
            self.suspicious_dir
        )
        self._source_index = self._index_files(
            self.source_dir
        )

    @staticmethod
    def _index_files(directory: Path) -> dict[str, Path]:
        index = {}

        for path in sorted(directory.rglob("*.txt")):
            if path.name in index:
                raise RuntimeError(
                    f"Duplicate PAN filename: {path.name}"
                )

            index[path.name] = path

        return index

    def resolve(self, document_id: str) -> Path:
        if not isinstance(document_id, str):
            raise TypeError("document_id must be a string")

        if "::" not in document_id:
            raise ValueError(
                f"Invalid PAN document ID: {document_id}"
            )

        document_type, filename = document_id.split("::", 1)

        if (
            not filename
            or Path(filename).name != filename
            or not filename.endswith(".txt")
        ):
            raise ValueError(
                f"Invalid PAN filename in document ID: {document_id}"
            )

        if document_type == "SUSPICIOUS":
            index = self._suspicious_index

        elif document_type == "SOURCE":
            index = self._source_index

        else:
            raise ValueError(
                f"Unknown PAN document type: {document_type}"
            )

        try:
            return index[filename]
        except KeyError:
            raise FileNotFoundError(
                f"PAN document not found: {document_id}"
            ) from None

    def load_text(self, document_id: str) -> str:
        """
        Return original text without changing encoding or newlines.
        """

        path = self.resolve(document_id)

        with path.open(
            "r",
            encoding="utf-8",
            newline=""
        ) as file:
            return file.read()

    def load_normalized_text(self, document_id: str) -> str:
        """
        Return a separate normalized representation for similarity.
        Original text and its offsets remain unchanged.
        """

        original_text = self.load_text(document_id)

        return normalize_for_similarity(original_text)


def normalize_for_similarity(text: str) -> str:
    """
    Normalize text for lexical similarity.

    This function must never be used to calculate PAN span offsets.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    normalized = unicodedata.normalize("NFKC", text)

    normalized = normalized.lstrip("\ufeff")
    normalized = normalized.casefold()

    # Normalize whitespace without modifying the original text.
    normalized = " ".join(normalized.split())

    return normalized