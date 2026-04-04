from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.models.database import Domain, DomainStatus, User, UserRole, Workspace

router = APIRouter(prefix="/api/domains", tags=["domains"])


class DomainCreate(BaseModel):
    service_id: str
    domain_name: str


class DomainResponse(BaseModel):
    id: int
    workspace_id: int
    service_id: str
    domain_name: str
    status: str
    created_at: str


def _require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )


def _get_workspace(user: User, session: Session) -> Workspace:
    workspace = session.exec(
        select(Workspace).where(Workspace.owner_id == user.id)
    ).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No workspace found"
        )
    return workspace


@router.get("", response_model=List[DomainResponse])
def list_domains(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    workspace = _get_workspace(user, session)
    domains = session.exec(
        select(Domain).where(Domain.workspace_id == workspace.id)
    ).all()
    return [
        DomainResponse(
            id=d.id,
            workspace_id=d.workspace_id,
            service_id=d.service_id,
            domain_name=d.domain_name,
            status=d.status.value,
            created_at=d.created_at.isoformat(),
        )
        for d in domains
    ]


@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
def add_domain(
    body: DomainCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    workspace = _get_workspace(user, session)
    domain = Domain(
        workspace_id=workspace.id,
        service_id=body.service_id,
        domain_name=body.domain_name,
        status=DomainStatus.pending,
    )
    session.add(domain)
    session.commit()
    session.refresh(domain)
    return DomainResponse(
        id=domain.id,
        workspace_id=domain.workspace_id,
        service_id=domain.service_id,
        domain_name=domain.domain_name,
        status=domain.status.value,
        created_at=domain.created_at.isoformat(),
    )


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_domain(
    domain_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_admin(user)
    workspace = _get_workspace(user, session)
    domain = session.exec(
        select(Domain).where(Domain.id == domain_id, Domain.workspace_id == workspace.id)
    ).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
        )
    session.delete(domain)
    session.commit()
