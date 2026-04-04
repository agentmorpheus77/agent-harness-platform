from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from backend.api.auth import router as auth_router
from backend.api.issues import router as issues_router
from backend.api.repos import router as repos_router
from backend.api.settings import router as settings_router
from backend.core.deps import engine


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


@app.get("/health")
def health():
    return {"status": "ok"}
