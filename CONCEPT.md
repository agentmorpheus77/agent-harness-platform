# Agent Harness Platform — Konzept

**Stand:** 04.04.2026  
**Autor:** Morpheus + Chris (Brainstorming-Session)  
**Status:** Konzeptphase — bereit für Phase 1 Umsetzung  
**Repo:** https://github.com/agentmorpheus77/agent-harness-platform

---

## 🎯 Vision

Eine Plattform, auf der User selbstständig neue Features entwickeln können — indem sie ein GitHub Issue einreichen. Ein AI-Agent implementiert das Feature automatisch, deployed eine Preview-Umgebung und benachrichtigt den User zum Testen. Der User approved oder gibt Feedback, danach wird gemergt.

> *"Submit an Issue. Get a working feature. No developer needed."*

**Vorbild:** Paperclip — klare Approval-Gates, transparente Agent-Aktivität, Boards die man versteht.

---

## 🏗️ Gesamt-Architektur

```
┌──────────────────────────────────────────────────────────────┐
│                     AGENT HARNESS UI                         │
│              (FastAPI + React + Tailwind CSS)                 │
│                                                              │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ Repo-Select │  │  Issues (CRUD)   │  │    Settings    │  │
│  │  (Dropdown) │  │  Liste / Status  │  │  API Keys etc. │  │
│  └─────────────┘  └──────────────────┘  └────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              ISSUE CREATOR (Chat-Interface)           │   │
│  │  🎙️ Voice Input → Transkript  |  📎 Attachments      │   │
│  │  💬 Agent-Dialog (Rückfragen) |  🎨 Mockup-Preview   │   │
│  │  ✅ Confirm → Issue einreichen                        │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────┐       ┌──────────────────────┐
│   GitHub API     │       │   OpenRouter API      │
│  Issues / PRs    │       │  (Model-agnostisch)   │
└──────────────────┘       └──────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────────────────────────────────┐
│              CODING AGENT (Agentic Loop)          │
│  • Git Worktree pro Issue                         │
│  • Tool-Calls: read/write/run/git                 │
│  • Skills aus cdb-skills laden                    │
│  • Live-Streaming Output → UI                     │
└──────────────────────────┬───────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Railway Preview      │
              │   Deploy (auto)        │
              │   + Demo-Seed-Daten    │
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Morpheus Notification │
              │  Preview-URL → User    │
              │  ✅ Approve / ❌ Retry │
              └────────────────────────┘
```

---

## 📱 UI-Struktur

### Tech Stack

| Layer | Tech |
|-------|------|
| **Backend** | FastAPI (Python) |
| **Frontend** | React + TypeScript + Vite |
| **Styling** | Tailwind CSS (neueste Version) |
| **Komponenten** | shadcn/ui (neueste Version, konsistent & anpassbar) |
| **Theme** | Dark + Light Mode, von Anfang an |
| **Sprachen** | Multilingual (i18n, mind. DE + EN) |
| **State** | Zustand oder TanStack Query |

### Design-Prinzipien

- **Einheitlich:** shadcn/ui als Basis — konsistente Komponenten, kein Mix-and-Match
- **Aktuell:** Immer neueste stable Versionen (shadcn/ui, Tailwind, React)
- **Anpassbar:** Tailwind CSS Variables für einfaches Rebranding
- **Dark/Light:** System-Default + manueller Toggle, von Tag 1
- **Multilingual:** i18next, alle Strings externalisiert, DE/EN minimal

---

### Navigation (3 Hauptbereiche)

#### 1. Repo-Selector (Header)
```
┌─────────────────────────────────────────────────────┐
│  🤖 Agent Harness  │  [BIK-GmbH/cdb-skills ▼]  │ ⚙️ │
└─────────────────────────────────────────────────────┘
```
- Dropdown: alle konfigurierten Repos
- Umschalten lädt neuen Kontext (Issues, Skills)
- Settings-Icon → API Keys + Konfiguration

#### 2. Issues-Übersicht (CRUD)
- Liste aller Issues mit Status (Open / In Progress / Done / Closed)
- Filter: Typ (Feature/Bug/Chore), Assignee, Label
- Klick → Issue-Detail mit Live-Agent-Output
- "+ Neues Issue" → öffnet Issue-Creator

#### 3. Issue-Creator (Chat-Interface)
Eigener View — der Kern der Platform:

