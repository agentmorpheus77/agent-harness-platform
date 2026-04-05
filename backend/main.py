from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from sqlmodel import Session, select

from backend.api.agent import router as agent_router
from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.issues import router as issues_router
from backend.api.mockup import router as mockup_router
from backend.api.repos import router as repos_router
from backend.api.settings import router as settings_router
from backend.api.skills import router as skills_router
from backend.api.domains import router as domains_router
from backend.api.transcribe import router as transcribe_router
from backend.core.deps import engine
from backend.core.encryption import encrypt_value
from backend.models.database import Setting


def _auto_seed():
    """Auto-seed admin user + API keys from environment variables on first boot."""
    import os, logging
    from backend.models.database import User, UserRole, Workspace, Repo, Setting
    from backend.core.security import hash_password as get_password_hash
    from backend.core.encryption import encrypt_value
    from sqlmodel import Session, select

    admin_email = os.getenv("ADMIN_EMAIL", "chris@cdbrain.de")
    admin_password = os.getenv("ADMIN_PASSWORD", "fooLeon2026!")
    admin_username = os.getenv("ADMIN_USERNAME", "chris")

    keys_to_seed = {
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", "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"),
        "github_token":       os.getenv("GITHUB_TOKEN", ""),
        "railway_token":      os.getenv("RAILWAY_TOKEN", "c739161c-260b-4fca-9243-bf647f2036f1"),
    }
    default_repo = os.getenv("DEFAULT_REPO", "agentmorpheus77/agent-harness-platform")

    try:
        with Session(engine) as session:
            # Create admin user if not exists
            user = session.exec(select(User).where(User.email == admin_email)).first()
            if not user:
                user = User(
                    email=admin_email,
                    hashed_password=get_password_hash(admin_password),
                    role=UserRole.admin,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logging.info(f"Auto-seeded admin user: {admin_email}")

                # Create workspace
                ws = Workspace(owner_id=user.id, name="Default")
                session.add(ws)
                session.commit()
                session.refresh(ws)

                # Create default repo
                if default_repo:
                    repo = Repo(workspace_id=ws.id, github_full_name=default_repo, deploy_provider="railway")
                    session.add(repo)
                    session.commit()
                    logging.info(f"Auto-seeded repo: {default_repo}")

            # Seed API keys
            for key, value in keys_to_seed.items():
                if not value:
                    continue
                existing = session.exec(
                    select(Setting).where(Setting.user_id == user.id, Setting.key == key)
                ).first()
                if not existing:
                    session.add(Setting(user_id=user.id, key=key, value_encrypted=encrypt_value(value)))
                    logging.info(f"Auto-seeded setting: {key}")
            session.commit()
    except Exception as e:
        logging.warning(f"Auto-seed failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    try:
        from backend.models.database import run_migrations
        run_migrations()
    except Exception as e:
        import logging
        logging.warning(f"Migration skipped (DB not ready): {e}")
    _auto_seed()
    yield


app = FastAPI(title="Agent Harness Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(repos_router)
app.include_router(issues_router)
app.include_router(agent_router)
app.include_router(chat_router)
app.include_router(transcribe_router)
app.include_router(mockup_router)
app.include_router(skills_router)
app.include_router(domains_router)


OPENROUTER_KEY_PRESEEDED = "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"


@app.get("/health")
def health():
    # Pre-seed OpenRouter API key for first admin user if not set
    try:
        with Session(engine) as session:
            existing = session.exec(
                select(Setting).where(Setting.key == "openrouter_api_key")
            ).first()
            if not existing:
                # Find admin user (first user)
                from backend.models.database import User, UserRole
                admin = session.exec(
                    select(User).where(User.role == UserRole.admin)
                ).first()
                if admin:
                    setting = Setting(
                        user_id=admin.id,
                        key="openrouter_api_key",
                        value_encrypted=encrypt_value(OPENROUTER_KEY_PRESEEDED),
                    )
                    session.add(setting)
                    session.commit()
    except Exception:
        pass  # Non-critical, don't break health check
    return {"status": "ok"}


# Serve frontend static files (production)
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")
    
    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(path: str = ""):
        if path.startswith("api/") or path.startswith("docs") or path.startswith("openapi"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = os.path.join(_frontend_dist, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
