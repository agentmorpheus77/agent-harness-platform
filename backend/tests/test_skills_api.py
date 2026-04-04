"""Tests for skills API endpoints."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.core.skills_manager import SkillInfo


class TestListSkills:
    @patch("backend.api.skills.scan_skills")
    def test_list_skills(self, mock_scan, client: TestClient, auth_headers: dict):
        mock_scan.return_value = [
            SkillInfo(
                name="typescript",
                description="TS best practices",
                version="1.0.0",
                status="available",
                path="/home/user/skills/typescript",
                keywords=["typescript", "ts"],
            ),
            SkillInfo(
                name="testing-qa",
                description="QA guidelines",
                version="2.1.0",
                status="outdated",
                path="/home/user/skills/testing-qa",
                keywords=["testing", "qa"],
            ),
        ]

        resp = client.get("/api/skills", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "typescript"
        assert data[1]["status"] == "outdated"

    def test_list_skills_unauthorized(self, client: TestClient):
        resp = client.get("/api/skills")
        assert resp.status_code == 401


class TestGetSkill:
    @patch("backend.api.skills.load_skill_content")
    def test_get_existing_skill(self, mock_load, client: TestClient, auth_headers: dict):
        mock_load.return_value = "---\nname: typescript\n---\n# TypeScript Best Practices"

        resp = client.get("/api/skills/typescript", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "typescript"
        assert "Best Practices" in data["content"]

    @patch("backend.api.skills.load_skill_content")
    def test_get_nonexistent_skill(self, mock_load, client: TestClient, auth_headers: dict):
        mock_load.return_value = None

        resp = client.get("/api/skills/nonexistent", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateSkills:
    @patch("backend.api.skills.update_all_skills")
    def test_update_skills(self, mock_update, client: TestClient, auth_headers: dict):
        mock_update.return_value = [
            {"dir": "/home/user/skills", "success": True, "output": "Already up to date.", "error": None}
        ]

        resp = client.post("/api/skills/update", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["success"] is True


class TestRelevantSkills:
    @patch("backend.api.skills.get_relevant_skills")
    def test_find_relevant(self, mock_relevant, client: TestClient, auth_headers: dict):
        mock_relevant.return_value = ["typescript", "testing-qa"]

        resp = client.post(
            "/api/skills/relevant",
            json={"text": "Add TypeScript tests for the API"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "typescript" in data["skills"]
        assert "testing-qa" in data["skills"]


class TestSkillsForRepo:
    @patch("backend.api.skills.get_relevant_skills")
    def test_skills_for_repo(self, mock_relevant, client: TestClient, auth_headers: dict, session):
        mock_relevant.return_value = ["ui-ux"]

        # Create a repo first
        from backend.models.database import Workspace, Repo, User
        from sqlmodel import select

        user = session.exec(select(User)).first()
        ws = Workspace(owner_id=user.id, name="test")
        session.add(ws)
        session.commit()
        session.refresh(ws)

        repo = Repo(workspace_id=ws.id, github_full_name="owner/frontend-app")
        session.add(repo)
        session.commit()
        session.refresh(repo)

        resp = client.get(f"/api/skills/for-repo/{repo.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ui-ux" in data["skills"]

    def test_skills_for_nonexistent_repo(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/skills/for-repo/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestIssueApproval:
    def test_approve_missing_issue(self, client: TestClient, auth_headers: dict):
        resp = client.post("/api/issues/99999/approve", headers=auth_headers)
        assert resp.status_code == 404

    def test_request_changes_missing_issue(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/issues/99999/request-changes",
            json={"feedback": "Fix the tests"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_approve_issue_no_github_number(self, client: TestClient, auth_headers: dict, session):
        from backend.models.database import Issue, Workspace, Repo, User
        from sqlmodel import select

        user = session.exec(select(User)).first()
        ws = Workspace(owner_id=user.id, name="test")
        session.add(ws)
        session.commit()
        session.refresh(ws)

        repo = Repo(workspace_id=ws.id, github_full_name="owner/repo")
        session.add(repo)
        session.commit()
        session.refresh(repo)

        issue = Issue(
            repo_id=repo.id,
            submitted_by=user.id,
            title="Test Issue",
            github_issue_number=None,
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)

        resp = client.post(f"/api/issues/{issue.id}/approve", headers=auth_headers)
        assert resp.status_code == 400
        assert "no GitHub PR" in resp.json()["detail"]

    def test_request_changes_success(self, client: TestClient, auth_headers: dict, session):
        from backend.models.database import Issue, IssueStatus, Workspace, Repo, User
        from sqlmodel import select

        user = session.exec(select(User)).first()
        ws = Workspace(owner_id=user.id, name="test-ws")
        session.add(ws)
        session.commit()
        session.refresh(ws)

        repo = Repo(workspace_id=ws.id, github_full_name="owner/repo2")
        session.add(repo)
        session.commit()
        session.refresh(repo)

        issue = Issue(
            repo_id=repo.id,
            submitted_by=user.id,
            title="Test Issue 2",
            status=IssueStatus.review,
            github_issue_number=10,
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)

        resp = client.post(
            f"/api/issues/{issue.id}/request-changes",
            json={"feedback": "Add more tests"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stored"] is True
        assert data["feedback"] == "Add more tests"

        # Check status was updated
        session.refresh(issue)
        assert issue.status == IssueStatus.building
