---
name: git-weekly-summary
description: AI-powered weekly git activity summary — structured by themes with optional infographic.
version: 0.1.0
---

# Git Weekly Summary

Analyze a git repository and generate a structured overview of work done in a given time period.

## Tools

### weekly_summary
Collect git history (commits, files changed, lines added/removed) and generate an AI-powered summary.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/weekly_summary.py --repo <path> [--days 7] [--author <name>] [--language de|en] [--visual <path>]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --repo | No | Path to git repository (default: current directory) |
| --days | No | Number of days to look back (default: 7) |
| --author | No | Filter by author name or email (default: auto-detects current git user) |
| --all-authors | No | Show commits from all authors instead of just the current user |
| --language | No | Output language (default: de) |
| --visual | No | Output path for infographic image (png). Generates a visual based on the text summary. |

**Examples:**
```bash
# This week's work in the current repo
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/weekly_summary.py

# Last 14 days, specific repo
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/weekly_summary.py --repo ~/projects/my-app --days 14

# All team members
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/weekly_summary.py --repo ~/projects/my-app --all-authors

# English output
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/weekly_summary.py --language en

# With visual infographic
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/weekly_summary.py --visual ~/Desktop/weekly-report.png
```

## When to use
- User asks "What did I work on this week?"
- User wants a weekly report or activity summary
- User says "Zeig mir was diese Woche passiert ist"
- User wants to prepare a standup or status update from git history
- User asks for a recap of recent changes in a repo
- User wants a visual/infographic of their weekly work → use `--visual`

## When NOT to use
- For a simple `git log` or `git status` — use the `/cdb-skills:status` command instead
- For code review — use `/cdb-skills:review`
- For a single commit message — just use git directly
