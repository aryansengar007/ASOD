import re
from dataclasses import dataclass
from io import BytesIO


@dataclass(frozen=True)
class LoadedDocument:
    filename: str
    file_type: str
    text: str
    char_count: int
    word_count: int


class DocumentLoadError(ValueError):
    """Raised when an uploaded document cannot be extracted safely."""


SUPPORTED_EXTENSIONS = {".txt", ".docx"}


def _safe_filename(filename: str) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise DocumentLoadError("A valid filename is required.")

    # Remove any directory components supplied by the client.
    return filename.replace("\\", "/").rsplit("/", 1)[-1]


def _extract_txt(content: bytes) -> str:
    try:
        # utf-8-sig also handles UTF-8 files containing a BOM.
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentLoadError("The TXT file must use UTF-8 encoding.") from exc


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document

        document = Document(BytesIO(content))
        blocks = []

        # Preserve the order of paragraphs and tables.
        for block in document.iter_inner_content():
            if hasattr(block, "text"):
                blocks.append(block.text)
            else:
                for row in block.rows:
                    cells = [cell.text.replace("\n", " ").strip() for cell in row.cells]
                    blocks.append(" | ".join(cells))

        return "\n".join(blocks)

    except DocumentLoadError:
        raise
    except Exception as exc:
        raise DocumentLoadError("The DOCX file is unreadable or invalid.") from exc


def load_document(filename: str, content: bytes) -> LoadedDocument:
    """
    Extract a TXT or DOCX document from uploaded bytes.

    Character offsets in the returned text refer to this extracted
    representation, not to native Word page positions or file bytes.
    """
    safe_name = _safe_filename(filename)

    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")

    if not content:
        raise DocumentLoadError("The uploaded file is empty.")

    extension = "." + safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""

    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentLoadError(
            f"Unsupported file type: {extension or 'no extension'}. "
            "Supported types are TXT and DOCX."
        )

    if extension == ".txt":
        extracted_text = _extract_txt(content)
    else:
        extracted_text = _extract_docx(content)

    if not extracted_text.strip():
        raise DocumentLoadError(f"No readable text was found in {safe_name}.")

    return LoadedDocument(
        filename=safe_name,
        file_type=extension[1:],
        text=extracted_text,
        char_count=len(extracted_text),
        word_count=len(re.findall(r"\S+", extracted_text)),
    )
