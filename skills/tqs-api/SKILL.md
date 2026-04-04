---
name: tqs-api
description: "Use when the user wants to interact with the CDB TQS production backend — list documents, search knowledge, check health, manage knowledge areas, or query the Corporate Digital Brain. Triggers on requests like 'list documents', 'show TQS documents', 'search in TQS', 'TQS health', 'knowledge areas'."
version: 0.1.0
---

# CDB TQS API — Production Backend Interaction

## Overview

Interact with the **CDB TQS production backend** via the BFF proxy. Uses Azure AD authentication (`az account get-access-token`) to obtain a Bearer token, then calls the BFF at `https://cdbos.de/api/v1/tqs/*` which proxies to the internal TQS backend.

### Architecture
```
Claude Skill → AppGW (cdbos.de) → BFF (cdb-webos-bff) → TQS Backend (internal)
```

### Prerequisites
- Azure CLI (`az`) must be installed and logged in (`az login`)
- User must have an active Azure AD session with access to the CDB tenant
- First-time setup: `az login --tenant "98ceeb53-755d-4a99-b1bc-8154b0f982ef" --scope "api://bfc31465-9282-4d18-8a6a-f3007b42832f/access_as_user"`

### Security
- No secrets stored in code — tokens are fetched at runtime from the Azure CLI cache
- Tokens are short-lived (60-90 minutes)
- All requests go through AppGW WAF + BFF JWT validation
- Users only see documents they have access to (Knowledge Area permissions enforced server-side)

## Tools

### list-documents
List documents from the TQS backend with optional filtering.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/list_documents.py [--knowledge-area <name>] [--status <status>] [--search <term>] [--limit <n>] [--offset <n>]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --knowledge-area | No | Filter by knowledge area name |
| --status | No | Filter by status (processing, ready, error) |
| --search | No | Search term for title/filename |
| --limit | No | Max results (default: 50) |
| --offset | No | Pagination offset (default: 0) |

**Examples:**
```bash
# List all documents
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/list_documents.py

# Filter by knowledge area
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/list_documents.py --knowledge-area engineering

# Search for specific documents
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/list_documents.py --search "Hilti" --limit 10
```

### health
Check health status of the TQS backend.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/health.py
```

**Example:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/health.py
```

## When to use
- User asks to list, search, or check documents in TQS/CDB production
- User wants to check TQS backend health or connectivity
- User wants to interact with the Corporate Digital Brain API

## When NOT to use
- Local development testing (use curl directly against localhost:8000)
- Modifying code in the cdb_tqs or cdb-webos2 repositories
