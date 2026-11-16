from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.overlap.comparison_service import compare_documents
from src.preprocessing.document_loader import (
    DocumentLoadError,
    load_document,
)

MAX_FILES = 10
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_PATH = FRONTEND_DIR / "index.html"
ASSETS_PATH = FRONTEND_DIR / "assets"

# Separate logo files for the browser tab and interface.
FAVICON_PATH = ASSETS_PATH / "asod-logo-1.svg"

# Legal pages.
PRIVACY_PATH = FRONTEND_DIR / "privacy.html"
TERMS_PATH = FRONTEND_DIR / "terms.html"


app = FastAPI(
    title="ASOD API",
    description=(
        "Assignment Similarity and Overlap Detector. "
        "Upload documents to identify exact and near-copy text overlap."
    ),
    version="0.1.0",
)

# Serve frontend logo assets.
app.mount(
    "/assets",
    StaticFiles(directory=ASSETS_PATH),
    name="assets",
)


def serve_frontend_file(path: Path, description: str):
    """Serve a frontend HTML file after checking that it exists."""

    if not path.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"{description} was not found.",
        )

    return FileResponse(
        path,
        media_type="text/html",
    )


@app.get("/", include_in_schema=False)
async def home():
    """Serve the main ASOD interface."""

    return serve_frontend_file(
        FRONTEND_PATH,
        "Frontend index.html",
    )


@app.get("/privacy", include_in_schema=False)
async def privacy_policy():
    """Serve the Privacy Policy page."""

    return serve_frontend_file(
        PRIVACY_PATH,
        "Privacy Policy",
    )


@app.get("/terms", include_in_schema=False)
async def terms_of_use():
    """Serve the Terms of Use page."""

    return serve_frontend_file(
        TERMS_PATH,
        "Terms of Use",
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve the browser tab SVG logo."""

    if not FAVICON_PATH.is_file():
        raise HTTPException(
            status_code=404,
            detail="Browser tab logo was not found.",
        )

    return FileResponse(
        FAVICON_PATH,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/health")
async def health_check():
    """Return the API health status."""

    return {
        "status": "healthy",
        "service": "ASOD API",
    }


@app.post("/api/compare")
async def compare_uploaded_documents(
    files: list[UploadFile] = File(...),
):
    """
    Compare every unique pair of uploaded TXT/DOCX documents.

    Upload restrictions:
    - Minimum documents: 2
    - Maximum documents: 10
    - Maximum file size: 10 MB per document

    Returned character offsets refer to extracted text, not native
    Word page numbers or PDF page positions.
    """

    if len(files) < 2:
        raise HTTPException(
            status_code=400,
            detail="Upload at least two documents.",
        )

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"A maximum of {MAX_FILES} documents is allowed.",
        )

    documents = []

    for uploaded_file in files:
        filename = uploaded_file.filename or "unnamed"

        try:
            content = await uploaded_file.read(MAX_FILE_SIZE_BYTES + 1)

            if len(content) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(f"File '{filename}' exceeds " "the 10 MB upload limit."),
                )

            document = load_document(
                filename=filename,
                content=content,
            )

            documents.append(document)

        except DocumentLoadError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not process '{filename}': {exc}",
            ) from exc

        finally:
            await uploaded_file.close()

    comparisons = compare_documents(documents)

    return {
        "status": "success",
        "document_count": len(documents),
        "pair_count": len(comparisons),
        "documents": [
            {
                "filename": document.filename,
                "file_type": document.file_type,
                "char_count": document.char_count,
                "word_count": document.word_count,
            }
            for document in documents
        ],
        "comparisons": comparisons,
        "notice": (
            "Detected matches are textual overlap evidence, "
            "not an automatic determination of plagiarism."
        ),
    }
