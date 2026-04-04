# Agent Harness Platform

Submit a GitHub Issue. Get a working feature. No developer needed.

## Tech Stack

- **Backend:** FastAPI + SQLModel + SQLite + JWT
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui
- **i18n:** i18next (DE/EN)

## Setup

### Prerequisites

- Python 3.9+
- Node.js 20+
- npm

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

### Environment

```bash
cp .env.example .env
# Edit .env with your secrets
```

## Development

### Run both servers

```bash
# Terminal 1: Backend (from project root)
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Frontend runs at `http://localhost:5173` with API proxy to backend.

### Run tests

```bash
# Backend tests
source .venv/bin/activate
python -m pytest backend/tests/ -v

# Frontend build check
cd frontend && npm run build
```

### Docker

```bash
docker compose up --build
```

Backend: `http://localhost:8000`
Frontend: `http://localhost:5173`

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

## Project Structure

```
agent-harness-platform/
├── backend/
│   ├── api/          # Route handlers
│   ├── core/         # Config, security, deps
│   ├── models/       # SQLModel database models
│   ├── tests/        # pytest tests
│   └── main.py       # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── components/  # React components + shadcn/ui
│   │   ├── pages/       # Page components
│   │   ├── i18n/        # DE/EN translations
│   │   └── lib/         # API client, utils, theme
│   └── package.json
├── docker-compose.yml
├── Makefile
└── CONCEPT.md
```
