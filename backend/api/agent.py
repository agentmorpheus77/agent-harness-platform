"""Agent API endpoints - start agent jobs, stream output via SSE."""

from __future__ import annotations

import asyncio
import os
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

    # Get github token for cloning
    from backend.core.encryption import decrypt_value
    from backend.models.database import Setting as _Setting
    gh_setting = session.exec(
        select(_Setting)
        .where(_Setting.user_id == user.id)
        .where(_Setting.key == "github_token")
    ).first()
    github_token = decrypt_value(gh_setting.value_encrypted) if gh_setting else ""

    issue_dict = {
        "title": issue.title or f"Issue #{issue.id}",
        "body": issue.body or "",
        "number": issue.github_issue_number or issue.id,
    }

    # Store job metadata
    _jobs[job_id] = {
        "id": job_id,
        "issue_id": issue.id,
        "model": model,
        "model_tier": body.model_tier,
        "status": "starting",
        "events": [],
        "worktree_path": "",
        "repo_local_path": repo_local_path,
        "api_key": api_key,
        "issue_dict": issue_dict,
        "github_full_name": repo.github_full_name,
        "github_token": github_token,
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
        # Step 1: Clone repo if not already present
        job["status"] = "cloning"
        github_full_name = job.get("github_full_name", "")
        github_token = job.get("github_token", "")
        
        if not os.path.exists(os.path.join(repo_local_path, ".git")):
            os.makedirs(repo_local_path, exist_ok=True)
            job["events"].append({
                "type": "thought",
                "content": f"Cloning {github_full_name}...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            clone_url = f"https://x-access-token:{github_token}@github.com/{github_full_name}.git"
            clone_proc = await asyncio.create_subprocess_exec(
                "git", "clone", clone_url, repo_local_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, clone_err = await clone_proc.communicate()
            if clone_proc.returncode != 0:
                # Try without token as fallback
                clone_url_public = f"https://github.com/{github_full_name}.git"
                clone_proc2 = await asyncio.create_subprocess_exec(
                    "git", "clone", clone_url_public, repo_local_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, clone_err2 = await clone_proc2.communicate()
                if clone_proc2.returncode != 0:
                    raise RuntimeError(f"Clone failed: {clone_err2.decode()}")
            job["events"].append({
                "type": "tool_result",
                "content": f"✅ Cloned {github_full_name}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # Step 2: Create worktree
        job["status"] = "creating_worktree"
        issue_number = issue_dict.get("number", 0)
        try:
            wt = await create_worktree(repo_local_path, issue_number)
            job["worktree_path"] = wt.worktree_path
        except Exception as e:
            job["events"].append({
                "type": "thought",
                "content": f"Using repo directly (worktree: {e})",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Fall back to using repo path directly
            job["worktree_path"] = repo_local_path

        worktree_path = job["worktree_path"]
        job["status"] = "running"

        # Build model fallback list: primary model + tier fallbacks
        model_tier = job.get("model_tier", "free")
        from backend.core.llm_client import MODEL_TIERS as _MODEL_TIERS
        tier_models = [m["id"] for m in _MODEL_TIERS.get(model_tier, [])]
        # Ensure primary model is first, then add tier alternatives
        models_to_try = [model] + [m for m in tier_models if m != model]
        # Cross-tier fallback: always add llama as last resort (reliable + free)
        fallback_safety = "meta-llama/llama-3.3-70b-instruct:free"
        if fallback_safety not in models_to_try:
            models_to_try.append(fallback_safety)

        last_error = None
        for attempt_model in models_to_try:
            if attempt_model != model:
                job["events"].append({
                    "type": "thought",
                    "content": f"⚡ Retrying with fallback model: {attempt_model}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            job["model"] = attempt_model
            got_error = False
            rate_limited = False

            async for event in run_agent_loop(api_key, attempt_model, issue_dict, worktree_path):
                job["events"].append(event)
                if event["type"] == "done":
                    job["status"] = "completed"
                    break
                elif event["type"] == "error":
                    content = event.get("content", "")
                    if "429" in content or "rate" in content.lower() or "rate-limited" in content.lower():
                        rate_limited = True
                    got_error = True
                    last_error = content
                    job["status"] = "error"
                    break

            if not got_error or not rate_limited:
                # Either success, or a non-rate-limit error — don't retry
                break
            # Rate limited — try next model

        if job["status"] == "error" and last_error:
            # already recorded
            pass

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
