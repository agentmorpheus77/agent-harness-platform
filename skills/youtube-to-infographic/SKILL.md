---
name: youtube-to-infographic
description: "Use when the user wants to turn a YouTube video into a visual infographic — extracts content, generates a 9:16 Card-Stack infographic with interactive ASCII preview. Triggers on 'Infografik aus Video', 'Video visuell aufbereiten', 'Content-Paket', or YouTube URL + 'infographic'."
version: 0.1.0
---

# YouTube to Infographic

Transform a YouTube video into a complete content package: structured Markdown analysis + 9:16 Card-Stack infographic with interactive ASCII preview.

## Tools

### pipeline (analyze mode)
Extract transcript, run AI analysis, and generate an ASCII layout preview for user review.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/pipeline.py --url <youtube-url> [--language de] [--transcript-language de,en]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --url | Yes | YouTube URL or video ID |
| --language | No | Output language (default: de) |
| --transcript-language | No | Preferred transcript languages, comma-separated (default: de,en) |

**Returns JSON with:**
- `result.analysis` — Structured Markdown analysis
- `result.ascii_layout` — ASCII Card-Stack layout for review
- `result.state_file` — Path to state file (needed for generate mode)
- `result.video_id` — Extracted video ID

### pipeline (generate mode)
Generate the infographic image and save the content package after user review.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/pipeline.py --generate <state-file> --prompt "<infographic-prompt>" --output-dir <dir>
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --generate | Yes | Path to state file from analyze mode |
| --prompt | Yes | Full image generation prompt based on reviewed layout |
| --output-dir | No | Base directory for output (default: ~/youtube-to-infographic) |

### Available Styles

When building the `--prompt` for generate mode, use one of these style descriptions. The style templates are defined in `INFOGRAPHIC_STYLES` in pipeline.py.

| Style | Vibe |
|-------|------|
| `glassmorphism` | Futuristic dark mode, frosted glass cards, neon cyan/purple accents |
| `editorial` | Bold magazine spread, asymmetric color blocks, mixed typography weights |
| `minimal` | Swiss design, pure white, ample negative space, one accent color |
| `neon` | Cyberpunk neon signs on dark brick wall, glowing tubes, smoky noir |
| `gradient` | Modern SaaS hero, mesh gradients, floating cards, duotone icons |
| `sketch` | Hand-drawn sketchnote, cream paper, marker lines, highlighter accents |
| `blueprint` | Technical drawing, engineering blue, white schematic lines, monospaced font |
| `retro` | 8-bit pixel art game UI, CRT scanlines, arcade pixel font |
| `watercolor` | Artistic watercolor washes, botanical accents, elegant serif typography |
| `noir` | Film noir, high-contrast B&W, one crimson accent, chiaroscuro lighting |

When the user doesn't specify a style, ask:
> "Welcher Stil fuer die Infografik? glassmorphism, editorial, minimal, neon, gradient, sketch, blueprint, retro, watercolor, noir"

### pipeline (skip-review mode)
Full pipeline in one shot — no interactive review.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/pipeline.py --url <youtube-url> --skip-review [--output-dir <dir>]
```

## Interaction Flow

### Phase 1: Analyze

1. Call pipeline in analyze mode with the YouTube URL
2. Parse the JSON result
3. Show the user the ASCII layout:

> "So wuerde die Infografik aussehen:"
>
> [ASCII layout from result]
>
> "Passt das so? Du kannst anpassen:
> - Headline aendern (z.B. 'Nimm XYZ als Titel' oder 'Ohne Videotitel')
> - Mehr oder weniger Learnings
> - Inhalte austauschen (z.B. ein Zitat statt einem Learning)
> - Oder einfach bestaetigen mit 'passt so'"

### Phase 2: Generate

4. Based on user feedback, build the infographic prompt:
   - Start with: "Generate a clean, modern infographic image in 9:16 portrait format. Card-Stack layout."
   - Include the (potentially modified) content from the analysis
   - If user changed the headline, use their version
   - If user removed video reference, omit it from the prompt
5. Call pipeline in generate mode with the state file and prompt
6. Show the user the output paths:

> "Content-Paket erstellt:
> - Infografik: [path]/infographic.png
> - Analyse: [path]/analysis.md
> - Metadata: [path]/metadata.json
>
> Soll ich die Infografik oeffnen? (`open [path]/infographic.png`)"

## When to use
- User shares a YouTube URL AND mentions "Infografik", "visuell aufbereiten", "Content-Paket"
- User asks to create a visual summary of a video
- User mentions "Video to Infographic"

## When NOT to use
- User only wants a transcript — use youtube-knowledge-extractor
- User only wants text analysis — use youtube-knowledge-extractor
- User wants to generate an image from a text prompt — use image skill
- User has a local audio/video file — use audio skill
