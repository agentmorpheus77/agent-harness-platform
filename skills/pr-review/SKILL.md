---
name: pr-review
description: "Use when the user shares a GitHub PR URL or number and wants a code review. Triggers on 'review PR', 'PR review', GitHub pull request URLs, or when the user asks for feedback on a pull request."
version: 0.1.0
---

# PR Review — Dual-LLM Code Review

Review GitHub pull requests against BIK team standards using two LLM perspectives.

## Tools

### review
Fetch PR context and get an LLM review via the configured provider (default: Gemini).

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/review.py --pr <number> --repo <owner/repo> [--language de]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --pr | Yes | PR number |
| --repo | Yes | GitHub repo (owner/repo format) |
| --language | No | Output language (default: de) |

**Examples:**
```bash
# Review PR #42
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/review.py --pr 42 --repo BIK-GmbH/my-project

# Review with English output
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/review.py --pr 42 --repo BIK-GmbH/my-project --language en
```

### fetch_context
Fetch PR metadata and diff without running an LLM review. Useful for manual inspection.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/fetch_context.py --pr <number> --repo <owner/repo>
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --pr | Yes | PR number |
| --repo | Yes | GitHub repo (owner/repo format) |

## Before running tools

### How to use (Dual-LLM Review)

When the user asks to review a PR:

1. Parse the PR number and repo from the URL or user input
   - `https://github.com/BIK-GmbH/repo/pull/42` → `--pr 42 --repo BIK-GmbH/repo`
2. Run `review.py` to get the **LLM review** (Gemini by default)
3. Read the `result.diff` from the JSON output
4. Perform your **own review** of the same diff against BIK team standards
5. Present both reviews side by side:

```markdown
## PR Review: [title] (#[number])

### Gemini Review
[LLM review output]

### Claude Review
[Your own analysis]

### Vergleich
- **Uebereinstimmung:** [Issues both found]
- **Nur Gemini:** [Issues only Gemini found]
- **Nur Claude:** [Issues only Claude found]

### Empfehlung
[Overall assessment]
```

This dual perspective helps catch more issues — different models have different blind spots.

## When to use
- User shares a GitHub PR URL
- User asks to review a PR or pull request
- User mentions "PR review", "Code Review", "review PR #42"

## When NOT to use
- For reviewing local uncommitted changes → use `/review` command
- For reviewing a single file → use `/review <filepath>` command
- For explaining code → future code skill
