from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.core.encryption import encrypt_value
from backend.models.database import Repo, User, Workspace

router = APIRouter(prefix="/api/repos", tags=["repos"])


class RepoCreate(BaseModel):
    github_full_name: str
    github_token: Optional[str] = None
    deploy_provider: str = "railway"


class RepoResponse(BaseModel):
    id: int
    workspace_id: int
    github_full_name: str
    deploy_provider: str


@router.get("", response_model=List[RepoResponse])
def list_repos(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    workspaces = session.exec(select(Workspace).where(Workspace.owner_id == user.id)).all()
    workspace_ids = [w.id for w in workspaces]
    if not workspace_ids:
        return []
    repos = session.exec(select(Repo).where(Repo.workspace_id.in_(workspace_ids))).all()
    return [
        RepoResponse(
            id=r.id,
            workspace_id=r.workspace_id,
            github_full_name=r.github_full_name,
            deploy_provider=r.deploy_provider,
        )
        for r in repos
    ]


@router.post("", response_model=RepoResponse, status_code=201)
def create_repo(
    body: RepoCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    workspace = session.exec(select(Workspace).where(Workspace.owner_id == user.id)).first()
    if not workspace:
        raise HTTPException(status_code=400, detail="No workspace found")

    token_enc = encrypt_value(body.github_token) if body.github_token else None
    repo = Repo(
        workspace_id=workspace.id,
        github_full_name=body.github_full_name,
        github_token_encrypted=token_enc,
        deploy_provider=body.deploy_provider,
    )
    session.add(repo)
    session.commit()
    session.refresh(repo)
    return RepoResponse(
        id=repo.id,
        workspace_id=repo.workspace_id,
        github_full_name=repo.github_full_name,
        deploy_provider=repo.deploy_provider,
    )
