from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from sqlmodel import Session, select

from backend.api.agent import router as agent_router
from backend.api.auth import router as auth_router
from backend.api.issues import router as issues_router
from backend.api.repos import router as repos_router
from backend.api.settings import router as settings_router
from backend.core.deps import engine
from backend.core.encryption import encrypt_value
from backend.models.database import Setting


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
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
