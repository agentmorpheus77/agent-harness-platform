"""Preview server manager — spins up a dev server for a worktree and runs smoke tests."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class PreviewServer:
    port: int
    url: str
    pid: int
    worktree_path: str
    process: Optional[asyncio.subprocess.Process] = None


def _find_free_port(start: int = 4000, end: int = 4100) -> int:
    """Find a free TCP port in range."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range")


async def start_preview(worktree_path: str, timeout: int = 60) -> PreviewServer:
    """Start a Vite dev server for the frontend in this worktree.

    Installs deps if needed, starts on a free port, waits until healthy.
    Returns PreviewServer with url + pid.
    """
    frontend_path = os.path.join(worktree_path, "frontend")
    if not os.path.isdir(frontend_path):
        raise RuntimeError(f"No frontend/ directory in worktree: {worktree_path}")

    # Install deps if node_modules missing
    nm_path = os.path.join(frontend_path, "node_modules")
    if not os.path.isdir(nm_path):
        proc = await asyncio.create_subprocess_shell(
            "npm install --prefer-offline",
            cwd=frontend_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)

    port = _find_free_port()
    url = f"http://localhost:{port}"

    # Start vite dev server
    env = {**os.environ, "PORT": str(port), "VITE_PORT": str(port)}
    process = await asyncio.create_subprocess_shell(
        f"npm run dev -- --port {port} --host 127.0.0.1",
        cwd=frontend_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    # Wait until server responds
    deadline = time.time() + timeout
    import httpx
    while time.time() < deadline:
        await asyncio.sleep(2)
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code < 500:
                    return PreviewServer(
                        port=port,
                        url=url,
                        pid=process.pid,
                        worktree_path=worktree_path,
                        process=process,
                    )
        except Exception:
            pass
        if process.returncode is not None:
            out, err = await process.communicate()
            raise RuntimeError(f"Preview server died: {err.decode()[:300]}")

    process.kill()
    raise RuntimeError(f"Preview server did not start within {timeout}s on port {port}")


async def stop_preview(server: PreviewServer) -> None:
    """Kill the preview server process tree."""
    if server.process:
        try:
            server.process.kill()
            await asyncio.wait_for(server.process.wait(), timeout=5)
        except Exception:
            pass
    # Also kill by port as fallback
    try:
        proc = await asyncio.create_subprocess_shell(
            f"lsof -ti:{server.port} | xargs kill -9 2>/dev/null || true",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
    except Exception:
        pass


async def run_smoke_tests(url: str, checks: list[str] | None = None) -> dict:
    """Run basic smoke tests against the preview URL.

    checks: list of strings that must appear in the HTML response.
    Returns {"passed": bool, "results": [...]}
    """
    import httpx

    results = []

    # 1. Homepage loads
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url)
            results.append({
                "test": "homepage_loads",
                "passed": resp.status_code < 400,
                "detail": f"HTTP {resp.status_code}",
            })
            body = resp.text

            # 2. No JS bundle error markers
            error_markers = ["Uncaught SyntaxError", "Cannot find module", "Module not found"]
            has_error = any(m in body for m in error_markers)
            results.append({
                "test": "no_bundle_errors",
                "passed": not has_error,
                "detail": "Clean" if not has_error else "Bundle errors detected",
            })

            # 3. Custom string checks
            for check in (checks or []):
                found = check.lower() in body.lower()
                results.append({
                    "test": f"contains_{check[:20]}",
                    "passed": found,
                    "detail": f"{'Found' if found else 'NOT FOUND'}: {check!r}",
                })

    except Exception as e:
        results.append({
            "test": "homepage_loads",
            "passed": False,
            "detail": str(e),
        })

    passed = all(r["passed"] for r in results)
    return {"passed": passed, "url": url, "results": results}
