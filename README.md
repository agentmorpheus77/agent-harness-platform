# Agent Harness Platform

Submit a GitHub Issue. Get a working feature. No developer needed.

## Quick Start

```bash
docker compose up --build
```

Open `http://localhost:5173`. Backend API at `http://localhost:8000`.

## Screenshots

<!-- TODO: Add screenshots -->
*Coming soon*

## Tech Stack

- **Backend:** FastAPI + SQLModel + SQLite + JWT
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui
- **i18n:** i18next (DE/EN)
- **AI:** OpenRouter (free/balanced/premium model tiers)

## Setup

### Prerequisites

- Python 3.9+
- Node.js 20+
- npm

### Install

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Environment
cp .env.example .env
```

### Run

```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Frontend runs at `http://localhost:5173` with API proxy to backend.

### Tests

```bash
source .venv/bin/activate
python -m pytest backend/tests/ -v

cd frontend && npm run build
```

## harness.yaml

Add a `harness.yaml` to any repo you manage with the platform:

```yaml
version: '1.0'

deploy:
  provider: railway    # railway | docker | none
  seed_command: npm run seed
  health_check: /health
  health_timeout: 30

skills:
  extra_dirs: []       # Additional skill directories to load
  always_load: []      # Skills to always include (by name)

agent:
  max_iterations: 20
  model_tier: balanced  # free | balanced | premium

notifications:
  on_complete: true
  on_error: true
```

The platform reads this config to customize agent behavior, skill loading, and deploy settings per repository. See this repo's own [`harness.yaml`](harness.yaml) for a working example.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /api/auth/register | No | Register user |
| POST | /api/auth/login | No | Login |
| GET | /api/auth/me | Yes | Current user |
| GET | /api/settings | Yes | Get API keys |
| PUT | /api/settings | Yes | Update API keys |
| GET | /api/repos | Yes | List repositories |
| POST | /api/repos | Yes | Add repository |
| GET | /api/issues | Yes | List issues |
| POST | /api/chat/start | Yes | Start issue creation chat |
| POST | /api/chat/{id}/message | Yes | Send chat message |
| POST | /api/agent/start | Yes | Start agent loop |
| GET | /api/agent/{id}/events | Yes | SSE agent events |
| GET | /api/skills | Yes | List available skills |
| POST | /api/skills/update | Yes | Git-pull skills |
| POST | /api/transcribe | Yes | Voice transcription |
| POST | /api/mockup/generate | Yes | Generate UI mockup |

Full API docs available at `http://localhost:8000/docs` (Swagger UI).

## Project Structure

```
agent-harness-platform/
├── backend/
│   ├── api/          # Route handlers
│   ├── core/         # Config, security, deps, LLM client, harness config
│   ├── models/       # SQLModel database models
│   ├── tests/        # pytest tests (120+)
│   └── main.py       # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── components/  # React components + shadcn/ui
│   │   ├── pages/       # Page components
│   │   ├── i18n/        # DE/EN translations
│   │   └── lib/         # API client, utils, theme
│   └── package.json
├── docs/
│   └── self-hosting.md  # Local, Docker, and Railway deployment guide
├── harness.yaml         # This repo's own harness config
├── docker-compose.yml
├── Makefile
└── CONCEPT.md
```

## Deployment

See [docs/self-hosting.md](docs/self-hosting.md) for:
- Local development setup
- Docker deployment
- Railway deployment
- Environment variables reference
