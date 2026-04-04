---
name: image
description: Use when the user asks to generate images from text prompts, describe or analyze existing images, or needs visual content created — supports multiple styles, aspect ratios, and batch generation
version: 0.2.0
---

# Image Processing

Generate images from text prompts and analyze existing images.

## Tools

### generate
Generate one or more images from a text prompt using AI.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/generate.py --prompt <text> --output <path> [--style photo|illustration|diagram|sketch|watercolor|3d|pixel|none] [--aspect 1:1|16:9|9:16|4:3|3:4] [--count 1|2|3|4]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --prompt | Yes | Text description of the image to generate |
| --output | Yes | Output file path (png) |
| --style | No | Visual style (default: none — model decides) |
| --aspect | No | Aspect ratio (default: 1:1) |
| --count | No | Number of variations to generate (default: 1, max: 4) |

**Styles:**
| Style | Description |
|-------|-------------|
| photo | Photorealistic photograph |
| illustration | Digital illustration |
| diagram | Clean technical diagram or infographic |
| sketch | Hand-drawn sketch |
| watercolor | Watercolor painting |
| 3d | 3D rendered image |
| pixel | Pixel art |
| none | Let the AI decide the best style |

**Examples:**
```bash
# Simple image generation
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/generate.py --prompt "A modern office" --output ~/office.png

# Specific style and format
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/generate.py --prompt "Network architecture diagram" --output ~/diagram.png --style diagram --aspect 16:9

# Multiple variations
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/generate.py --prompt "Logo for a tech startup" --output ~/logo.png --style illustration --count 3
```

### describe
Describe or analyze an existing image using AI.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/describe.py --file <path> [--task describe|analyze|extract|caption] [--language de|en]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --file | Yes | Path to image file (png, jpg, jpeg, webp, gif, bmp, tiff) |
| --task | No | What to do (default: describe) |
| --language | No | Output language (default: de) |

**Tasks:**
| Task | What it does |
|------|-------------|
| describe | Detailed description (subject, setting, colors, composition) |
| analyze | Technical analysis (dimensions, palette, style, visible text) |
| extract | Extract all text, data, numbers from the image |
| caption | Short 1-2 sentence caption |

**Examples:**
```bash
# Describe a photo
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/describe.py --file ~/photos/meeting.jpg --task describe

# Extract text from screenshot
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/describe.py --file ~/screenshots/error.png --task extract --language en

# Quick caption
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/describe.py --file ~/photos/team.jpg --task caption
```

## Before running tools

### Generate — Interactive Mode

If the user is **vague** (e.g. "Mach mir ein Bild", "Generiere was"), ask in **separate steps**. IMPORTANT: Ask question 1 FIRST and wait for the answer before continuing. The user's answer to question 1 becomes the `--prompt` value. Do NOT mix up the content description with style or format.

> **Step 1 (ask first, wait for answer):**
> "Beschreibe mir, was auf dem Bild zu sehen sein soll — Motiv, Szene, Details."
>
> **Step 2 (after receiving the content description):**
> "Welcher Stil? **photo** (fotorealistisch), **illustration**, **diagram**, **sketch** (handgezeichnet), **watercolor**, **3d**, **pixel** — oder soll ich entscheiden?"
>
> **Step 3:**
> "Welches Format? **1:1** (quadratisch), **16:9** (quer), **9:16** (hoch/Story)"

The answer to Step 1 is the `--prompt`. The answer to Step 2 is the `--style`. These are SEPARATE parameters — never combine them. If the user answers everything in one message, parse it correctly:
- Content/scene description → `--prompt`
- Style keywords → `--style`
- Format keywords → `--aspect`

If the user is **specific** (e.g. "Erstelle ein fotorealistisches Bild von einem Buero, Querformat"), run directly — map keywords to parameters:
- "Foto / fotorealistisch / realistisch" → `--style photo`
- "Illustration / gezeichnet / Comic" → `--style illustration`
- "Diagramm / Infografik / Schema" → `--style diagram`
- "Skizze / handgezeichnet" → `--style sketch`
- "Aquarell" → `--style watercolor`
- "3D / gerendert" → `--style 3d`
- "Querformat / landscape / breit" → `--aspect 16:9`
- "Hochformat / portrait / Story" → `--aspect 9:16`
- "Variationen / Alternativen" → `--count 3`

After generating, always show the user the output file path and suggest: "Soll ich das Bild oeffnen? (`open <path>`)"

### Describe — Interactive Mode

If the user just says "Schau dir das Bild an" without specifying what they want, ask:

> "Was soll ich mit dem Bild machen?
> - **Beschreiben** — Detaillierte Beschreibung (Motiv, Farben, Komposition)
> - **Analysieren** — Technische Analyse (Stil, Palette, sichtbarer Text)
> - **Text extrahieren** — Alle Texte, Zahlen, Daten aus dem Bild lesen
> - **Caption** — Kurze Bildbeschreibung in 1-2 Saetzen"

If the context is clear (e.g. user shares a screenshot and asks "Was steht da?"), run directly with `--task extract`.

## When to use
- User asks to generate, create, or make an image
- User wants a specific visual style (photo, sketch, diagram, etc.)
- User wants multiple variations of an image
- User has an image and wants it described, analyzed, or text extracted
- User mentions screenshot, photo, diagram, illustration, logo

## When NOT to use
- For audio files -> use audio skill
- For PDF documents -> use pdf-analysis skill
