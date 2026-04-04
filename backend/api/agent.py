"""Agent API endpoints - start agent jobs, stream output via SSE."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.agent import run_agent_loop
from backend.core.complexity import estimate_complexity
from backend.core.deps import get_current_user, get_session
from backend.core.encryption import decrypt_value
from backend.core.llm_client import MODEL_TIERS, get_default_model
from backend.core.worktree import WorktreeInfo, cleanup_worktree, create_worktree
from backend.models.database import Issue, IssueStatus, Repo, Setting, User

router = APIRouter(prefix="/api/agent", tags=["agent"])

# In-memory job store (for MVP; upgrade to Redis/DB for production)
_jobs: dict[str, dict[str, Any]] = {}


class StartAgentRequest(BaseModel):
    issue_id: int
    model_tier: str = "free"
    model_id: Optional[str] = None  # Override specific model


class StartAgentResponse(BaseModel):
    job_id: str
    model: str
    worktree_path: str


class ComplexityRequest(BaseModel):
    title: str
    body: str = ""


class ComplexityResponse(BaseModel):
    tier: str
    reason: str
    estimated_files: int
    score: float
    categories: list[str]


def _get_openrouter_key(user: User, session: Session) -> str:
    """Get OpenRouter API key from user settings."""
    setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "openrouter_api_key")
    ).first()
    if not setting:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured. Go to Settings.")
    try:
        return decrypt_value(setting.value_encrypted)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to decrypt OpenRouter API key")


@router.post("/start", response_model=StartAgentResponse)
async def start_agent(
    body: StartAgentRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Start an agent job for an issue."""
    # Get the issue
    issue = session.get(Issue, body.issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Get the repo
    repo = session.get(Repo, issue.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    # Get API key
    api_key = _get_openrouter_key(user, session)

    # Determine model
    model = body.model_id or get_default_model(body.model_tier)

    # Create worktree (we need a local clone path - for now use a convention)
    # In production this would clone from GitHub first
    repo_local_path = f"/tmp/agent-harness/repos/{repo.github_full_name.replace('/', '_')}"

    job_id = str(uuid.uuid4())

    # Update issue status
    issue.status = IssueStatus.building
    issue.model_tier = body.model_tier
    session.add(issue)
    session.commit()

    issue_dict = {
        "title": issue.title,
        "body": "",
        "number": issue.github_issue_number or issue.id,
    }

    # Store job metadata
    _jobs[job_id] = {
        "id": job_id,
        "issue_id": issue.id,
        "model": model,
        "status": "starting",
        "events": [],
        "worktree_path": "",
        "repo_local_path": repo_local_path,
        "api_key": api_key,
        "issue_dict": issue_dict,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Start agent in background
    asyncio.create_task(_run_agent_job(job_id, api_key, model, issue_dict, repo_local_path))

    return StartAgentResponse(
        job_id=job_id,
        model=model,
        worktree_path=repo_local_path,
    )


async def _run_agent_job(
    job_id: str,
    api_key: str,
    model: str,
    issue_dict: dict[str, Any],
    repo_local_path: str,
):
    """Background task that runs the agent loop and stores events."""
    job = _jobs.get(job_id)
    if not job:
        return

    try:
        # Create worktree
        job["status"] = "creating_worktree"
        issue_number = issue_dict.get("number", 0)
        try:
            wt = await create_worktree(repo_local_path, issue_number)
            job["worktree_path"] = wt.worktree_path
        except Exception as e:
            event = {
                "type": "error",
                "content": f"Failed to create worktree: {e}. Running in repo directly.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            job["events"].append(event)
            # Fall back to using repo path directly
            job["worktree_path"] = repo_local_path

        worktree_path = job["worktree_path"]
        job["status"] = "running"

        async for event in run_agent_loop(api_key, model, issue_dict, worktree_path):
            job["events"].append(event)
            if event["type"] == "done":
                job["status"] = "completed"
            elif event["type"] == "error":
                job["status"] = "error"

    except Exception as e:
        job["status"] = "error"
        job["events"].append({
            "type": "error",
            "content": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


@router.get("/{job_id}/stream")
async def stream_agent_output(job_id: str):
    """SSE stream of agent output events."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_index = 0
        while True:
            job = _jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Job disappeared'})}\n\n"
                return

            events = job["events"]
            while last_index < len(events):
                event = events[last_index]
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] in ("done", "error") and last_index == len(events) - 1:
                    return
                last_index += 1

            if job["status"] in ("completed", "error"):
                return

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/status")
async def get_job_status(job_id: str):
    """Get current status of an agent job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "model": job["model"],
        "event_count": len(job["events"]),
        "created_at": job["created_at"],
    }


@router.post("/estimate-complexity", response_model=ComplexityResponse)
async def estimate_issue_complexity(body: ComplexityRequest):
    """Estimate issue complexity for model tier recommendation."""
    result = estimate_complexity(body.title, body.body)
    return ComplexityResponse(
        tier=result.tier,
        reason=result.reason,
        estimated_files=result.estimated_files,
        score=result.score,
        categories=result.categories,
    )


@router.get("/models")
async def list_models():
    """List available models by tier."""
    return MODEL_TIERS
