import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.core.encryption import decrypt_value
from backend.core.merge_agent import approve_and_merge
from backend.models.database import Issue, IssueStatus, Repo, Setting, User, Workspace

router = APIRouter(prefix="/api/issues", tags=["issues"])


class IssueResponse(BaseModel):
    id: int
    repo_id: int
    submitted_by: int
    github_issue_number: Optional[int]
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    preview_url: Optional[str] = None
    status: str
    model_tier: str
    title: str
    body: Optional[str] = None


class IssueSubmitRequest(BaseModel):
    repo_id: int
    title: str
    body: str
    labels: Optional[List[str]] = None
    assignee: Optional[str] = None


class IssueSubmitResponse(BaseModel):
    id: int
    github_issue_number: int
    github_url: str
    title: str


@router.get("", response_model=List[IssueResponse])
def list_issues(
    repo_id: Optional[int] = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Get user's workspace IDs
    workspaces = session.exec(select(Workspace).where(Workspace.owner_id == user.id)).all()
    workspace_ids = [w.id for w in workspaces]
    if not workspace_ids:
        return []

    # Get repos in user's workspaces
    repos_query = select(Repo).where(Repo.workspace_id.in_(workspace_ids))
    if repo_id is not None:
        repos_query = repos_query.where(Repo.id == repo_id)
    repos = session.exec(repos_query).all()
    repo_ids = [r.id for r in repos]
    if not repo_ids:
        return []

    issues = session.exec(select(Issue).where(Issue.repo_id.in_(repo_ids))).all()
    return [
        IssueResponse(
            id=i.id,
            repo_id=i.repo_id,
            submitted_by=i.submitted_by,
            github_issue_number=i.github_issue_number,
            pr_number=i.pr_number,
            branch_name=i.branch_name,
            preview_url=i.preview_url,
            status=i.status.value,
            model_tier=i.model_tier,
            title=i.title,
            body=i.body,
        )
        for i in issues
    ]


@router.post("/submit", response_model=IssueSubmitResponse)
async def submit_issue(
    req: IssueSubmitRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Verify repo belongs to user
    workspaces = session.exec(select(Workspace).where(Workspace.owner_id == user.id)).all()
    workspace_ids = [w.id for w in workspaces]
    repo = session.exec(
        select(Repo).where(Repo.id == req.repo_id, Repo.workspace_id.in_(workspace_ids))
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get GitHub token
    setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "github_token")
    ).first()
    if not setting:
        raise HTTPException(status_code=400, detail="GitHub token not configured")

    github_token = decrypt_value(setting.value_encrypted)
    owner_repo = repo.github_full_name  # e.g. "owner/repo"

    # Create issue on GitHub
    gh_payload: dict = {"title": req.title, "body": req.body}
    if req.labels:
        gh_payload["labels"] = req.labels
    if req.assignee:
        gh_payload["assignee"] = req.assignee

    async with httpx.AsyncClient(timeout=30.0) as client:
        gh_resp = await client.post(
            f"https://api.github.com/repos/{owner_repo}/issues",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=gh_payload,
        )

    if gh_resp.status_code not in (201, 200):
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error {gh_resp.status_code}: {gh_resp.text[:200]}",
        )

    gh_data = gh_resp.json()
    gh_number = gh_data["number"]
    gh_url = gh_data["html_url"]

    # Save to local DB
    issue = Issue(
        repo_id=req.repo_id,
        submitted_by=user.id,
        github_issue_number=gh_number,
        status=IssueStatus.open,
        title=req.title,
        body=req.body,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)

    return IssueSubmitResponse(
        id=issue.id,
        github_issue_number=gh_number,
        github_url=gh_url,
        title=req.title,
    )


class ApproveResponse(BaseModel):
    success: bool
    message: str
    conflicts: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    feedback: str


class FeedbackResponse(BaseModel):
    issue_id: int
    feedback: str
    job_id: str
    stored: bool


