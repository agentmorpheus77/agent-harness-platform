---
name: firecrawl-interact
description: "Use when you need to interact with a live web page - click buttons, fill forms, extract dynamic content, take screenshots, debug DOM structure, inspect CSS selectors, or navigate multi-step web flows. Triggers on requests like 'check this website', 'click on X', 'fill out the form', 'take a screenshot', 'inspect the DOM', 'debug the page', 'check the selectors', or when you need to see what a page looks like in a real browser. Also use when WebFetch fails or a site blocks scraping."
version: 0.1.0
---

# Firecrawl Interact — Browser Automation Skill

## Overview

Control a **real cloud browser** via the Firecrawl Interact API: navigate pages, click elements, fill forms, extract data, inspect DOM structure, and run Playwright code. The browser is a full Chromium instance — it renders JavaScript, handles SPAs, and can navigate to any URL including sites that block normal scraping.

### When to Use
- Debugging frontend issues (inspect live DOM, verify CSS selectors)
- Sites that block WebFetch or Firecrawl scrape (e.g. some scrape-blocked sites can still be reached via `page.goto()` inside an interact session)
- Extracting data from dynamic/JS-heavy pages
- Multi-step web interactions (login, search, navigate)
- Verifying how a page looks in a real browser

## Prerequisites

- Environment variable `FIRECRAWL_API_KEY` must be set
- Get a key at https://firecrawl.dev (free tier available)
- Uses cURL via Bash tool (no SDK installation needed)

## CRITICAL: Response Parsing Gotcha

Firecrawl responses often contain **non-UTF-8 control characters** that break `json.loads()`. You MUST sanitize before parsing:

```python
# WRONG — will crash on many responses:
d = json.loads(raw)

# RIGHT — always sanitize first:
import re
raw = sys.stdin.buffer.read()
clean = re.sub(rb'[\x00-\x1f\x7f-\x9f]', b' ', raw)
d = json.loads(clean)
```

**Standard parse helper** (use this for ALL Firecrawl responses):
```bash
| python3 -c "
import sys,re,json
text = sys.stdin.buffer.read().decode('latin-1')
clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
d = json.loads(clean)
# ... process d ...
"
```
**Important**: Use `decode('latin-1')` NOT `decode('utf-8')` — Firecrawl responses frequently contain
bytes that break UTF-8 decoding (e.g. `0xe2` without valid continuation bytes). Latin-1 never fails.

## Workflow

### Step 1: Create Session

Scrape any URL to get a `scrapeId`. This starts the browser session.

```bash
RESPONSE=$(curl -s -X POST "https://api.firecrawl.dev/v2/scrape" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.google.com", "formats": ["markdown"]}')

SCRAPE_ID=$(echo "$RESPONSE" | python3 -c "
import sys,re,json
raw = sys.stdin.buffer.read()
clean = re.sub(rb'[\x00-\x1f\x7f-\x9f]', b' ', raw)
d = json.loads(clean)
print(d.get('data',{}).get('metadata',{}).get('scrapeId',''))
")
echo "SCRAPE_ID: $SCRAPE_ID"
```

**Tip**: If the target site is blocked by Firecrawl's scrape endpoint (e.g. LinkedIn returns "we do not support this site"), start with a neutral URL like `https://www.google.com` and then use `page.goto()` in an interact call to navigate to the blocked site. The interact browser is NOT restricted the same way as the scrape endpoint.

### Step 2: Interact

Choose between **prompt** (AI-driven, 7 credits/min) or **code** (Playwright, 2 credits/min).

#### Option A: AI Prompt (simple tasks)
```bash
curl -s -X POST "https://api.firecrawl.dev/v2/scrape/$SCRAPE_ID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me the exact CSS class names of the h1 element and any headline elements on this page.", "timeout": 30}'
```
Response: `.output` contains the AI's natural language answer. `.stdout` may contain an accessibility tree snapshot.

#### Option B: Playwright Code (precise DOM inspection)
```bash
curl -s -X POST "https://api.firecrawl.dev/v2/scrape/$SCRAPE_ID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "PLAYWRIGHT_CODE_HERE",
    "language": "node",
    "timeout": 30
  }'
```
Response: `.result` contains the return value of the last expression. `.stdout` for console output.

#### Option C: Navigate to a different site within the session
```bash
curl -s -X POST "https://api.firecrawl.dev/v2/scrape/$SCRAPE_ID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "await page.goto(\"https://TARGET_URL\", {waitUntil: \"domcontentloaded\", timeout: 20000}); await new Promise(r => setTimeout(r, 3000)); const title = await page.title(); const url = page.url(); JSON.stringify({title, url});",
    "language": "node",
    "timeout": 45
  }'
```

