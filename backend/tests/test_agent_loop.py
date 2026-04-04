"""Tests for agent loop (mocked tool execution)."""

import os
import tempfile

import pytest

from backend.core.agent import _execute_tool, _is_path_safe


@pytest.fixture
def temp_worktree():
    """Create a temporary directory to simulate a worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test files
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Test Repo\n")
        os.makedirs(os.path.join(tmpdir, "src"))
        with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
            f.write("print('hello')\n")
        yield tmpdir


def test_path_safe():
    assert _is_path_safe("/work/tree", "src/main.py") is True
    assert _is_path_safe("/work/tree", "../escape") is False
    assert _is_path_safe("/work/tree", "../../etc/passwd") is False
    assert _is_path_safe("/work/tree", "sub/../valid.txt") is True


@pytest.mark.asyncio
async def test_read_file(temp_worktree):
    result = await _execute_tool("read_file", {"path": "README.md"}, temp_worktree)
    assert "# Test Repo" in result


@pytest.mark.asyncio
async def test_read_file_not_found(temp_worktree):
    result = await _execute_tool("read_file", {"path": "nonexistent.txt"}, temp_worktree)
    assert "Error" in result


@pytest.mark.asyncio
async def test_read_file_path_escape(temp_worktree):
    result = await _execute_tool("read_file", {"path": "../../etc/passwd"}, temp_worktree)
    assert "Error" in result


@pytest.mark.asyncio
async def test_write_file(temp_worktree):
    result = await _execute_tool("write_file", {"path": "new_file.txt", "content": "hello world"}, temp_worktree)
    assert "OK" in result
    with open(os.path.join(temp_worktree, "new_file.txt")) as f:
        assert f.read() == "hello world"


@pytest.mark.asyncio
async def test_write_file_creates_dirs(temp_worktree):
    result = await _execute_tool("write_file", {"path": "deep/nested/file.txt", "content": "test"}, temp_worktree)
    assert "OK" in result
    assert os.path.exists(os.path.join(temp_worktree, "deep", "nested", "file.txt"))


@pytest.mark.asyncio
async def test_list_files(temp_worktree):
    result = await _execute_tool("list_files", {"path": "."}, temp_worktree)
    assert "README.md" in result
    assert "src" in result


@pytest.mark.asyncio
async def test_run_command(temp_worktree):
    result = await _execute_tool("run_command", {"cmd": "echo hello"}, temp_worktree)
    assert "hello" in result


@pytest.mark.asyncio
async def test_run_command_blocked(temp_worktree):
    result = await _execute_tool("run_command", {"cmd": "sudo rm -rf /"}, temp_worktree)
    assert "blocked" in result.lower()


@pytest.mark.asyncio
async def test_git_commit(temp_worktree):
    # Init a git repo in worktree
    os.system(f"cd {temp_worktree} && git init && git add -A && git commit -m 'init'")
    # Make a change
    with open(os.path.join(temp_worktree, "new.txt"), "w") as f:
        f.write("test")
    result = await _execute_tool("git_commit", {"message": "add new file"}, temp_worktree)
    assert "add new file" in result or "1 file changed" in result


@pytest.mark.asyncio
async def test_done_tool(temp_worktree):
    result = await _execute_tool("done", {"summary": "All done!"}, temp_worktree)
    assert result == "All done!"


@pytest.mark.asyncio
async def test_unknown_tool(temp_worktree):
    result = await _execute_tool("nonexistent", {}, temp_worktree)
    assert "Unknown tool" in result