```
┌──────────────────────────────────────────────────────┐
│  Neues Issue — BIK-GmbH/cdb-skills                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  🤖 Agent: Ich hab mir den Code kurz angeschaut.    │
│           Was soll ich bauen?                        │
│                                                      │
│  👤 User: [Chat-Verlauf...]                         │
│                                                      │
│  🤖 Agent: [Mockup-Bild wenn UI-Feature]            │
│           Habe ich das richtig verstanden?           │
│                                                      │
├──────────────────────────────────────────────────────┤
│  [📎] [🎙️ Aufnehmen]  Tippen oder sprechen...  [→] │
└──────────────────────────────────────────────────────┘
```

#### 4. Settings
```
API Keys:
  OpenRouter:  [••••••••••••••••]  [Testen]
  Gemini:      [••••••••••••••••]  [Testen]
  Firecrawl:   [••••••••••••••••]  [Testen]
  Railway:     [••••••••••••••••]  [Testen]
  GitHub:      [••••••••••••••••]  [Testen]

Repositories:
  [+ Repository hinzufügen]

Standard-Modell:
  [Dropdown: Fast & Free / Balanced / Premium]

Sprache / Theme: [DE ▼]  [🌙 Dark ●  ☀️ Light]
```

---

## 🔄 Vollständiger Workflow

### Schritt 1: Repo-Select + Kontext laden

Wenn User ein Repo auswählt:

```python
# Backend startet automatisch:
1. GitHub API → Issues laden
2. Shallow Clone / File-Tree lesen (kein voller Clone)
3. Passende Skills aus cdb-skills identifizieren:
   - Hat package.json?     → typescript-best-practices
   - Hat Railway config?   → cicd-pipeline
   - Hat i18n-Ordner?      → i18n-internationalization
   - Hat tests/?           → testing-qa
   - Hat Website/UI?       → ui-ux-guidelines + image/generate
   - Hat firecrawl ref?    → firecrawl-interact
4. Skills in System-Prompt laden → Agent kennt den Stack
```

### Schritt 2: Issue-Creator Chat

```
User drückt "+ Neues Issue"

Agent liest:
- README.md des Repos
- File-Tree (Top-Level)
- Letzte 5 Issues (Kontext)
- Geladene Skills

Agent sagt:
"Ich hab mir [repo] kurz angeschaut. Es ist ein [TypeScript/React] Projekt
mit Railway-Deploy. Was soll ich bauen?"

User spricht (🎙️) oder tippt:
→ Audio → Whisper (audio Skill aus cdb-skills) → Transkript

Agent stellt Rückfragen (max 3-4):
→ Typ? Feature / Bug / Chore
→ Acceptance Criteria?
→ Betroffene Bereiche?

Optional: Agent generiert Mockup:
→ image/generate Skill (Gemini) → Wireframe-Bild
→ "Meinst du sowas in der Art?"

Agent zeigt Issue-Draft:
→ Titel + Body (Englisch, nach issue-writer Template)
→ "Passt das? Oder Änderungen?"

User bestätigt:
→ GitHub Issue wird erstellt (via gh API)
→ Label + Assignee optional
```

### Schritt 3: Coding Agent startet

```bash
# Pro Issue: isolierter Worktree
git worktree add ../worktrees/issue-{number} -b feature/issue-{number}

# Agentic Loop (OpenRouter)
POST https://openrouter.ai/api/v1/chat/completions
{
  "model": "<user-gewählt>",
  "messages": [system_prompt_mit_skills + issue_kontext],
  "tools": [read_file, write_file, run_command, git_commit],
  "stream": true  # Live-Output in UI
}
```

**Live-Output:**
```
┌─────────────────────────────────────────────────────┐
│  🤖 Agent arbeitet an Issue #42                     │
├─────────────────────────────────────────────────────┤
│  ✅ Repo geclont (Worktree: feature/issue-42)       │
│  📖 Lese src/components/Toolbar.tsx...              │
│  ✍️  Schreibe src/components/ExportButton.tsx...   │
│  🧪 Führe Tests aus...                              │
│  ✅ 12/12 Tests bestanden                           │
│  📤 Pushe Branch...                                 │
│  🔗 PR geöffnet: #43                               │
└─────────────────────────────────────────────────────┘
```

### Schritt 4: Railway Preview Deploy

```toml
# railway.toml im Target-Repo
[deploy]
startCommand = "npm run seed && npm run start"

[environments.preview]
# Automatisch für jeden PR-Branch
# Seed-Daten beim Start
```

Railway liefert URL: `https://feature-issue-42-xyz.up.railway.app`

### Schritt 5: Notification + Approval

```
Morpheus → User (WhatsApp/Telegram):
"✅ Feature #42 ist fertig!

Was wurde gebaut: Export-Button als PDF
Teste hier: https://feature-issue-42-xyz.up.railway.app
Login: demo@example.com / demo123

✅ Antwort mit 'Looks good' → Merge
❌ Antwort mit Feedback → Agent iteriert"
```

