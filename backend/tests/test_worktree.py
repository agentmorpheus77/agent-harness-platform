"""Tests for worktree manager."""

import os
import tempfile

import pytest

from backend.core.worktree import cleanup_worktree, create_worktree, get_worktree_status


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repo for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "test-repo")
        os.makedirs(repo_path)
        os.system(f"cd {repo_path} && git init && git commit --allow-empty -m 'init'")
        yield repo_path


@pytest.mark.asyncio
async def test_create_worktree(temp_git_repo):
    wt = await create_worktree(temp_git_repo, 42)
    assert wt.branch_name == "feature/issue-42"
    assert wt.issue_number == 42
    assert os.path.exists(wt.worktree_path)
    # Cleanup
    await cleanup_worktree(wt.worktree_path, temp_git_repo)


@pytest.mark.asyncio
async def test_worktree_status(temp_git_repo):
    wt = await create_worktree(temp_git_repo, 99)
    status = await get_worktree_status(wt.worktree_path)
    assert status["branch"] == "feature/issue-99"
    assert status["status"] == "clean"
    # Cleanup
    await cleanup_worktree(wt.worktree_path, temp_git_repo)


@pytest.mark.asyncio
async def test_cleanup_worktree(temp_git_repo):
    wt = await create_worktree(temp_git_repo, 7)
    assert os.path.exists(wt.worktree_path)
    await cleanup_worktree(wt.worktree_path, temp_git_repo)
    assert not os.path.exists(wt.worktree_path)


@pytest.mark.asyncio
async def test_create_worktree_idempotent(temp_git_repo):
    """Creating a worktree for the same issue twice should succeed."""
    wt1 = await create_worktree(temp_git_repo, 5)
    wt2 = await create_worktree(temp_git_repo, 5)
    assert os.path.exists(wt2.worktree_path)
    await cleanup_worktree(wt2.worktree_path, temp_git_repo)
