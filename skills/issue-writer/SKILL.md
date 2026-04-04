---
name: issue-writer
description: "Use when the user wants to create a GitHub issue, write a bug report, feature request, or ticket. Triggers on 'create issue', 'file a bug', 'feature request', 'leg ein Issue an', 'erstell ein Ticket', 'I need a ticket', or any request to write/create an issue or ticket."
version: 0.1.0
---

# Issue Writer

Create well-structured GitHub issues through a guided conversation. Interview the user, draft the issue, let them review, then create it via `gh`.

## How this skill works

This skill has NO tools. You (Claude) drive the entire flow as a conversation, following the phases below. At the end, you use `gh issue create` to create the issue.

**Language rule:** Converse in whatever language the user speaks. The issue title and body are ALWAYS in English.

---

## Phase 1: Repository

1. Detect the current repo:

```bash
gh repo view --json nameWithOwner -q .nameWithOwner
```

2. Ask the user:

> "Should I create the issue in **[detected repo]**, or a different one?"

3. If the user wants a different repo:
   - Ask which repo they mean
   - If unclear, run `gh repo list --limit 20` and present options
   - Confirm the chosen repo before proceeding

---

## Phase 2: Issue Type

4. Ask:

> "What kind of issue is this?
> - **Feature** — New functionality or enhancement
> - **Bug** — Something is broken or behaving unexpectedly
> - **Chore** — Refactoring, tech debt, dependency updates, cleanup"

5. If the user is unsure or their description doesn't clearly fit, suggest a type based on what they described and ask for confirmation.

---

## Phase 3: Description & Interview

6. Ask:

> "Describe what you need — keep it casual, I'll ask follow-up questions."

7. After the user describes their need, ask **targeted follow-up questions based on type**. Skip questions the user already answered. Ask 2-4 questions max — enough to fill the template, not so many it becomes tedious.

**Feature follow-ups:**
- What is the desired outcome from a user perspective?
- Are there specific acceptance criteria you have in mind?
- Any technical constraints or dependencies to be aware of?

**Bug follow-ups:**
- How do you reproduce it? (step by step)
- What did you expect to happen?
- What happens instead?
- Any error messages or logs?

**Chore follow-ups:**
- What exactly is in scope?
- Why now — what's the motivation?
- Any risks or dependencies?

---

## Phase 4: Draft & Review

8. Compose the issue using the matching template below. Present it as a Markdown preview:

> "Here's the draft:"
>
> **Title:** [title]
>
> [full body in the template format]
>
> "Want to change anything, or does this look good?"

9. If the user requests changes, revise and present again. Repeat until approved.

---

## Phase 5: Labels, Assignee & Create

10. Ask about labels (optional):

> "Any labels? (e.g., `bug`, `enhancement`, `priority:high`) — or skip."

11. Ask about assignee (optional):

> "Assign to someone? — or skip."

12. Create the issue:

```bash
# Write body to temp file (avoids escaping issues)
cat > /tmp/issue-body.md << 'ISSUE_EOF'
[issue body here]
ISSUE_EOF

# Create the issue
gh issue create --repo <owner/repo> --title "<title>" --body-file /tmp/issue-body.md [--label "<labels>"] [--assignee "<assignee>"]

# Clean up
rm -f /tmp/issue-body.md
```

13. Show the issue URL to the user.

---

## Issue Templates

### Feature

```markdown
## Summary
[One sentence: what should be built and why]

## Desired Outcome
[What should work when done — from user perspective]

## Acceptance Criteria
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]

## Technical Notes
[Optional: implementation hints, affected files, dependencies]
```

### Bug

```markdown
## Summary
[One sentence: what is broken]

## Steps to Reproduce
1. [Step]
2. [Step]

## Expected Behavior
[What should happen]

## Actual Behavior
[What happens instead]

## Technical Notes
[Optional: error messages, logs, affected files]
```

### Chore

```markdown
## Summary
[One sentence: what should be cleaned up/improved and why]

## Scope
- [ ] [Specific item]
- [ ] [Specific item]

## Technical Notes
[Optional: affected files, dependencies, risks]
```

### Template Rules

- **Summary** is always required — one clear sentence
- **Technical Notes** is always optional — only include if the user mentioned something relevant
- Fill the template from the conversation — the user never sees or fills a template directly
- Acceptance Criteria / Steps to Reproduce / Scope must be concrete and testable
- If the user didn't provide enough for a section, ask — don't guess

---

## When to use
- User wants to create a GitHub issue
- User says "create issue", "file a bug", "feature request"
- User says "Leg ein Issue an", "Erstell ein Ticket"
- User wants to write a structured bug report or feature request
- User invokes `/cdb-skills:create-issue`

## When NOT to use
- User wants to read or list existing issues — use `gh issue list` directly
- User wants to close or comment on an issue — use `gh` directly
- User wants a PR, not an issue — use `gh pr create` or `/cdb-skills:review`
