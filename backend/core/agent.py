"""Agentic coding loop - executes tool calls in a worktree via OpenRouter."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from backend.core.llm_client import stream_chat_completion

MAX_ITERATIONS = 20
COMMAND_TIMEOUT = 30

# Tool definitions for OpenRouter (OpenAI-compatible function calling format)
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the given path (relative to worktree root).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file at the given path (relative to worktree root). Creates directories as needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path to write"},
                    "content": {"type": "string", "description": "File content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the worktree directory. Returns stdout and stderr. Timeout: 30s.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at the given path (relative to worktree root).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path (default: '.')"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and create a git commit with the given message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Push the current branch to the remote origin.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "done",
            "description": "Signal that the task is complete. Call this when you have finished implementing the requested changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Brief summary of what was done"},
                },
                "required": ["summary"],
            },
        },
    },
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_path_safe(worktree_path: str, relative_path: str) -> bool:
    """Ensure path stays within the worktree."""
    full = os.path.normpath(os.path.join(worktree_path, relative_path))
    return full.startswith(os.path.normpath(worktree_path))


async def _execute_tool(name: str, arguments: dict[str, Any], worktree_path: str) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "read_file":
        path = arguments.get("path", "")
        if not _is_path_safe(worktree_path, path):
            return "Error: Path escapes worktree boundary"
        full_path = os.path.join(worktree_path, path)
        try:
            with open(full_path) as f:
                content = f.read()
            # Truncate very large files
            if len(content) > 50000:
                return content[:50000] + "\n\n... [truncated, file too large]"
            return content
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error reading file: {e}"

    elif name == "write_file":
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        if not _is_path_safe(worktree_path, path):
            return "Error: Path escapes worktree boundary"
        full_path = os.path.join(worktree_path, path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            return f"OK: Wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    elif name == "run_command":
        cmd = arguments.get("cmd", "")
        # Security: block commands that could escape
        blocked = ["rm -rf /", "sudo", "curl | sh", "wget | sh"]
        if any(b in cmd for b in blocked):
            return "Error: Command blocked for security reasons"
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=worktree_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=COMMAND_TIMEOUT)
            result = ""
            if stdout:
                result += stdout.decode(errors="replace")
            if stderr:
                result += ("\n--- stderr ---\n" + stderr.decode(errors="replace"))
            if not result.strip():
                result = f"(exit code: {proc.returncode})"
            # Truncate
            if len(result) > 20000:
                result = result[:20000] + "\n... [truncated]"
            return result
        except asyncio.TimeoutError:
            return f"Error: Command timed out after {COMMAND_TIMEOUT}s"
        except Exception as e:
            return f"Error running command: {e}"

    elif name == "list_files":
        path = arguments.get("path", ".")
        if not _is_path_safe(worktree_path, path):
            return "Error: Path escapes worktree boundary"
        full_path = os.path.join(worktree_path, path)
        try:
            entries = sorted(os.listdir(full_path))
            result = []
            for entry in entries:
                entry_path = os.path.join(full_path, entry)
                prefix = "d " if os.path.isdir(entry_path) else "f "
                result.append(prefix + entry)
            return "\n".join(result) if result else "(empty directory)"
        except FileNotFoundError:
            return f"Error: Directory not found: {path}"
        except Exception as e:
            return f"Error listing files: {e}"

    elif name == "git_commit":
        message = arguments.get("message", "agent commit")
        try:
            proc = await asyncio.create_subprocess_shell(
                f'git add -A && git commit -m "{message}"',
                cwd=worktree_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
        except Exception as e:
            return f"Error committing: {e}"

    elif name == "git_push":
        try:
            proc = await asyncio.create_subprocess_shell(
                "git push -u origin HEAD",
                cwd=worktree_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
        except Exception as e:
            return f"Error pushing: {e}"

    elif name == "done":
        return arguments.get("summary", "Task completed")

    return f"Error: Unknown tool '{name}'"


async def run_agent_loop(
    api_key: str,
    model: str,
    issue: dict[str, Any],
    worktree_path: str,
    system_prompt: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run the agentic coding loop. Yields SSE-style event dicts.

    Events:
    - {"type": "thought", "content": "...", "timestamp": "..."}
    - {"type": "tool_call", "content": "tool_name(args)", "timestamp": "..."}
    - {"type": "tool_result", "content": "...", "timestamp": "..."}
    - {"type": "error", "content": "...", "timestamp": "..."}
    - {"type": "done", "content": "...", "timestamp": "..."}
    """
    if not system_prompt:
        system_prompt = (
            "You are a coding agent. You implement features and fix bugs in a git repository. "
            "You have tools to read/write files, run commands, and manage git. "
            "Work step by step: understand the codebase, make changes, test them, commit and push. "
            "Call the done() tool when you are finished."
        )

    issue_context = (
        f"## Issue to implement\n"
        f"Title: {issue.get('title', 'No title')}\n"
        f"Body: {issue.get('body', 'No description')}\n"
        f"Number: #{issue.get('number', 'N/A')}\n"
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": issue_context},
    ]

    for iteration in range(MAX_ITERATIONS):
        yield {
            "type": "thought",
            "content": f"Iteration {iteration + 1}/{MAX_ITERATIONS}",
            "timestamp": _timestamp(),
        }

        # Collect the full response (content + tool calls) from streaming
        full_content = ""
        tool_calls_building: dict[int, dict[str, str]] = {}  # index -> {id, name, arguments}

        async for chunk in stream_chat_completion(api_key, model, messages, AGENT_TOOLS):
            if chunk["type"] == "content_delta":
                full_content += chunk["content"]

            elif chunk["type"] == "tool_call_delta":
                idx = chunk["index"]
                if idx not in tool_calls_building:
                    tool_calls_building[idx] = {"id": "", "name": "", "arguments": ""}
                if chunk.get("id"):
                    tool_calls_building[idx]["id"] = chunk["id"]
                if chunk.get("name"):
                    tool_calls_building[idx]["name"] = chunk["name"]
                tool_calls_building[idx]["arguments"] += chunk.get("arguments_delta", "")

            elif chunk["type"] == "error":
                yield {"type": "error", "content": chunk["content"], "timestamp": _timestamp()}
                return

            elif chunk["type"] == "done":
                break

        # Emit thought if there was text content
        if full_content.strip():
            yield {"type": "thought", "content": full_content.strip(), "timestamp": _timestamp()}

        # If no tool calls, we're done (model stopped without calling tools)
        if not tool_calls_building:
            yield {"type": "done", "content": full_content.strip() or "Agent finished without tool calls", "timestamp": _timestamp()}
            return

        # Build assistant message with tool calls
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if full_content:
            assistant_msg["content"] = full_content
        tc_list = []
        for idx in sorted(tool_calls_building.keys()):
            tc = tool_calls_building[idx]
            tc_list.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            })
        assistant_msg["tool_calls"] = tc_list
        messages.append(assistant_msg)

        # Execute each tool call
        for tc in tc_list:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
            except json.JSONDecodeError:
                fn_args = {}

            yield {
                "type": "tool_call",
                "content": f"{fn_name}({json.dumps(fn_args, ensure_ascii=False)[:200]})",
                "timestamp": _timestamp(),
            }

            # Check for done tool
            if fn_name == "done":
                summary = fn_args.get("summary", "Task completed")
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": summary})
                yield {"type": "done", "content": summary, "timestamp": _timestamp()}
                return

            result = await _execute_tool(fn_name, fn_args, worktree_path)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

            yield {
                "type": "tool_result",
                "content": result[:500] + ("..." if len(result) > 500 else ""),
                "timestamp": _timestamp(),
            }

    yield {"type": "done", "content": f"Agent reached max iterations ({MAX_ITERATIONS})", "timestamp": _timestamp()}
