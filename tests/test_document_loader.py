from io import BytesIO

import pytest
from docx import Document

from src.preprocessing.document_loader import (
    DocumentLoadError,
    load_document,
)


def make_docx_bytes():
    document = Document()
    document.add_paragraph("First paragraph.")
    document.add_paragraph("Second paragraph.")

    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Table content"
    table.cell(0, 1).text = "Second cell"

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_load_txt_preserves_text():
    content = b"First paragraph.\nSecond paragraph.\n"

    result = load_document("sample.txt", content)

    assert result.filename == "sample.txt"
    assert result.file_type == "txt"
    assert result.text == "First paragraph.\nSecond paragraph.\n"
    assert result.char_count == len(result.text)
    assert result.word_count == 4


def test_load_txt_handles_utf8_bom():
    content = b"\xef\xbb\xbfHello world"

    result = load_document("sample.txt", content)

    assert result.text == "Hello world"


def test_load_docx_preserves_paragraph_order():
    result = load_document("sample.docx", make_docx_bytes())

    assert result.file_type == "docx"
    assert result.text.startswith("First paragraph.\nSecond paragraph.")
    assert result.text.index("First paragraph") < result.text.index("Second paragraph")
    assert "Table content | Second cell" in result.text


def test_load_docx_reports_extracted_offsets():
    result = load_document("sample.docx", make_docx_bytes())

    start = result.text.index("Second paragraph.")
    end = start + len("Second paragraph.")

    assert result.text[start:end] == "Second paragraph."


def test_rejects_empty_upload():
    with pytest.raises(DocumentLoadError, match="empty"):
        load_document("empty.txt", b"")


def test_rejects_unsupported_extension():
    with pytest.raises(DocumentLoadError, match="Unsupported"):
        load_document("sample.pdf", b"some content")


def test_rejects_invalid_txt_encoding():
    with pytest.raises(DocumentLoadError, match="UTF-8"):
        load_document("sample.txt", b"\xff\xfe\xfa")


def test_rejects_invalid_docx():
    with pytest.raises(DocumentLoadError, match="unreadable"):
        load_document("broken.docx", b"not a valid docx")


def test_rejects_empty_extracted_text():
    with pytest.raises(DocumentLoadError, match="No readable text"):
        load_document("empty.txt", b" \n\t ")


def test_removes_client_supplied_directory_from_filename():
    result = load_document(
        r"C:\fakepath\sample.txt",
        b"Some document text",
    )

    assert result.filename == "sample.txt"