### Schritt 6: Merge oder Iterate

| User-Antwort | Aktion |
|-------------|--------|
| ✅ Approve | PR merge, Railway Env löschen, Issue schließen |
| ❌ + Feedback | Feedback → Agent → neuer Commit → Railway updated → neue Notification |

---

## 🛠️ Skill-System

### Agnostisches Skill-Loading

**Skills = Markdown-Dateien** (aus cdb-skills Repo) → in System-Prompt laden → funktioniert mit JEDEM Modell.

```python
# Automatische Skill-Auswahl per Repo-Analyse
def load_skills_for_repo(repo_path: str) -> list[str]:
    skills = []
    
    if (repo_path / "package.json").exists():
        skills.append(read_skill("typescript-best-practices"))
    if (repo_path / "railway.toml").exists():
        skills.append(read_skill("cicd-pipeline"))
    if has_i18n_files(repo_path):
        skills.append(read_skill("i18n-internationalization"))
    if has_test_directory(repo_path):
        skills.append(read_skill("testing-qa"))
    if has_ui_components(repo_path):
        skills.append(read_skill("ui-ux-guidelines"))
    
    return skills
```

### Skills aus cdb-skills (direkt nutzbar)

| Skill | Datei | Wann geladen |
|-------|-------|-------------|
| **audio** | `skills/audio/tools/transcribe.py` | Immer (Voice-Input) |
| **image** | `skills/image/tools/generate.py` | Bei UI-Features → Mockup |
| **issue-writer** | `skills/issue-writer/SKILL.md` | Issue-Creator Chat |
| **firecrawl-interact** | `skills/firecrawl-interact/` | Repo hat Website |
| **pr-review** | `skills/pr-review/` | Approval-Workflow |
| **typescript-best-practices** | `skills/typescript-best-practices/SKILL.md` | JS/TS Repos |
| **ui-ux-guidelines** | `skills/ui-ux-guidelines/SKILL.md` | Frontend-Repos |
| **testing-qa** | `skills/testing-qa/SKILL.md` | Repos mit Tests |
| **security-best-practices** | `skills/security-best-practices/SKILL.md` | Immer (Backend) |
| **cicd-pipeline** | `skills/cicd-pipeline/SKILL.md` | Railway-Repos |

### Shared LLM Client (cdb-skills)

`shared/llm.py` ist bereits vorhanden — provider-agnostisch:

```python
from cdb_skills.shared.llm import complete

# Funktioniert mit Gemini, OpenAI, Anthropic, OpenRouter
response = complete(
    prompt="Analyse diese Codebasis...",
    provider="openrouter",
    model="qwen/qwen-2.5-coder-32b-instruct:free"
)
```

---

## 🤖 Modell-Strategie (OpenRouter)

**Alle Calls laufen über OpenRouter** — kein Provider-Lock-in.

### Kategorien (keine spezifischen Modelle — aktuell halten via OpenRouter-Liste)

| Kategorie | Use Case | Kosten |
|-----------|----------|--------|
| **Fast & Free** | Issue-Chat, Rückfragen, einfache Bugs | $0 |
| **Balanced** | Standard-Features, mittlere Komplexität | ~$0.50/Issue |
| **Premium** | Komplexe Architekturen, große Refactorings | ~$2-5/Issue |

**User wählt Kategorie pro Issue** — bewusste Kosten-Entscheidung.

### Transparenz-Anzeige

```
Modell: Qwen 2.5 Coder (Free) ▼
Geschätzte Kosten: $0.00
Token verwendet: 12.450 / 32.000
```

---

## 🔑 API-Key Management

**Alle Keys im Settings-Bereich** — niemals hardcoded.

```python
# Backend: Keys in .env / DB (verschlüsselt)
OPENROUTER_API_KEY=...
GEMINI_API_KEY=...
FIRECRAWL_API_KEY=...
RAILWAY_API_KEY=...
GITHUB_TOKEN=...
OPENAI_WHISPER_KEY=...  # Optional: für Audio-Transkription
```

**UI Settings-Page:**
- Key eingeben → sofort testen ("Test"-Button)
- Welche Skills/Features ohne Key nicht verfügbar sind (klar anzeigen)
- Keys werden verschlüsselt gespeichert (nicht im Plain-Text)

---

## 📊 Kosten-Übersicht