### Step 3: ALWAYS Stop Session When Done
```bash
curl -s -X DELETE "https://api.firecrawl.dev/v2/scrape/$SCRAPE_ID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY"
```
Sessions cost credits per minute. Always stop explicitly!

## Proven Recipes (battle-tested)

### Inspect DOM: Get all h1 elements with classes
```json
{
  "code": "const h1s = await page.$$eval('h1', els => els.map(e => ({cls: e.className, text: e.textContent.trim().slice(0,100)}))); JSON.stringify({h1s});",
  "language": "node",
  "timeout": 30
}
```

### Inspect DOM: Get element details by selector
```json
{
  "code": "const data = await page.evaluate(() => { const r = {}; r.h1 = document.querySelector('h1')?.className; r.h1text = document.querySelector('h1')?.textContent?.trim(); r.h2s = [...document.querySelectorAll('h2')].slice(0,5).map(e => ({cls: e.className.slice(0,80), text: e.textContent.trim().slice(0,100)})); return r; }); JSON.stringify(data);",
  "language": "node",
  "timeout": 30
}
```

### Navigate to blocked site (workaround)
Start session with google.com, then navigate:
```json
{
  "code": "await page.goto('https://BLOCKED-SITE.com/page', {waitUntil: 'domcontentloaded', timeout: 20000}); await new Promise(r => setTimeout(r, 5000)); const title = await page.title(); JSON.stringify({title, url: page.url()});",
  "language": "node",
  "timeout": 45
}
```

### AI prompt for selector discovery (most convenient)
```json
{
  "prompt": "Look at the current page. I need you to tell me: 1) The exact CSS class of the h1 element. 2) The exact CSS class of the headline/subtitle element. 3) The exact CSS class of any location element. Report exact class names from the DOM.",
  "timeout": 30
}
```
This returns `.output` with natural language AND `.stdout` with the accessibility tree.

### Extract structured data
```json
{
  "code": "const data = await page.$$eval('.item', items => items.map(i => ({title: i.querySelector('h3')?.textContent, price: i.querySelector('.price')?.textContent}))); JSON.stringify(data);",
  "language": "node"
}
```

### Fill form and submit
```json
{"prompt": "Fill the email field with test@example.com, fill the password field with secret, then click the Login button"}
```

## Login Sessions & Interactive Live View

Some sites require authentication to show the real content (e.g. LinkedIn shows a public view
to unauthenticated browsers, but a completely different DOM when logged in). Firecrawl Interact
provides two ways to handle this:

### Method 1: Interactive Live View (recommended for user's own accounts)

Every interact response includes an `interactiveLiveViewUrl`. The user can open this URL in their
browser and **manually log in** by clicking and typing — just like a normal browser. Once logged in,
subsequent interact API calls use the authenticated session.

**Workflow:**
```bash
# 1. Start session and navigate to login page
SID=$(curl -s -X POST "https://api.firecrawl.dev/v2/scrape" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.google.com", "formats": ["markdown"]}' \
  | python3 -c "
import sys,re,json
text = sys.stdin.buffer.read().decode('latin-1')
clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
print(json.loads(clean)['data']['metadata']['scrapeId'])
")

# 2. Navigate to the target site (e.g. LinkedIn)
RESULT=$(curl -s -X POST "https://api.firecrawl.dev/v2/scrape/$SID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "await page.goto(\"https://www.linkedin.com/login\", {waitUntil: \"domcontentloaded\"}); await new Promise(r => setTimeout(r, 3000)); JSON.stringify({url: page.url()});",
    "language": "node", "timeout": 30
  }')

# 3. Extract the interactive live view URL
LIVE_URL=$(echo "$RESULT" | python3 -c "
import sys,re,json
text = sys.stdin.buffer.read().decode('latin-1')
clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
d = json.loads(clean)
print(d.get('interactiveLiveViewUrl',''))
")
echo "Open this URL for the user to log in: $LIVE_URL"

# 4. Tell the user: "Open this link and log in manually"
# 5. Wait for user to confirm they're logged in
# 6. Now all subsequent interact calls use the authenticated session!
```

**Key points:**
- The `interactiveLiveViewUrl` is a full interactive browser — user can click, type, scroll
- The `liveViewUrl` is read-only (view only, no interaction)
- Session state (cookies, localStorage) persists across interact calls
- The user logs in ONCE, then you can make as many API calls as needed
- **Never ask the user for their password** — let them type it in the live view

### Method 2: AI Prompt Login (for test/demo accounts only)

If you have non-sensitive credentials (test accounts), you can use a prompt:
```json
{"prompt": "Fill the email field with test@example.com and the password with demo123, then click Sign In"}
```

### Method 3: Saved Profiles (persistent sessions across scrapes)

