"""Tests for skills_manager.py — mock filesystem + git."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.core.skills_manager import (
    SkillInfo,
    get_relevant_skills,
    load_skill_content,
    parse_skill_frontmatter,
    scan_skills,
    update_all_skills,
    update_skill,
)


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = """---
name: typescript-best-practices
description: Best practices for TypeScript
version: 1.2.0
keywords: typescript, ts, linting
---

# Skill content here
"""
        meta = parse_skill_frontmatter(content)
        assert meta["name"] == "typescript-best-practices"
        assert meta["description"] == "Best practices for TypeScript"
        assert meta["version"] == "1.2.0"
        assert meta["keywords"] == "typescript, ts, linting"

    def test_no_frontmatter(self):
        content = "# Just a markdown file\nNo frontmatter here."
        meta = parse_skill_frontmatter(content)
        assert meta == {}

    def test_empty_frontmatter(self):
        content = "---\n---\nBody"
        meta = parse_skill_frontmatter(content)
        assert meta == {}

    def test_invalid_yaml(self):
        content = "---\n: bad: yaml: [[\n---\nBody"
        meta = parse_skill_frontmatter(content)
        assert meta == {}


class TestScanSkills:
    def test_scan_existing_skills(self, tmp_path):
        """Scan a directory with two skill subdirectories."""
        skill1 = tmp_path / "typescript" / "SKILL.md"
        skill1.parent.mkdir()
        skill1.write_text(
            "---\nname: typescript\ndescription: TS best practices\nversion: 1.0.0\n---\n# Content"
        )

        skill2 = tmp_path / "testing-qa" / "SKILL.md"
        skill2.parent.mkdir()
        skill2.write_text(
            "---\nname: testing-qa\ndescription: QA guidelines\nversion: 2.1.0\n---\n# Test stuff"
        )

        # Non-skill dir (no SKILL.md)
        (tmp_path / "random-dir").mkdir()
        (tmp_path / "random-dir" / "README.md").write_text("not a skill")

        with patch("backend.core.skills_manager.check_git_status", return_value="available"):
            skills = scan_skills([str(tmp_path)])

        assert len(skills) == 2
        names = {s.name for s in skills}
        assert "typescript" in names
        assert "testing-qa" in names

    def test_scan_empty_dir(self, tmp_path):
        skills = scan_skills([str(tmp_path)])
        assert skills == []

    def test_scan_nonexistent_dir(self):
        skills = scan_skills(["/nonexistent/path/12345"])
        assert skills == []

    def test_deduplicates_by_name(self, tmp_path):
        """If same skill name appears in two dirs, first one wins."""
        dir1 = tmp_path / "dir1" / "my-skill"
        dir1.mkdir(parents=True)
        (dir1 / "SKILL.md").write_text("---\nname: my-skill\nversion: 1.0.0\n---\nV1")

        dir2 = tmp_path / "dir2" / "my-skill"
        dir2.mkdir(parents=True)
        (dir2 / "SKILL.md").write_text("---\nname: my-skill\nversion: 2.0.0\n---\nV2")

        with patch("backend.core.skills_manager.check_git_status", return_value="available"):
            skills = scan_skills([str(tmp_path / "dir1"), str(tmp_path / "dir2")])

        assert len(skills) == 1
        assert skills[0].version == "1.0.0"


class TestGetRelevantSkills:
    def test_matches_by_description(self, tmp_path):
        skill_dir = tmp_path / "ui-ux" / "SKILL.md"
        skill_dir.parent.mkdir()
        skill_dir.write_text(
            "---\nname: ui-ux\ndescription: UI and UX design guidelines for frontend\nversion: 1.0.0\n---\n# UI"
        )

        with patch("backend.core.skills_manager.check_git_status", return_value="available"):
            result = get_relevant_skills(None, "frontend UI design", dirs=[str(tmp_path)])

        assert "ui-ux" in result

    def test_matches_by_repo_path(self, tmp_path):
        skill_dir = tmp_path / "skills" / "typescript" / "SKILL.md"
        skill_dir.parent.mkdir(parents=True)
        skill_dir.write_text(
            "---\nname: typescript\ndescription: TypeScript best practices\nversion: 1.0.0\n---\n# TS"
        )

        # Create a fake repo with package.json
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "package.json").write_text("{}")

        with patch("backend.core.skills_manager.check_git_status", return_value="available"):
            result = get_relevant_skills(str(repo_dir), "", dirs=[str(tmp_path / "skills")])

        assert "typescript" in result

    def test_empty_skills(self, tmp_path):
        result = get_relevant_skills(None, "whatever", dirs=[str(tmp_path)])
        assert result == []


class TestLoadSkillContent:
    def test_load_existing(self, tmp_path):
        skill_file = tmp_path / "my-skill" / "SKILL.md"
        skill_file.parent.mkdir()
        skill_file.write_text("---\nname: my-skill\n---\n# Content here")

        content = load_skill_content("my-skill", dirs=[str(tmp_path)])
        assert content is not None
        assert "# Content here" in content

    def test_load_nonexistent(self, tmp_path):
        content = load_skill_content("nonexistent-skill", dirs=[str(tmp_path)])
        assert content is None


class TestUpdateSkill:
    @patch("backend.core.skills_manager.subprocess.run")
    def test_update_success(self, mock_run):
        mock_run.return_value = type("Result", (), {"returncode": 0, "stdout": "Already up to date.", "stderr": ""})()
        result = update_skill("/some/skill/dir")
        assert result["success"] is True

    @patch("backend.core.skills_manager.subprocess.run")
    def test_update_failure(self, mock_run):
        mock_run.return_value = type("Result", (), {"returncode": 1, "stdout": "", "stderr": "fatal: not a git repo"})()
        result = update_skill("/some/dir")
        assert result["success"] is False
        assert "fatal" in result["error"]


class TestUpdateAllSkills:
    def test_updates_git_dirs_only(self, tmp_path):
        """Only dirs with .git should be updated."""
        git_dir = tmp_path / "with-git"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()

        no_git_dir = tmp_path / "without-git"
        no_git_dir.mkdir()

        with patch("backend.core.skills_manager.update_skill") as mock_update:
            mock_update.return_value = {"success": True, "output": "ok", "error": None}
            results = update_all_skills([str(git_dir), str(no_git_dir)])

        assert len(results) == 1
        assert results[0]["dir"] == str(git_dir)
