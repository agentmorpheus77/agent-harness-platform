---
name: doc-intake
description: "Use when the user wants to analyze, summarize, or compare multiple documents. Triggers on 'analysiere Dokumente', 'Dokument-Analyse', 'document intake', 'fasse diese Dokumente zusammen', 'vergleiche diese Dateien', or any request to upload and analyze files."
version: 0.1.0
---

# Document Intake — Multi-File Analysis

Upload multiple documents via a browser form, extract their content locally, and get an AI-powered analysis.

## Tools

### analyze
Open a browser form to collect files and settings, then analyze all documents together.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/analyze.py
```

No CLI arguments needed — all input is collected via the browser form.

**Supported formats:** PDF, PNG, JPG, DOCX, XLSX, PPTX, TXT, MD, CSV

**Analysis modes:**
- **Zusammenfassung** — Compact summary of all documents
- **Analyse** — Deep analysis: contradictions, open questions, connections
- **Beides** — Summary first, then analysis

**Output language:** German or English (selectable in form)

## When to use
- User wants to analyze, summarize, or compare multiple documents
- User has files to upload and wants AI-powered insights
- User mentions "Dokument-Analyse" or "document intake"

## When NOT to use
- Single file analysis (use the LLM directly)
- Image-only analysis without text context (use image skill)