| Komponente | Plan | Kosten/Monat |
|-----------|------|-------------|
| Railway Preview Envs | Pro | ~$20 |
| OpenRouter (20 Issues) | Pay-per-use | ~$10-40 |
| Firecrawl | Free Tier | $0 |
| **Gesamt** | | **~$30-60** |

---

## 🚨 Constraints & Grenzen

### Data Privacy
- Preview-Environments: **ausschließlich Seed/Demo-Daten** — nie Produktionsdaten
- Seed-Skript im Target-Repo Pflicht: `npm run seed` / `python seed.py`

### Security
- Agent hat nur Zugriff auf Target-Repo-Worktree
- Keine Produktion-DB-Credentials für Agents
- GitHub Token: nur `repo` Scope, kein Admin

### Parallelität
- Railway Pro: unbegrenzte Preview Envs
- Worktrees: unbegrenzt parallel, aber Git-Konflikte möglich
- Lösung: Issues mit überlappenden Files → sequentiell queuen

---

## 🗺️ Rollout-Plan

### Phase 1 — Grundgerüst (Woche 1-2)
- [ ] FastAPI Backend (Skeleton + GitHub API Integration)
- [ ] React Frontend: Repo-Selector + Issues-Liste + Settings
- [ ] OpenRouter Integration (shared/llm.py erweitern)
- [ ] Issue-Creator: einfacher Chat (Text, kein Voice noch)
- [ ] Erster End-to-End Test: Issue einreichen → GitHub

### Phase 2 — Agent + Deploy (Woche 3-4)
- [ ] Agentic Loop: Worktree + Tool-Calls + git push
- [ ] Live-Streaming Output in UI (WebSocket)
- [ ] Railway Integration: PR → Preview URL
- [ ] Morpheus-Notification nach Deploy

### Phase 3 — Voice + Mockups (Woche 5-6)
- [ ] Voice-Input: 🎙️ Button → Whisper → Transkript
- [ ] Image-Attachment im Chat
- [ ] Mockup-Generator: image/generate Skill → Wireframe
- [ ] Approval-Workflow: ✅/❌ → Merge oder Iterate

### Phase 4 — Skills + Multilingual (Woche 7-8)
- [ ] Automatisches Skill-Loading per Repo-Analyse
- [ ] i18n: DE + EN komplett
- [ ] Dark/Light Theme polish
- [ ] Multi-Repo Support

### Phase 5 — Dog-Fooding (ongoing)
- [ ] Platform selbst auf Railway deployen
- [ ] agent-harness-platform als erstes Test-Repo nutzen
- [ ] Erste externe User einladen

---

## 📁 Geplante Repo-Struktur

```
agent-harness-platform/
├── CONCEPT.md                    ← dieses Dokument
├── README.md
├── .env.example
│
├── backend/                      ← FastAPI
│   ├── main.py
│   ├── api/
│   │   ├── repos.py              ← GitHub Repo-Management
│   │   ├── issues.py             ← Issue CRUD + Creator
│   │   ├── agent.py              ← Coding Agent Loop
│   │   ├── deploy.py             ← Railway Integration
│   │   └── settings.py           ← API Key Management
│   ├── core/
│   │   ├── skill_loader.py       ← Automatisches Skill-Loading
│   │   ├── llm_client.py         ← OpenRouter Wrapper
│   │   ├── worktree.py           ← Git Worktree Manager
│   │   └── notify.py             ← Morpheus Notification
│   └── models/
│       ├── issue.py
│       └── settings.py
│
├── frontend/                     ← React + TypeScript + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── RepoSelector/
│   │   │   ├── IssueList/
│   │   │   ├── IssueCreator/     ← Chat-Interface
│   │   │   ├── AgentOutput/      ← Live-Streaming
│   │   │   └── Settings/
│   │   ├── i18n/
│   │   │   ├── de.json
│   │   │   └── en.json
│   │   └── lib/
│   │       ├── api.ts
│   │       └── theme.ts
│   └── package.json
│
└── docs/
    ├── setup.md
    └── railway-setup.md
```

---

## 🔮 Langfristige Vision

1. **Self-hosted SaaS** — "Connect your GitHub → Users submit Issues → AI builds it"
2. **CDBrain-Integration** — Enterprise-Kunden können ihr Wissenssystem durch Issues erweitern  
3. **Skill Marketplace** — Community teilt Skills für verschiedene Stacks
4. **Multi-Agent** — Mehrere spezialisierte Agents parallel (Frontend-Agent, Backend-Agent, Test-Agent)

---

*"The users are the product team. The AI is the engineering team."*

---

*Letzte Aktualisierung: 04.04.2026 — Konzept abgeschlossen, bereit für Phase 1*
