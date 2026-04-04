"""Tests for merge_agent.py — mock gh CLI + git."""

from unittest.mock import patch, MagicMock

import pytest

from backend.core.merge_agent import (
    MergeResult,
    approve_and_merge,
    cleanup_worktree,
    conflict_check,
    merge_pr,
    store_feedback,
)


def make_result(returncode=0, stdout="", stderr=""):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = stderr
    return r


class TestConflictCheck:
    @patch("backend.core.merge_agent.subprocess.run")
    def test_no_conflicts(self, mock_run):
        mock_run.side_effect = [
            make_result(stdout="abc123"),  # merge-base
            make_result(stdout="def456"),  # rev-parse HEAD
            make_result(stdout="ghi789"),  # rev-parse main
            make_result(stdout="clean output"),  # merge-tree
        ]
        conflicts = conflict_check("/some/worktree", "main")
        assert conflicts == []

    @patch("backend.core.merge_agent.subprocess.run")
    def test_with_conflicts(self, mock_run):
        mock_run.side_effect = [
            make_result(stdout="abc123"),
            make_result(stdout="def456"),
            make_result(stdout="ghi789"),
            make_result(stdout="changed in both\n  base   100644 abc src/app.py\n<<<<<<< ours"),
        ]
        conflicts = conflict_check("/some/worktree", "main")
        assert len(conflicts) > 0

    @patch("backend.core.merge_agent.subprocess.run")
    def test_merge_base_failure(self, mock_run):
        mock_run.return_value = make_result(returncode=1, stderr="no merge base")
        conflicts = conflict_check("/some/worktree", "main")
        assert len(conflicts) == 1
        assert "merge base" in conflicts[0].lower()


class TestMergePr:
    @patch("backend.core.merge_agent.subprocess.run")
    def test_merge_success(self, mock_run):
        mock_run.return_value = make_result(stdout="Merged PR #42")
        result = merge_pr("owner/repo", 42)
        assert result.success is True
        assert "#42" in result.message

        # Verify gh CLI was called correctly
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "gh" in cmd
        assert "pr" in cmd
        assert "merge" in cmd
        assert "42" in cmd
        assert "--squash" in cmd

    @patch("backend.core.merge_agent.subprocess.run")
    def test_merge_failure(self, mock_run):
        mock_run.return_value = make_result(returncode=1, stderr="Merge conflict")
        result = merge_pr("owner/repo", 42)
        assert result.success is False
        assert "conflict" in result.message.lower()

    @patch("backend.core.merge_agent.subprocess.run")
    def test_merge_with_token(self, mock_run):
        mock_run.return_value = make_result(stdout="Merged")
        merge_pr("owner/repo", 10, github_token="gh_token_123")
        call_args = mock_run.call_args
        env = call_args[1].get("env") or call_args.kwargs.get("env")
        assert env is not None
        assert env["GH_TOKEN"] == "gh_token_123"


class TestCleanupWorktree:
    @patch("backend.core.merge_agent.subprocess.run")
    def test_cleanup_success(self, mock_run):
        mock_run.return_value = make_result()
        result = cleanup_worktree("/path/to/worktree", "feature/issue-42")
        assert result["worktree_removed"] is True
        assert result["branch_deleted"] is True
        assert mock_run.call_count == 2

    @patch("backend.core.merge_agent.subprocess.run")
    def test_cleanup_without_branch(self, mock_run):
        mock_run.return_value = make_result()
        result = cleanup_worktree("/path/to/worktree")
        assert result["worktree_removed"] is True
        assert result["branch_deleted"] is False
        assert mock_run.call_count == 1

    @patch("backend.core.merge_agent.subprocess.run")
    def test_cleanup_failure(self, mock_run):
        mock_run.return_value = make_result(returncode=1, stderr="error")
        result = cleanup_worktree("/path/to/worktree", "branch")
        assert result["worktree_removed"] is False
        assert result["branch_deleted"] is False


class TestApproveAndMerge:
    @patch("backend.core.merge_agent.cleanup_worktree")
    @patch("backend.core.merge_agent.merge_pr")
    @patch("backend.core.merge_agent.conflict_check")
    @patch("backend.core.merge_agent.subprocess.run")
    def test_full_success(self, mock_fetch, mock_conflict, mock_merge, mock_cleanup):
        mock_fetch.return_value = make_result()
        mock_conflict.return_value = []
        mock_merge.return_value = MergeResult(success=True, message="PR #5 merged")
        mock_cleanup.return_value = {"worktree_removed": True, "branch_deleted": True}

        result = approve_and_merge("owner/repo", 5, "/worktree", "feature/issue-5")
        assert result.success is True
        assert "merged" in result.message.lower()

    @patch("backend.core.merge_agent.conflict_check")
    @patch("backend.core.merge_agent.subprocess.run")
    def test_with_conflicts(self, mock_fetch, mock_conflict):
        mock_fetch.return_value = make_result()
        mock_conflict.return_value = ["changed in both: src/app.py"]

        result = approve_and_merge("owner/repo", 5, "/worktree", "feature/issue-5")
        assert result.success is False
        assert result.conflicts is not None
        assert len(result.conflicts) == 1

    @patch("backend.core.merge_agent.merge_pr")
    @patch("backend.core.merge_agent.conflict_check")
    @patch("backend.core.merge_agent.subprocess.run")
    def test_merge_failure(self, mock_fetch, mock_conflict, mock_merge):
        mock_fetch.return_value = make_result()
        mock_conflict.return_value = []
        mock_merge.return_value = MergeResult(success=False, message="PR not found")

        result = approve_and_merge("owner/repo", 99, "/worktree", "feature/issue-99")
        assert result.success is False


class TestStoreFeedback:
    def test_stores_feedback(self):
        result = store_feedback(42, "Please add error handling")
        assert result["issue_id"] == 42
        assert result["feedback"] == "Please add error handling"
        assert result["stored"] is True
