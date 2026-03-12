# SOP Manager Agent

Convert operational documents (PDFs, Word docs, Excel sheets, video recordings) into structured, searchable SOPs using Claude AI.

## Features
- Upload PDF, DOCX, XLSX, MP4/MOV/audio files
- AI-powered translation to structured Markdown SOPs via Claude
- Central SOP library with search and tag filtering
- In-browser editor for SOPs
- Download individual SOPs as `.md` files

## Setup

```bash
pip3 install -r requirements.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

## Run

```bash
python3 run.py
```

Open [http://localhost:8004](http://localhost:8004)

## Stack
- FastAPI + Jinja2 + Vanilla JS
- Claude claude-opus-4-6 (Anthropic)
- pdfplumber, python-docx, openpyxl, openai-whisper
- SOPs stored as Markdown files in `app/sops/`
