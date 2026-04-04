---
name: youtube-knowledge-extractor
description: "Use when the user shares a YouTube link and wants its content extracted, transcribed, analyzed, or structured. Triggers on any YouTube URL (youtube.com, youtu.be) or when user says 'extract', 'transcribe', 'analyze', or 'summarize' a YouTube video."
version: 0.2.0
---

# YouTube Knowledge Extractor

Extract transcripts, analyze content, and structure knowledge from YouTube videos. No API key needed — uses youtube-transcript-api (free, local).

## Tools

### transcript
Extract the raw transcript from a YouTube video.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcript.py --url <youtube-url> [--language de,en] [--format text|timestamped|srt]
```

**Parameters:**
- **--url** (required) — YouTube URL or video ID
- **--language** (optional) — Preferred languages, comma-separated (default: de,en)
- **--format** (optional) — text (plain), timestamped (with times), srt (subtitle format) (default: text)

**Examples:**
```bash
# Plain text transcript
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcript.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# With timestamps
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcript.py --url "https://youtu.be/dQw4w9WgXcQ" --format timestamped

# German preferred, fallback English
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/transcript.py --url "https://youtube.com/watch?v=ID" --language de,en
```

### analyze
Full analysis: extract transcript + AI-powered structuring into Key Learnings, Concepts, Tools, Action Items.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/analyze.py --url <youtube-url> [--language de] [--transcript-language de,en]
```

**Parameters:**
- **--url** (required) — YouTube URL or video ID
- **--language** (optional) — Output language for analysis (default: de)
- **--transcript-language** (optional) — Preferred transcript languages (default: de,en)

**Example:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/analyze.py --url "https://youtube.com/watch?v=ID" --language de
```

### list_languages
Show which transcript languages are available for a video.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/list_languages.py --url <youtube-url>
```

## Before running tools

### Interactive Mode

If the user shares a YouTube URL without specifying what they want, ask:

> "Was soll ich mit dem Video machen?
> - **Transkript** — Reiner Text des gesprochenen Inhalts
> - **Analyse** — Strukturierte Zusammenfassung mit Key Learnings, Konzepten, Tools, Action Items
> - **Sprachen pruefen** — Welche Untertitel-Sprachen sind verfuegbar?"

If the user is specific (e.g. "Transkribiere das Video", "Was sind die Key Learnings?"), run directly:
- "Transkribiere / Transkript / Text" → transcript tool
- "Analysiere / Key Learnings / Zusammenfassung / Was lernt man" → analyze tool
- "Welche Sprachen" → list_languages tool

After running **analyze**, always offer:
> "Soll ich das als Markdown-Datei speichern?"

## When to use
- User shares a YouTube URL (youtube.com, youtu.be)
- User wants a video transcribed
- User wants key learnings or a summary from a video
- User mentions "YouTube", "Video analysieren", "Video zusammenfassen"

## When NOT to use
- For local audio files → use audio skill
- For local video files → future video skill
- For live streams (no transcript available)
- For music videos without speech content
