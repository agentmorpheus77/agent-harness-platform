---
name: audio
description: Use when the user has an audio file to transcribe, wants text-to-speech output, or needs audio content analyzed — supports dialog transcription, meeting minutes, summaries, and keyword extraction
version: 0.2.0
---

# Audio Processing

Transcribe audio files in multiple modes and generate speech from text.

## Tools

### transcribe
Transcribe or analyze an audio file using AI. Supports multiple output modes.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcribe.py --file <path> [--mode transcript|dialog|summary|minutes|keywords] [--language auto|de|en] [--output-language de|en]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --file | Yes | Path to audio file (mp3, wav, m4a, ogg, flac, webm, aac) |
| --mode | No | Output mode (default: transcript) |
| --language | No | Expected audio language for accuracy (default: auto) |
| --output-language | No | Language for summary/minutes/keywords output (default: de) |

**Modes:**
| Mode | What it does |
|------|-------------|
| transcript | Plain flowing text transcription |
| dialog | Speaker-labeled dialog (Speaker 1: ..., Speaker 2: ...) |
| summary | Concise summary of the audio content (not word-by-word) |
| minutes | Structured meeting minutes (Participants, Topics, Decisions, Action Items) |
| keywords | Comma-separated list of key topics and terms |

**Examples:**
```bash
# Simple transcription
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcribe.py --file ~/meetings/standup.mp3

# Meeting with speaker detection
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcribe.py --file ~/meetings/standup.mp3 --mode dialog

# Meeting minutes in German
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcribe.py --file ~/meetings/standup.mp3 --mode minutes --output-language de

# Quick summary in English
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcribe.py --file ~/podcast/episode.mp3 --mode summary --output-language en
```

### tts
Generate speech audio from text (Text-to-Speech).

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/tts.py --text <text> --output <path> [--voice Kore|Puck|Charon|Fenrir|Aoede]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --text | Yes | Text to convert to speech |
| --output | Yes | Output file path (wav format) |
| --voice | No | Voice preset (default: Kore) |

**Voices:**
| Voice | Character |
|-------|-----------|
| Kore | Female, warm, professional |
| Puck | Male, friendly, conversational |
| Charon | Male, deep, authoritative |
| Fenrir | Male, energetic |
| Aoede | Female, clear, expressive |

**Example:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/tts.py --text "Willkommen beim CDB Skills System" --output ~/output.wav --voice Kore
```

## Before running tools

### Transcribe — Interactive Mode

If the user is **vague** (e.g. "Transkribiere das", "Was wird in der Datei gesagt?"), ask:

> "Wie soll ich die Audio-Datei verarbeiten?
> - **Transkript** — Wort-fuer-Wort als Fliesstext
> - **Dialog** — Mit Sprechererkennung (Speaker 1, Speaker 2...)
> - **Zusammenfassung** — Nur die Kernpunkte, kein volles Transkript
> - **Meeting Minutes** — Strukturiert mit Themen, Entscheidungen, Action Items
> - **Keywords** — Nur die wichtigsten Schlagwoerter"

If the user is **specific** (e.g. "Erstelle Meeting Minutes", "Wer sagt was?"), run directly with the matching mode:
- "Meeting Minutes / Protokoll" → `--mode minutes`
- "Wer sagt was / Dialog / Sprecher" → `--mode dialog`
- "Zusammenfassung / Worum geht es" → `--mode summary`
- "Schlagwoerter / Keywords / Themen" → `--mode keywords`
- "Transkribiere / Schreib auf" → `--mode transcript`

### TTS — Interactive Mode

If the user does not specify a voice, briefly offer:

> "Welche Stimme? **Kore** (weiblich, warm), **Puck** (maennlich, freundlich), **Charon** (tief, autoritaer), **Fenrir** (energisch), **Aoede** (weiblich, klar) — oder soll ich Kore als Standard nehmen?"

If the user says "egal" or wants it quick, use **Kore** as default.

Always ask where die Audio-Datei gespeichert werden soll, unless the user specified a path. Suggest `~/Desktop/output.wav` as default.

## When to use
- User has an audio file and wants it transcribed
- User wants a meeting recording turned into minutes or a summary
- User wants to identify speakers in a recording (dialog mode)
- User wants to extract key topics from audio (keywords mode)
- User wants to convert text to speech / generate audio
- User mentions meeting, podcast, voice memo, dictation, recording

## When NOT to use
- For video files -> future video skill
- For text-only tasks that don't involve audio
- For PDF content -> use pdf-analysis skill