@router.post("/{issue_id}/approve", response_model=ApproveResponse)
def approve_issue(
    issue_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Approve an issue and trigger merge agent."""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Verify user owns the workspace
    repo = session.get(Repo, issue.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    workspace = session.get(Workspace, repo.workspace_id)
    if not workspace or workspace.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Determine PR number: prefer stored pr_number, fall back to github_issue_number
    pr_number = issue.pr_number or issue.github_issue_number
    if not pr_number:
        raise HTTPException(status_code=400, detail="Issue has no associated PR number. Run the agent first.")

    # Get GitHub token
    setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "github_token")
    ).first()
    github_token = decrypt_value(setting.value_encrypted) if setting else None

    # Resolve worktree path: prefer stored path, fall back to convention
    repo_base = f"/tmp/agent-harness/repos/{repo.github_full_name.replace('/', '_')}"
    if issue.worktree_path and os.path.exists(issue.worktree_path):
        worktree_path = issue.worktree_path
    else:
        # Convention fallback: try multiple possible paths
        candidates = [
            f"/tmp/agent-harness/repos/worktrees/issue-{issue.github_issue_number}",
            f"/tmp/agent-harness/repos/worktrees/issue-{pr_number}",
            repo_base,
        ]
        worktree_path = next((p for p in candidates if p and os.path.exists(p)), repo_base)

    branch_name = issue.branch_name or f"feature/issue-{issue.github_issue_number}"

    result = approve_and_merge(
        repo_full_name=repo.github_full_name,
        pr_number=pr_number,
        worktree_path=worktree_path,
        branch_name=branch_name,
        github_token=github_token,
    )

    if result.success:
        issue.status = IssueStatus.merged
        session.add(issue)
        session.commit()

    return ApproveResponse(
        success=result.success,
        message=result.message,
        conflicts=result.conflicts,
    )


@router.post("/{issue_id}/request-changes", response_model=FeedbackResponse)
async def request_changes(
    issue_id: int,
    req: FeedbackRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Store feedback and re-trigger agent to iterate on the same branch."""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Verify user owns the workspace
    repo = session.get(Repo, issue.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    workspace = session.get(Workspace, repo.workspace_id)
    if not workspace or workspace.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get API keys
    or_setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "openrouter_api_key")
    ).first()
    if not or_setting:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured")
    api_key = decrypt_value(or_setting.value_encrypted)

    gh_setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "github_token")
    ).first()
    github_token = decrypt_value(gh_setting.value_encrypted) if gh_setting else ""

    railway_setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "railway_token")
    ).first()
    railway_token = decrypt_value(railway_setting.value_encrypted) if railway_setting else ""

    # Resolve worktree path
    repo_base = f"/tmp/agent-harness/repos/{repo.github_full_name.replace('/', '_')}"
    if issue.worktree_path and os.path.exists(issue.worktree_path):
        worktree_path = issue.worktree_path
    else:
        worktree_path = repo_base

    # Update status back to building
    issue.status = IssueStatus.building
    session.add(issue)
    session.commit()

    # Determine model
    from backend.core.llm_client import get_default_model
    model = get_default_model(issue.model_tier or "free")

    # Build issue dict with feedback context
    issue_dict = {
        "title": issue.title or f"Issue #{issue.id}",
        "body": (
            f"{issue.body or ''}\n\n"
            f"---\n## User Feedback (iteration request)\n"
            f"The previous implementation was reviewed. The user wants changes:\n\n"
            f"{req.feedback}\n\n"
            f"Please make the requested changes on this existing branch. "
            f"The codebase already has the previous implementation — modify it accordingly."
        ),
        "number": issue.github_issue_number or issue.id,
    }

    # Create a new job and re-trigger agent
    from backend.api.agent import _jobs, _run_agent_job
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "id": job_id,
        "issue_id": issue.id,
        "model": model,
        "model_tier": issue.model_tier or "free",
        "status": "starting",
        "events": [],
        "worktree_path": worktree_path,
        "repo_local_path": repo_base,
        "api_key": api_key,
        "issue_dict": issue_dict,
        "github_full_name": repo.github_full_name,
        "github_token": github_token,
        "railway_token": railway_token,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    asyncio.create_task(_run_agent_job(job_id, api_key, model, issue_dict, repo_base))

    return FeedbackResponse(
        issue_id=issue_id,
        feedback=req.feedback,
        job_id=job_id,
        stored=True,
    )

@router.post("/{issue_id}/reset", response_model=IssueResponse)
def reset_issue_status(
    issue_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> IssueResponse:
    """Reset a stuck issue back to open status."""
    issue = session.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    repo = session.get(Repo, issue.repo_id)
    if not repo or repo.workspace_id not in [
        w.id for w in session.exec(select(Workspace).where(Workspace.owner_id == user.id)).all()
    ]:
        raise HTTPException(status_code=403, detail="Not authorized")

    issue.status = IssueStatus.open
    session.add(issue)
    session.commit()
    session.refresh(issue)

    return IssueResponse(
        id=issue.id,
        repo_id=issue.repo_id,
        github_issue_number=issue.github_issue_number,
        status=issue.status.value,
        model_tier=issue.model_tier or "free",
        title=issue.title or "",
        created_at=issue.created_at.isoformat() if issue.created_at else "",
    )
