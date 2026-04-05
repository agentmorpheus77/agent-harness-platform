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
from backend.core.preview import PreviewServer, run_smoke_tests, start_preview, stop_preview
from backend.core.railway_deploy import create_preview_env, delete_preview_env
from backend.core.llm_client import MODEL_TIERS, get_default_model
from backend.core.skills_manager import detect_repo_skills, load_inline_skill
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

    # Railway token (optional — enables Railway preview deploy)
    railway_setting = session.exec(
        select(_Setting)
        .where(_Setting.user_id == user.id)
        .where(_Setting.key == "railway_token")
    ).first()
    railway_token = decrypt_value(railway_setting.value_encrypted) if railway_setting else ""

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
        "railway_token": railway_token,
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
        wt_branch = f"feature/issue-{issue_number}"
        try:
            wt = await create_worktree(repo_local_path, issue_number)
            job["worktree_path"] = wt.worktree_path
            wt_branch = wt.branch_name if hasattr(wt, "branch_name") else wt_branch
        except Exception as e:
            job["events"].append({
                "type": "thought",
                "content": f"Using repo directly (worktree creation failed: {e})",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Fall back to using repo path directly
            job["worktree_path"] = repo_local_path

        # Persist worktree path + branch to DB so approve can find it
        from backend.core.deps import get_session as _get_session
        from backend.models.database import Issue as _Issue
        try:
            from sqlmodel import Session as _Session
            from backend.core.deps import engine as _engine
            with _Session(_engine) as _db:
                _issue_db = _db.get(_Issue, job["issue_id"])
                if _issue_db:
                    _issue_db.worktree_path = job["worktree_path"]
                    _issue_db.branch_name = wt_branch
                    _db.add(_issue_db)
                    _db.commit()
        except Exception as db_err:
            # Non-fatal — approve will fall back to convention-based path
            pass

        worktree_path = job["worktree_path"]
        job["status"] = "running"

        # ── Auto Skill Loading: detect repo skills and build enhanced system prompt ──
        skills_prompt_section = ""
        try:
            file_tree = os.listdir(worktree_path)
            detected_skills = detect_repo_skills(file_tree)
            if detected_skills:
                job["events"].append({
                    "type": "thought",
                    "content": f"📚 Loaded skills: {', '.join(detected_skills)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                skill_sections = []
                for skill_name in detected_skills:
                    content = load_inline_skill(skill_name)
                    if content:
                        skill_sections.append(content)
                if skill_sections:
                    skills_prompt_section = "\n\n## Relevant Skills & Best Practices\n" + "\n\n".join(skill_sections)
        except Exception:
            pass  # Non-fatal: agent works fine without skills

        # Build model fallback list: primary model + tier fallbacks
        model_tier = job.get("model_tier", "free")
        from backend.core.llm_client import MODEL_TIERS as _MODEL_TIERS
        tier_models = [m["id"] for m in _MODEL_TIERS.get(model_tier, [])]
        # Ensure primary model is first, then add tier alternatives
        models_to_try = [model] + [m for m in tier_models if m != model]
        # Cross-tier safety nets — ordered by reliability, always appended last
        for safety in [
            "meta-llama/llama-3.3-70b-instruct:free",
            "openai/gpt-oss-120b:free",
            "google/gemini-2.5-flash",   # paid fallback if free tier exhausted
        ]:
            if safety not in models_to_try:
                models_to_try.append(safety)

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

            async for event in run_agent_loop(api_key, attempt_model, issue_dict, worktree_path, skills_context=skills_prompt_section):
                job["events"].append(event)
                if event["type"] == "done":
                    job["status"] = "completed"
                    break
                elif event["type"] == "error":
                    content = event.get("content", "")
                    # Retry on: rate limits (429), spend limits (402), provider errors
                    if any(code in content for code in ["429", "402", "503", "529"]) or \
                       any(kw in content.lower() for kw in ["rate", "limit", "exceeded", "overloaded", "upstream"]):
                        rate_limited = True
                    got_error = True
                    last_error = content
                    job["status"] = "error"
                    break

            if not got_error or not rate_limited:
                # Either success, or a non-rate-limit error — don't retry
                break
            # Rate limited — try next model

        # After agent completes successfully: auto-create PR if commits exist
        if job["status"] == "completed":
            await _auto_create_pr(job)

    except Exception as e:
        job["status"] = "error"
        job["events"].append({
            "type": "error",
            "content": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


async def _auto_create_pr(job: dict[str, Any]) -> None:
    """After agent completes: check if there are commits and auto-create a GitHub PR."""
    worktree_path = job.get("worktree_path", "")
    github_full_name = job.get("github_full_name", "")
    github_token = job.get("github_token", "")
    issue_dict = job.get("issue_dict", {})
    issue_id = job.get("issue_id")

    if not worktree_path or not github_full_name:
        return

    try:
        # Check if there are any commits ahead of main
        check_proc = await asyncio.create_subprocess_shell(
            "git log --oneline origin/main..HEAD 2>/dev/null | wc -l",
            cwd=worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await check_proc.communicate()
        commits_ahead = int(stdout.decode().strip() or "0")

        if commits_ahead == 0:
            job["events"].append({
                "type": "thought",
                "content": "⚠️ No commits found — agent did not write any changes. No PR created.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            job["status"] = "review"  # Needs human review
            return

        # Push the branch
        job["events"].append({
            "type": "thought",
            "content": f"🔀 Pushing branch ({commits_ahead} commit(s))...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        push_env = {**os.environ}
        if github_token:
            push_env["GH_TOKEN"] = github_token
            # Set push URL with token
            await asyncio.create_subprocess_shell(
                f"git remote set-url origin https://x-access-token:{github_token}@github.com/{github_full_name}.git",
                cwd=worktree_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )

        push_proc = await asyncio.create_subprocess_shell(
            "git push -u origin HEAD",
            cwd=worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, push_err = await push_proc.communicate()
        if push_proc.returncode != 0:
            job["events"].append({
                "type": "error",
                "content": f"Push failed: {push_err.decode()[:200]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return

        # Create PR via gh CLI
        issue_title = issue_dict.get("title", "Agent fix")
        issue_number = issue_dict.get("number", "?")
        branch_proc = await asyncio.create_subprocess_shell(
            "git branch --show-current",
            cwd=worktree_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        branch_stdout, _ = await branch_proc.communicate()
        branch_name = branch_stdout.decode().strip()

        pr_body = (
            f"## Auto-generated by Agent Harness\n\n"
            f"Fixes #{issue_number}: {issue_title}\n\n"
            f"Agent explored the codebase and implemented the requested changes.\n"
            f"Please review and approve."
        )

        pr_proc = await asyncio.create_subprocess_shell(
            f'gh pr create --title "fix: {issue_title} (#{issue_number})" '
            f'--body "{pr_body}" --base main --head "{branch_name}" --repo "{github_full_name}"',
            cwd=worktree_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "GH_TOKEN": github_token} if github_token else None,
        )
        pr_stdout, pr_stderr = await pr_proc.communicate()
        pr_url = pr_stdout.decode().strip()

        if pr_proc.returncode == 0 and pr_url:
            # Extract PR number from URL
            pr_number = int(pr_url.rstrip("/").split("/")[-1]) if pr_url else None
            job["events"].append({
                "type": "thought",
                "content": f"✅ PR created: {pr_url}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            job["pr_url"] = pr_url

            # Save PR number + branch to DB
            if issue_id and pr_number:
                try:
                    from sqlmodel import Session as _Session
                    from backend.core.deps import engine as _engine
                    from backend.models.database import Issue as _Issue
                    with _Session(_engine) as _db:
                        _issue_db = _db.get(_Issue, issue_id)
                        if _issue_db:
                            _issue_db.pr_number = pr_number
                            _issue_db.branch_name = branch_name
                            _issue_db.status = IssueStatus.review
                            _db.add(_issue_db)
                            _db.commit()
                except Exception:
                    pass

            # Step 3: Start preview server and run smoke tests
            await _preview_and_test(job, worktree_path, github_full_name, github_token, pr_number)

        else:
            err = pr_stderr.decode()[:200]
            job["events"].append({
                "type": "error",
                "content": f"PR creation failed: {err}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    except Exception as e:
        job["events"].append({
            "type": "error",
            "content": f"Auto-PR error: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


async def _preview_and_test(
    job: dict[str, Any],
    worktree_path: str,
    github_full_name: str,
    github_token: str,
    pr_number: int,
) -> None:
    """Start a preview server for the worktree, run smoke tests, auto-merge on pass.

    If a Railway token is configured, deploy to Railway for a real public URL.
    Otherwise, fall back to a local Vite dev server.
    """
    issue_id = job.get("issue_id")
    railway_token = job.get("railway_token", "")
    railway_env_id: str | None = None

    # ── 1. Start preview (Railway or local) ─────────────────────────────────
    job["events"].append({
        "type": "thought",
        "content": "🚀 Starting preview server to test changes...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    server: PreviewServer | None = None
    preview_url: str | None = None

    try:
        if railway_token:
            # Railway deploy path
            branch_name = job.get("issue_dict", {}).get("number", "unknown")
            branch = job.get("branch_name") or f"feature/issue-{branch_name}"
            # Try to get actual branch from worktree
            try:
                bp = await asyncio.create_subprocess_shell(
                    "git branch --show-current",
                    cwd=worktree_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                bp_out, _ = await bp.communicate()
                if bp_out.decode().strip():
                    branch = bp_out.decode().strip()
            except Exception:
                pass

            job["events"].append({
                "type": "thought",
                "content": f"🚂 Deploying to Railway (branch: {branch})...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            result = await create_preview_env(
                repo_full_name=github_full_name,
                branch_name=branch,
                github_token=github_token,
                railway_token=railway_token,
            )

            if result.success and result.url:
                preview_url = result.url
                railway_env_id = result.environment_id
                job["preview_url"] = preview_url
                job["events"].append({
                    "type": "tool_result",
                    "content": f"🌐 Railway preview live: {preview_url}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                job["events"].append({
                    "type": "thought",
                    "content": f"⚠️ Railway deploy failed: {result.error} — falling back to local preview",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                # Fall through to local preview

        if not preview_url:
            # Local Vite dev server fallback
            server = await asyncio.wait_for(
                start_preview(worktree_path, timeout=90),
                timeout=100,
            )
            preview_url = server.url
            job["preview_url"] = preview_url
            job["events"].append({
                "type": "tool_result",
                "content": f"🌐 Preview live: {preview_url}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # Save preview_url to DB
        if issue_id and preview_url:
            try:
                from sqlmodel import Session as _Session
                from backend.core.deps import engine as _engine
                from backend.models.database import Issue as _Issue
                with _Session(_engine) as _db:
                    _issue_db = _db.get(_Issue, issue_id)
                    if _issue_db:
                        _issue_db.preview_url = preview_url
                        _db.add(_issue_db)
                        _db.commit()
            except Exception:
                pass

        # ── 2. Smoke tests ───────────────────────────────────────────────────
        job["events"].append({
            "type": "thought",
            "content": f"🧪 Running smoke tests on {preview_url}...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        test_result = await run_smoke_tests(preview_url)
        passed = test_result["passed"]

        for r in test_result["results"]:
            icon = "✅" if r["passed"] else "❌"
            job["events"].append({
                "type": "tool_result",
                "content": f"{icon} [{r['test']}] {r['detail']}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # ── 3. Auto-merge if all tests passed ────────────────────────────────
        if passed:
            job["events"].append({
                "type": "thought",
                "content": "✅ All tests passed — auto-merging PR...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            env_gh = {**os.environ, "GH_TOKEN": github_token} if github_token else None
            merge_proc = await asyncio.create_subprocess_shell(
                f"gh pr merge {pr_number} --squash --delete-branch --repo {github_full_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env_gh,
            )
            m_out, m_err = await asyncio.wait_for(merge_proc.communicate(), timeout=30)
            merge_ok = merge_proc.returncode == 0

            if merge_ok:
                job["events"].append({
                    "type": "done",
                    "content": f"🎉 Merged! PR #{pr_number} → main. Preview: {preview_url}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                job["status"] = "merged"

                # Update DB status
                if issue_id:
                    try:
                        from sqlmodel import Session as _Session
                        from backend.core.deps import engine as _engine
                        from backend.models.database import Issue as _Issue, IssueStatus as _IS
                        with _Session(_engine) as _db:
                            _issue_db = _db.get(_Issue, issue_id)
                            if _issue_db:
                                _issue_db.status = _IS.merged
                                _db.add(_issue_db)
                                _db.commit()
                    except Exception:
                        pass
            else:
                err_msg = m_err.decode()[:200]
                job["events"].append({
                    "type": "error",
                    "content": f"Auto-merge failed: {err_msg}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        else:
            job["events"].append({
                "type": "thought",
                "content": f"⚠️ Some tests failed — PR #{pr_number} left for manual review at {job.get('pr_url','')}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    except asyncio.TimeoutError:
        job["events"].append({
            "type": "thought",
            "content": "⚠️ Preview server timed out — skipping smoke tests. PR left open for manual review.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        job["events"].append({
            "type": "thought",
            "content": f"⚠️ Preview/test error: {e} — PR left open for manual review.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        # Always stop the preview server (local only)
        if server:
            await stop_preview(server)
            job["events"].append({
                "type": "thought",
                "content": "🛑 Preview server stopped.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        # Cleanup Railway preview env (non-blocking)
        if railway_env_id and railway_token:
            try:
                await delete_preview_env(railway_token, railway_env_id)
            except Exception:
                pass


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

            if job["status"] in ("completed", "error", "merged", "review"):
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
        "pr_url": job.get("pr_url"),
        "preview_url": job.get("preview_url"),
        "worktree_path": job.get("worktree_path"),
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
