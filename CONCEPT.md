# Agent Harness Platform — Konzept

**Stand:** 04.04.2026  
**Autor:** Morpheus (Brainstorming mit Chris)  
**Status:** Konzeptphase — noch nichts umgesetzt

---

## 🎯 Vision

Eine Plattform, auf der User selbstständig neue Features entwickeln können — indem sie einfach ein GitHub Issue einreichen. Ein AI-Agent implementiert das Feature automatisch, deployed eine Preview-Umgebung und benachrichtigt den User zum Testen. Der User approved oder gibt Feedback, danach wird gemergt.

**Kernsatz:** "Submit an Issue. Get a working feature. No developer needed."

---

## 🏗️ Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER                                      │
│   Submits GitHub Issue (Feature Request / Bug)                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MORPHEUS (OpenClaw)                            │
│   Issue Watcher via gh-issues Skill (--watch / --cron)          │
│   • Validiert Issue (Label, Format)                              │
│   • Erstellt Task in Paperclip (optional)                        │
│   • Spawnt Claude Code Agent                                     │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CLAUDE CODE (Agent)                            │
│   • git worktree add → isolierter Branch pro Issue               │
│   • Implementiert Feature                                        │
│   • Schreibt Tests                                               │
│   • git push → PR öffnen                                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RAILWAY (Preview Environment)                  │
│   • PR-Trigger → automatischer Deploy                            │
│   • Eigene Subdomain pro Environment                             │
│   • Demo-Daten via Seed-Skript beim Start                        │
│   • Ephemeral: wird nach Merge/Close gelöscht                    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MORPHEUS → USER NOTIFICATION                   │
│   • WhatsApp/Telegram: "Dein Feature ist fertig!"                │
│   • Preview-URL + kurze Zusammenfassung                          │
│   • Approval-Workflow: "✅ Sieht gut aus" / "❌ Feedback geben"  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    ✅ APPROVED               ❌ CHANGES REQUESTED
    → PR Merge                → Feedback → Claude Code
    → Railway Env deleted     → Agent iteriert
    → Issue closed
```

---

## 📋 Workflow im Detail

### 1. Issue-Einreichung (User)

```markdown
# Issue Format (empfohlen)
**Titel:** [FEATURE] Exportfunktion für PDF hinzufügen

**Beschreibung:**
Als User möchte ich meine Daten als PDF exportieren können.

**Akzeptanzkriterien:**
- [ ] Button "Export als PDF" in der Toolbar
- [ ] Erzeugt valides PDF mit aktuellem Stand
- [ ] Dateiname: {projectname}-{datum}.pdf

**Label:** feature | priority:medium
```

### 2. Morpheus triggert (automatisch via Cron)

```bash
# gh-issues Skill läuft alle X Minuten
/gh-issues owner/repo --label feature --cron --interval 5

# Oder: GitHub Webhook → direkt an OpenClaw
```

**Morpheus-Logik:**
- Prüft Labels: nur `feature` / `bug` / `improvement` werden verarbeitet
- Prüft `harness:true` Label oder Konfiguration pro Repo
- Schreibt Session-Kontext + startet Claude Code

### 3. Claude Code arbeitet

```bash
# Pro Issue: Worktree anlegen
git worktree add ../feature-issue-42 -b feature/issue-42

# Claude Code mit Kontext
claude --permission-mode bypassPermissions --print "
Repo: owner/repo
Issue #42: [Titel + Beschreibung]
Akzeptanzkriterien: [Liste]

Implementiere das Feature. Schreibe Tests. Öffne am Ende einen PR.
Am Ende: openclaw system event --text 'Issue #42 implemented, PR ready' --mode now
"
```

**Worktree-Vorteile:**
- Jedes Issue = eigenes Verzeichnis, keine Konflikte
- Mehrere Issues parallel
- Einfach zu cleanen: `git worktree remove`

### 4. Railway Preview Deploy

**Trigger:** `git push` → PR → Railway GitHub Integration

**railway.toml Konfiguration:**
```toml
[deploy]
startCommand = "npm run seed && npm run start"
healthcheckPath = "/health"
healthcheckTimeout = 30

[environments.preview]
# Wird automatisch für jeden PR-Branch erstellt
```

**Demo-Daten Seed-Skript:**
```javascript
// scripts/seed.js
// Läuft nur in Preview-Environments
if (process.env.RAILWAY_ENVIRONMENT_NAME?.startsWith('pr-')) {
  await seedDemoData({
    users: 5,
    projects: 3,
    data: 'realistic-fixtures'
  });
}
```

**Resultat:** `https://feature-issue-42-xyz.up.railway.app`

### 5. User Notification

```
Morpheus → User (WhatsApp):
"✅ Feature #42 ist fertig!

📋 Was wurde gebaut:
• Exportfunktion für PDF in der Toolbar
• Dateiname: {projectname}-{datum}.pdf

🔗 Testen: https://feature-issue-42-xyz.up.railway.app

Login: demo@example.com / demo123

📝 Feedback:
Antwort mit ✅ wenn OK
Antwort mit ❌ + Beschreibung wenn Änderungen nötig"
```

