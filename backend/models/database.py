from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class IssueStatus(str, Enum):
    open = "open"
    building = "building"
    review = "review"
    merged = "merged"
    closed = "closed"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.user)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    workspaces: list["Workspace"] = Relationship(back_populates="owner")


class Workspace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    owner: Optional[User] = Relationship(back_populates="workspaces")
    repos: list["Repo"] = Relationship(back_populates="workspace")


class Repo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspace.id")
    github_full_name: str  # e.g. "owner/repo"
    github_token_encrypted: Optional[str] = None
    deploy_provider: str = Field(default="railway")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    workspace: Optional[Workspace] = Relationship(back_populates="repos")
    issues: list["Issue"] = Relationship(back_populates="repo")


class Issue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo_id: int = Field(foreign_key="repo.id")
    submitted_by: int = Field(foreign_key="user.id")
    github_issue_number: Optional[int] = None
    status: IssueStatus = Field(default=IssueStatus.open)
    model_tier: str = Field(default="balanced")
    title: str = Field(default="")
    body: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    repo: Optional[Repo] = Relationship(back_populates="issues")


class Setting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    key: str  # e.g. "openrouter_api_key"
    value_encrypted: str


def run_migrations():
    """Run any pending schema migrations."""
    from sqlalchemy import text, inspect
    from backend.core.deps import engine as _engine
    with _engine.connect() as conn:
        inspector = inspect(_engine)
        issue_cols = [c['name'] for c in inspector.get_columns('issue')] if inspector.has_table('issue') else []
        if 'body' not in issue_cols:
            conn.execute(text("ALTER TABLE issue ADD COLUMN body TEXT"))
            conn.commit()
        if 'title' not in issue_cols:
            conn.execute(text("ALTER TABLE issue ADD COLUMN title TEXT"))
            conn.commit()
