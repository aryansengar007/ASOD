<div align="center">

<img src="frontend/assets/asod-logo-2.svg" alt="ASOD Logo" width="240">

# ASOD

### Assignment Similarity & Overlap Detector

**A document comparison system for identifying textual overlap and inspecting supporting passage-level evidence.**

<br>

<img src="https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Frontend-HTML%20%7C%20CSS%20%7C%20JavaScript-orange" alt="Frontend">
<img src="https://img.shields.io/badge/Tests-pytest-blue?logo=pytest&logoColor=white" alt="pytest">
<img src="https://img.shields.io/badge/Formats-TXT%20%7C%20DOCX-informational" alt="Formats">

</div>

---

## About

ASOD (Assignment Similarity & Overlap Detector) is a document comparison project that helps identify textual reuse across multiple submitted documents.

Users can upload TXT and DOCX files, compare them pairwise, and inspect detected exact token-sequence matches and potential near-copy regions.

Instead of presenting a single similarity score as a plagiarism verdict, ASOD provides extracted text passages, character offsets, and supporting comparison evidence for human examination.

## Features

- **Multi-document upload:** Select between 2 and 10 documents.
- **Supported formats:** TXT and DOCX.
- **Pairwise comparison:** Compare every unique pair of uploaded documents.
- **Exact overlap detection:** Identify matching contiguous token sequences.
- **Near-copy detection:** Identify candidate regions containing partial or interrupted lexical matches.
- **Evidence inspection:** View corresponding source and target passages.
- **Character offsets:** Inspect the locations of evidence within extracted text.
- **Input validation:** Enforce file type, file size, and document-count limits.

## How It Works

1. Upload two or more supported documents.
2. ASOD extracts text from each document.
3. The comparison service evaluates every unique document pair.
4. Token alignment identifies exact and candidate near-copy regions.
5. The interface displays the matched passages, offsets, and supporting statistics.
6. A human reviewer interprets the evidence in its original context.

**Important:** Textual overlap is not automatically plagiarism. Results do not establish authorship, intent, or academic misconduct.

## Technology Stack

| Component           | Technology                     |
| ------------------- | ------------------------------ |
| Backend             | Python, FastAPI                |
| API server          | Uvicorn                        |
| Document extraction | python-docx                    |
| Text processing     | regex                          |
| Comparison          | Token-based sequence alignment |
| Frontend            | HTML, CSS, JavaScript          |
| Testing             | pytest                         |

## Project Structure

```text
ASOD/
├── benchmark/
│   ├── schemas/
│   │   ├── ai_annotation.schema.json
│   │   ├── benchmark_metadata.schema.json
│   │   ├── document.schema.json
│   │   ├── document_pair.schema.json
│   │   └── overlap.schema.json
│   ├── scripts/
│   └── ANNOTATION_PROTOCOL.md
├── frontend/
│   ├── assets/
│   │   ├── asod-logo-1.svg
│   │   └── asod-logo-2.svg
│   ├── index.html
│   ├── privacy.html
│   └── terms.html
├── src/
│   ├── api/
│   │   └── main.py
│   ├── overlap/
│   │   ├── comparison_service.py
│   │   └── token_alignment.py
│   ├── preprocessing/
│   │   ├── document_loader.py
│   │   └── pan_loader.py
│   └── similarity/
├── tests/
├── .gitignore
├── DATASET_ACQUISITION_REGISTER.md
├── dataset_card.md
├── LICENSE
└── README.md
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/aryansengar007/ASOD.git
cd ASOD
```

### 2. Install the core application dependencies

```bash
python -m pip install fastapi uvicorn python-multipart python-docx regex
```

For running the test suite:

```bash
python -m pip install pytest httpx
```

### 3. Start the application

From the project root:

```bash
python -m uvicorn src.api.main:app --reload
```

### 4. Open ASOD

Visit:

```text
http://127.0.0.1:8000
```

The FastAPI interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Running Tests

Run the core application tests:

```bash
python -m pytest tests/test_document_loader.py tests/test_comparison_service.py tests/test_api.py -v
```

## Current Scope and Limitations

- TXT and DOCX document extraction are supported.
- PDF extraction and OCR are not currently implemented.
- The current comparison engine focuses on lexical overlap and token alignment.
- Semantic paraphrase detection and AI-generated-text detection are not part of the current upload-and-compare workflow.
- Character offsets refer to extracted text, not original DOCX page positions.
- Detected evidence requires human interpretation.

## Research Dataset

The project also contains benchmark preparation and evaluation work involving the PAN-PC-11 plagiarism corpus.

The benchmark documentation records dataset provenance, annotation handling, and evaluation methodology. Research retrieval experiments are separate from the current user-upload comparison workflow.

## Author

<div align="center">

### Aryan Sengar

B.Tech Computer Science & Engineering (AI & ML)

<a href="https://github.com/aryansengar007">
<img src="https://img.shields.io/badge/GitHub-Profile-181717?logo=github&logoColor=white" alt="GitHub">
</a>
<a href="https://www.linkedin.com/in/aryan-sengar-786b96290/">
<img src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?logo=linkedin&logoColor=white" alt="LinkedIn">
</a>
<a href="https://aryan-sengar-portfolio-v2.netlify.app/">
<img src="https://img.shields.io/badge/Portfolio-Website-0A7EA4" alt="Portfolio">
</a>
<a href="https://leetcode.com/u/aryan_sengar007/">
<img src="https://img.shields.io/badge/LeetCode-Profile-FFA116?logo=leetcode&logoColor=black" alt="LeetCode">
</a>

</div>

---

<div align="center">

**ASOD — Assignment Similarity & Overlap Detector**

© 2026 Aryan Sengar

</div>