### 6. Approval Workflow

**User sagt ✅:**
- Morpheus merged PR automatisch (via `gh pr merge`)
- Railway löscht Preview-Environment
- Issue wird geschlossen
- User bekommt Bestätigung

**User sagt ❌ + Feedback:**
- Morpheus gibt Feedback weiter an Claude Code
- Neuer Commit auf gleichem Branch
- Railway updated Preview automatisch
- User wird erneut benachrichtigt

---

## 🔧 Technische Komponenten

### Bestehend (schon vorhanden)
| Komponente | Tool | Status |
|-----------|------|--------|
| Issue Watcher | `gh-issues` Skill | ✅ vorhanden |
| Agent Coding | Claude Code CLI | ✅ vorhanden |
| Notification | Morpheus (WhatsApp/TG) | ✅ vorhanden |
| Git Operations | `gh` CLI | ✅ vorhanden |

### Neu zu bauen
| Komponente | Was | Aufwand |
|-----------|-----|---------|
| Railway-Integration | Railway CLI + API für Preview-URLs | Klein |
| Worktree Manager | Script: create/list/cleanup Worktrees | Klein |
| Approval Parser | Morpheus: ✅/❌ aus WhatsApp-Reply parsen | Klein |
| Seed-System | Demo-Daten pro App | Mittel (app-spezifisch) |
| Orchestrator-Skill | Alles zusammenbindend | Mittel |

---

## 💰 Kosten-Abschätzung

### Railway
- **Hobby Plan:** $5/Monat, 3 Ephemeral Envs gleichzeitig
- **Pro Plan:** $20/Monat, unbegrenzte Preview Environments
- **Empfehlung:** Pro-Plan wenn mehr als 3 parallele Issues

### Claude Code
- API-Kosten pro Issue: ~$0.50 - $2.00 (je nach Komplexität)
- Bei 20 Issues/Monat: ~$10-40

### Gesamt: ~$30-60/Monat für aktive Nutzung

---

## 🚨 Bekannte Einschränkungen

### Data Privacy
- Preview-Environments dürfen **keine echten Produktionsdaten** enthalten
- Lösung: Immer Seed-Daten / Fixtures
- Bei sensibler App: separates anonymisiertes Staging-DB-Snapshot

### Komplexität
- Manche Features sind zu komplex für vollautomatische Implementierung
- Lösung: Morpheus prüft Komplexität, leitet ggf. weiter an Entwickler

### Parallele Issues
- Git-Konflikte möglich wenn 2 Issues denselben Code ändern
- Lösung: Worktree-basiert + Railway Limits beachten

### Security
- Agent darf keine Produktionsdatenbank berühren
- Lösung: Strict Environment Separation, nur `.env.preview` für Agents

---

## 🗺️ Rollout-Plan

### Phase 1 — Proof of Concept (1-2 Wochen)
- [ ] Orchestrator-Skript bauen (Issue → Worktree → Claude Code → Push)
- [ ] Railway GitHub-Integration aktivieren für Test-Repo
- [ ] Seed-Skript für ein konkretes Projekt
- [ ] Manueller Test: 1 Issue durchlaufen lassen

### Phase 2 — Benachrichtigungen (1 Woche)
- [ ] Morpheus gibt Preview-URL nach Deploy aus
- [ ] Approval via WhatsApp-Reply implementieren
- [ ] Auto-Merge bei ✅

### Phase 3 — Automation (2 Wochen)
- [ ] Cron-basierter Issue-Watcher live
- [ ] Worktree-Cleanup nach Merge
- [ ] Error-Handling + Fallback auf manuelle Review

### Phase 4 — Multi-Repo (ongoing)
- [ ] Config-File pro Projekt (`harness.yaml`)
- [ ] Paperclip-Integration für Approval-Board
- [ ] Metriken: Issues/Monat, Ø Zeit bis Deploy, Approval-Rate

---

## 📁 Repo-Struktur (geplant)

```
agent-harness-platform/
├── CONCEPT.md              ← dieses Dokument
├── README.md
├── orchestrator/
│   ├── watch-issues.sh     ← Issue Watcher
│   ├── create-worktree.sh  ← Worktree Management
│   ├── deploy-preview.sh   ← Railway Deploy
│   └── notify-user.sh      ← Morpheus Notification
├── config/
│   ├── harness.example.yaml ← Pro-Repo Konfiguration
│   └── railway.toml.example
├── scripts/
│   ├── seed-demo.js        ← Demo-Daten Template
│   └── cleanup-worktrees.sh
└── docs/
    ├── setup.md
    ├── user-guide.md
    └── troubleshooting.md
```

---

## 🔮 Langfristige Vision

Wenn das System reift, könnte es werden:

1. **SaaS-Produkt** — "Connect your GitHub → Users submit Issues → AI builds it"
2. **CDBrain-Feature** — Enterprise-Kunden können ihr eigenes Wissenssystem durch Issues erweitern
3. **Open Source** — Community-getriebene Plattform für AI-assisted development

---

*"The users are the product team. The AI is the engineering team."*

---

*Zuletzt aktualisiert: 04.04.2026*
