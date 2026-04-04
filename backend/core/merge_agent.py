"""Merge agent — handles approval, conflict detection, and PR merging."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class MergeResult:
    success: bool
    message: str
    conflicts: list[str] | None = None


def conflict_check(worktree_path: str, base_branch: str = "main") -> list[str]:
    """Check for merge conflicts using git merge-tree."""
    try:
        # Get merge base
        merge_base = subprocess.run(
            ["git", "merge-base", "HEAD", base_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if merge_base.returncode != 0:
            return [f"Could not find merge base: {merge_base.stderr.strip()}"]

        base_sha = merge_base.stdout.strip()

        # Get HEAD sha
        head_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Get base branch sha
        main_sha = subprocess.run(
            ["git", "rev-parse", base_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        result = subprocess.run(
            ["git", "merge-tree", base_sha, head_sha.stdout.strip(), main_sha.stdout.strip()],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=15,
        )

        conflicts = []
        if "<<<<<<" in result.stdout or "changed in both" in result.stdout:
            for line in result.stdout.splitlines():
                if line.startswith("changed in both"):
                    conflicts.append(line)
                elif "<<<<<<" in line:
                    conflicts.append(line.strip())
        return conflicts

    except subprocess.SubprocessError as e:
        return [f"Error during conflict check: {e}"]


def merge_pr(
    repo_full_name: str,
    pr_number: int,
    strategy: str = "squash",
    github_token: Optional[str] = None,
) -> MergeResult:
    """Merge a PR using gh CLI."""
    env = None
    if github_token:
        import os
        env = {**os.environ, "GH_TOKEN": github_token}

    cmd = ["gh", "pr", "merge", str(pr_number), f"--{strategy}", "--delete-branch", "--repo", repo_full_name]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode == 0:
            return MergeResult(success=True, message=f"PR #{pr_number} merged successfully")
        return MergeResult(success=False, message=result.stderr.strip() or "Merge failed")
    except subprocess.SubprocessError as e:
        return MergeResult(success=False, message=str(e))


def cleanup_worktree(worktree_path: str, branch_name: Optional[str] = None) -> dict:
    """Remove a git worktree and optionally delete the local branch."""
    results = {"worktree_removed": False, "branch_deleted": False}

    try:
        result = subprocess.run(
            ["git", "worktree", "remove", worktree_path, "--force"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        results["worktree_removed"] = result.returncode == 0
    except subprocess.SubprocessError:
        pass

    if branch_name:
        try:
            result = subprocess.run(
                ["git", "branch", "-D", branch_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            results["branch_deleted"] = result.returncode == 0
        except subprocess.SubprocessError:
            pass

    return results


def approve_and_merge(
    repo_full_name: str,
    pr_number: int,
    worktree_path: str,
    branch_name: str,
    base_branch: str = "main",
    github_token: Optional[str] = None,
) -> MergeResult:
    """Full approval flow: conflict check → merge → cleanup."""
    # Step 1: Fetch latest
    try:
        subprocess.run(
            ["git", "fetch", "origin", base_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.SubprocessError:
        pass

    # Step 2: Conflict check
    conflicts = conflict_check(worktree_path, f"origin/{base_branch}")
    if conflicts:
        return MergeResult(
            success=False,
            message=f"Conflicts detected in {len(conflicts)} location(s)",
            conflicts=conflicts,
        )

    # Step 3: Merge PR
    merge_result = merge_pr(repo_full_name, pr_number, github_token=github_token)
    if not merge_result.success:
        return merge_result

    # Step 4: Cleanup
    cleanup_worktree(worktree_path, branch_name)

    return MergeResult(success=True, message=f"PR #{pr_number} merged and cleaned up")


def store_feedback(issue_id: int, feedback: str) -> dict:
    """Store review feedback for re-triggering agent. Returns status dict."""
    # In a full implementation this would persist to DB and re-trigger the agent.
    # For now return the feedback as stored.
    return {"issue_id": issue_id, "feedback": feedback, "stored": True}
