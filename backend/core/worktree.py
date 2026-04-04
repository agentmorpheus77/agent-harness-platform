"""Git worktree manager for isolated agent workspaces."""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass


@dataclass
class WorktreeInfo:
    worktree_path: str
    branch_name: str
    issue_number: int


async def _run(cmd: str, cwd: str | None = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def create_worktree(repo_path: str, issue_number: int) -> WorktreeInfo:
    """Create a git worktree + branch for an issue.

    Creates worktree at <repo_path>/../worktrees/issue-<number>
    with branch feature/issue-<number>.
    """
    repo_path = os.path.abspath(repo_path)
    parent = os.path.dirname(repo_path)
    worktrees_dir = os.path.join(parent, "worktrees")
    os.makedirs(worktrees_dir, exist_ok=True)

    branch_name = f"feature/issue-{issue_number}"
    worktree_path = os.path.join(worktrees_dir, f"issue-{issue_number}")

    # Clean up if exists from previous run
    if os.path.exists(worktree_path):
        await cleanup_worktree(worktree_path, repo_path)

    # Create worktree with new branch from current HEAD
    returncode, stdout, stderr = await _run(
        f"git worktree add {worktree_path} -b {branch_name}",
        cwd=repo_path,
    )
    if returncode != 0:
        # Branch might already exist, try without -b
        returncode, stdout, stderr = await _run(
            f"git worktree add {worktree_path} {branch_name}",
            cwd=repo_path,
        )
        if returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {stderr}")

    return WorktreeInfo(
        worktree_path=worktree_path,
        branch_name=branch_name,
        issue_number=issue_number,
    )


async def cleanup_worktree(worktree_path: str, repo_path: str | None = None) -> None:
    """Remove a worktree and prune."""
    if os.path.exists(worktree_path):
        # Try git worktree remove first
        if repo_path:
            await _run(f"git worktree remove {worktree_path} --force", cwd=repo_path)
        # Fallback: manual removal
        if os.path.exists(worktree_path):
            shutil.rmtree(worktree_path, ignore_errors=True)

    # Prune stale worktree entries
    if repo_path:
        await _run("git worktree prune", cwd=repo_path)


async def get_worktree_status(worktree_path: str) -> dict[str, str]:
    """Get git status of a worktree."""
    returncode, stdout, stderr = await _run("git status --porcelain", cwd=worktree_path)
    if returncode != 0:
        return {"error": stderr}

    returncode2, branch_out, _ = await _run("git branch --show-current", cwd=worktree_path)
    branch = branch_out.strip() if returncode2 == 0 else "unknown"

    return {
        "branch": branch,
        "status": stdout.strip() if stdout.strip() else "clean",
        "path": worktree_path,
    }
