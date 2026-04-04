from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.core.encryption import decrypt_value
from backend.models.database import Issue, IssueStatus, Repo, Setting, User, Workspace

router = APIRouter(prefix="/api/issues", tags=["issues"])


class IssueResponse(BaseModel):
    id: int
    repo_id: int
    submitted_by: int
    github_issue_number: Optional[int]
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
