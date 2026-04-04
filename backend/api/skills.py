"""Skills API — list, get, update, and detect relevant skills."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.core.skills_manager import (
    SkillInfo,
    get_relevant_skills,
    load_skill_content,
    scan_skills,
    update_all_skills,
)
from backend.models.database import Repo, User, Workspace

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillResponse(BaseModel):
    name: str
    description: str
    version: str
    status: str
    path: str
    keywords: list[str]


class SkillContentResponse(BaseModel):
    name: str
    content: str


class SkillUpdateResponse(BaseModel):
    results: list[dict]


class RelevantRequest(BaseModel):
    text: str


class RelevantResponse(BaseModel):
    skills: list[str]


@router.get("", response_model=list[SkillResponse])
def list_skills(user: User = Depends(get_current_user)):
    """List all available skills with status."""
    skills = scan_skills()
    return [
        SkillResponse(
            name=s.name,
            description=s.description,
            version=s.version,
            status=s.status,
            path=s.path,
            keywords=s.keywords,
        )
        for s in skills
    ]


@router.get("/{name}", response_model=SkillContentResponse)
def get_skill(name: str, user: User = Depends(get_current_user)):
    """Get the full SKILL.md content for a skill."""
    content = load_skill_content(name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return SkillContentResponse(name=name, content=content)


@router.post("/update", response_model=SkillUpdateResponse)
def update_skills(user: User = Depends(get_current_user)):
    """Git pull latest on all skill repos."""
    results = update_all_skills()
    return SkillUpdateResponse(results=results)


@router.post("/relevant", response_model=RelevantResponse)
def find_relevant_skills(
    req: RelevantRequest,
    user: User = Depends(get_current_user),
):
    """Given issue text, return relevant skill names."""
    skills = get_relevant_skills(None, req.text)
    return RelevantResponse(skills=skills)


@router.get("/for-repo/{repo_id}", response_model=RelevantResponse)
def skills_for_repo(
    repo_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Auto-detect relevant skills for a repository."""
    workspaces = session.exec(select(Workspace).where(Workspace.owner_id == user.id)).all()
    workspace_ids = [w.id for w in workspaces]
    repo = session.exec(
        select(Repo).where(Repo.id == repo_id, Repo.workspace_id.in_(workspace_ids))
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # We don't have a local clone path readily available, so pass repo name as context
    skills = get_relevant_skills(None, repo.github_full_name)
    return RelevantResponse(skills=skills)
