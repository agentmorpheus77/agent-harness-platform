from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.models.database import Issue, Repo, User, Workspace

router = APIRouter(prefix="/api/issues", tags=["issues"])


class IssueResponse(BaseModel):
    id: int
    repo_id: int
    submitted_by: int
    github_issue_number: Optional[int]
    status: str
    model_tier: str
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
        )
        for i in issues
    ]
