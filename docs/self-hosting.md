# Self-Hosting Guide

## Local Setup

### Prerequisites

- Python 3.9+
- Node.js 20+
- npm

### 1. Clone and install

```bash
git clone https://github.com/your-org/agent-harness-platform.git
cd agent-harness-platform

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key!!!!
DATABASE_URL=sqlite:///./harness.db
```

### 3. Run

```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`.

---

## Docker Deployment

```bash
docker compose up --build -d
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### Custom environment

```bash
SECRET_KEY=prod-secret ENCRYPTION_KEY=prod-32-byte-key!!!!!!!!!!!!! docker compose up -d
```

---

## Railway Deployment

### 1. Create Railway project

Link your GitHub repo to [Railway](https://railway.app). Railway auto-detects the `docker-compose.yml`.

### 2. Set environment variables

In the Railway dashboard, add:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (random 32+ chars) |
| `ENCRYPTION_KEY` | API key encryption (exactly 32 bytes) |
| `DATABASE_URL` | SQLite path or Postgres URL |

### 3. Deploy

Push to `main` — Railway builds and deploys automatically.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes (prod) | `dev-secret-key-change-in-production` | JWT signing secret |
| `ENCRYPTION_KEY` | Yes (prod) | `dev-encryption-key-32bytes!!!!!` | AES key for encrypting stored API keys |
| `DATABASE_URL` | No | `sqlite:///./harness.db` | Database connection URL |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT token expiry in minutes |

---

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
  extra_dirs: []
  always_load: []

agent:
  max_iterations: 20
  model_tier: balanced  # free | balanced | premium

notifications:
  on_complete: true
  on_error: true
```

See the root `harness.yaml` in this repo for a working example.