Use the `profile` parameter on the initial scrape to save/reuse browser state:
```bash
curl -s -X POST "https://api.firecrawl.dev/v2/scrape" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.linkedin.com",
    "formats": ["markdown"],
    "profile": {"name": "linkedin-session", "saveChanges": true}
  }'
```
Next time you scrape with `"profile": {"name": "linkedin-session"}`, the browser reuses
the saved cookies/session — no re-login needed.

**Important:** Always stop the session when done so the profile gets saved:
```bash
curl -s -X DELETE "https://api.firecrawl.dev/v2/scrape/$SID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY"
```

## Real-World Example: LinkedIn DOM Inspection (with Login)

Successfully used on 2026-03-27 to debug Chrome extension selectors.
LinkedIn has completely different DOM when logged in vs logged out.

```bash
# 1. Start session from Google (LinkedIn blocks direct scrape)
SID=$(curl -s -X POST "https://api.firecrawl.dev/v2/scrape" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.google.com", "formats": ["markdown"]}' \
  | python3 -c "
import sys,re,json
text = sys.stdin.buffer.read().decode('latin-1')
clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
print(json.loads(clean)['data']['metadata']['scrapeId'])
")

# 2. Navigate to LinkedIn — get interactive URL for user login
RESULT=$(curl -s -X POST "https://api.firecrawl.dev/v2/scrape/$SID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "await page.goto(\"https://www.linkedin.com/login\"); await new Promise(r => setTimeout(r, 3000)); JSON.stringify({url: page.url()});",
    "language": "node", "timeout": 30
  }')
# Extract interactiveLiveViewUrl from RESULT and give it to the user to log in

# 3. After user logged in and navigated to the target profile:
#    Use AI prompt for selector discovery
curl -s -X POST "https://api.firecrawl.dev/v2/scrape/$SID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me the exact CSS class names and tag types for: 1) the name, 2) the headline, 3) the location, 4) the company.", "timeout": 30}'
# stdout contains accessibility tree with full element structure

# 4. Use code for precise DOM inspection
curl -s -X POST "https://api.firecrawl.dev/v2/scrape/$SID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "const info = await page.evaluate(() => { const section = document.querySelector(\"main section\"); const els = section.querySelectorAll(\"h1, h2, h3, p, a\"); return [...els].filter(e => e.textContent.trim().length > 1 && e.textContent.trim().length < 200).slice(0,20).map(e => ({tag: e.tagName, cls: e.className.toString().slice(0,80), text: e.textContent.trim().slice(0,150)})); }); JSON.stringify(info);",
    "language": "node", "timeout": 30
  }'
# Discovered: LinkedIn 2026 logged-in uses obfuscated hash classes
# Name = first H2 in main section (NOT h1!)
# Headline = long P tag, Company = P with dot separator, Location = P with comma pattern

# 5. ALWAYS stop session
curl -s -X DELETE "https://api.firecrawl.dev/v2/scrape/$SID/interact" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY"
```

### Key Learnings from LinkedIn Case
- **Logged-out** view uses semantic classes (`top-card-layout__title`) — name in H1
- **Logged-in** view (2026) uses obfuscated hashes (`_743f2250`) — name in H2
- Class-based selectors break on obfuscated sites → use **structural selectors** instead
- AI prompt mode returns accessibility tree in `.stdout` — very useful for element discovery
- Interactive Live View lets the user log in without sharing credentials

## Response Fields Reference

| Mode | Field | Description |
|------|-------|-------------|
| Prompt | `.output` | AI's natural language answer |
| Prompt | `.stdout` | Accessibility tree snapshot (very useful!) |
| Code | `.result` | Return value of last expression |
| Code | `.stdout` | Console output / print statements |
| Code | `.stderr` | Error output |
| Both | `.success` | Boolean |
| Both | `.liveViewUrl` | Read-only browser view URL |
| Both | `.interactiveLiveViewUrl` | Interactive browser control URL |

## Cost & Limits

| Mode | Cost | Best For |
|------|------|----------|
| Code only | 2 credits/min | DOM inspection, precise selectors |
| AI prompt | 7 credits/min | Discovery, complex tasks |
| Scrape | 1 credit | Starting a session |

- **Timeout**: Default 30s, max 300s
- **Session TTL**: ~10 min inactivity auto-expire
- **Always stop sessions** to avoid unnecessary billing

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Parsing crash on response | Always sanitize control chars before `json.loads()` |
| Target site blocked by scrape | Start with google.com, then `page.goto()` to target |
| Session expired error | Create a new scrape session |
| Empty `.output` | Check `.stdout` — AI prompt responses also include accessibility tree there |
| Code returns empty | Make sure last expression is `JSON.stringify(...)` |
| Forgot to stop session | Credits keep billing! Always DELETE when done |
