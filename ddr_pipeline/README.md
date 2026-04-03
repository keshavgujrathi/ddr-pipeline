# DDR Pipeline

An AI workflow that converts raw site inspection and thermal PDF reports into a structured, client-ready Detailed Diagnostic Report (DDR).

## Setup
```bash
pip install pdfplumber PyMuPDF pydantic jinja2 pillow groq
```

## Usage
```bash
export GROQ_API_KEY="your-api-key-here"
python -m ddr_pipeline.main inspection.pdf thermal.pdf output.html
```

## How it works

**Stage 1 — Extraction** (`extract.py`)
Pulls text and images from both PDFs using pdfplumber and pymupdf. Filters junk images by size, aspect ratio, page position, and content hash to retain only relevant defect photos.

**Stage 2 — Fusion** (`fuse.py`)
Merges inspection and thermal observations deterministically — no LLM involved. Detects conflicts between sources, flags missing information, and deduplicates images by MD5 hash.

**Stage 3 — Generation** (`generate.py`)
Sends fused data to Groq (LLaMA 3.3 70B) to produce: observations narrative, probable root cause, severity with evidence-based reasoning, and recommended actions. One API call per area.

**Stage 4 — Rendering** (`render.py`)
Produces a single self-contained HTML file with base64-embedded images, severity badges, conflict callouts, and missing info flags. Also saves a JSON sidecar for traceability.

## Output structure
- Property Issue Summary
- Executive Summary  
- Area-wise Observations with embedded photos
- Probable Root Cause
- Severity Assessment with reasoning
- Recommended Actions
- Missing or Unclear Information

## Requirements
- `GROQ_API_KEY` environment variable (free tier at console.groq.com)
- Input: one inspection PDF + one thermal PDF
- Output: portable HTML report + JSON sidecar
