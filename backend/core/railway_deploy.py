"""Railway Preview Deploy — creates ephemeral preview environments via Railway GraphQL API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"
DEPLOY_POLL_INTERVAL = 10  # seconds
DEPLOY_TIMEOUT = 300  # 5 minutes


@dataclass
class RailwayDeployResult:
    success: bool
    url: Optional[str] = None
    environment_id: Optional[str] = None
    deployment_id: Optional[str] = None
    error: Optional[str] = None


async def _graphql(token: str, query: str, variables: dict | None = None) -> dict:
    """Execute a Railway GraphQL query."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            RAILWAY_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"Railway API error: {data['errors']}")
        return data.get("data", {})


async def get_project_for_repo(token: str, repo_full_name: str) -> Optional[dict]:
    """Find the Railway project linked to a GitHub repo."""
    query = """
    query {
        me {
            projects {
                edges {
                    node {
                        id
                        name
                        services {
                            edges {
                                node {
                                    id
                                    name
                                    sourceRepo
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    data = await _graphql(token, query)
    projects = data.get("me", {}).get("projects", {}).get("edges", [])
    for edge in projects:
        project = edge.get("node", {})
        services = project.get("services", {}).get("edges", [])
        for svc_edge in services:
            svc = svc_edge.get("node", {})
            if svc.get("sourceRepo") and repo_full_name.lower() in svc["sourceRepo"].lower():
                return {"project_id": project["id"], "service_id": svc["id"]}
    return None


async def create_preview_env(
    repo_full_name: str,
    branch_name: str,
    github_token: str,
    railway_token: str,
) -> RailwayDeployResult:
    """Create a Railway preview environment for a branch and wait for deployment.

    Returns RailwayDeployResult with the public URL on success.
    """
    try:
        # Step 1: Find the project/service for this repo
        project_info = await get_project_for_repo(railway_token, repo_full_name)
        if not project_info:
            return RailwayDeployResult(
                success=False,
                error=f"No Railway project found linked to {repo_full_name}",
            )

        project_id = project_info["project_id"]
        service_id = project_info["service_id"]

        # Step 2: Create a temporary environment (PR environment) for the branch
        create_env_query = """
        mutation($input: EnvironmentCreateInput!) {
            environmentCreate(input: $input) {
                id
                name
            }
        }
        """
        env_name = f"preview-{branch_name.replace('/', '-')[:40]}"
        env_data = await _graphql(railway_token, create_env_query, {
            "input": {
                "projectId": project_id,
                "name": env_name,
                "ephemeral": True,
            },
        })
        environment = env_data.get("environmentCreate", {})
        environment_id = environment.get("id")
        if not environment_id:
            return RailwayDeployResult(success=False, error="Failed to create Railway environment")

        # Step 3: Trigger deployment on the new environment with the branch
        deploy_query = """
        mutation($input: DeploymentTriggerInput!) {
            deploymentTriggerCreate(input: $input) {
                id
            }
        }
        """
        deploy_data = await _graphql(railway_token, deploy_query, {
            "input": {
                "serviceId": service_id,
                "environmentId": environment_id,
                "branch": branch_name,
            },
        })
        deployment_id = deploy_data.get("deploymentTriggerCreate", {}).get("id")

        # Step 4: Poll for deployment status
        status_query = """
        query($environmentId: String!, $serviceId: String!) {
            deployments(
                input: {
                    environmentId: $environmentId
                    serviceId: $serviceId
                }
                first: 1
            ) {
                edges {
                    node {
                        id
                        status
                        staticUrl
                    }
                }
            }
        }
        """
        elapsed = 0
        while elapsed < DEPLOY_TIMEOUT:
            await asyncio.sleep(DEPLOY_POLL_INTERVAL)
            elapsed += DEPLOY_POLL_INTERVAL

            status_data = await _graphql(railway_token, status_query, {
                "environmentId": environment_id,
                "serviceId": service_id,
            })
            edges = status_data.get("deployments", {}).get("edges", [])
            if not edges:
                continue

            deployment = edges[0].get("node", {})
            status = deployment.get("status", "").upper()

            if status == "SUCCESS":
                static_url = deployment.get("staticUrl", "")
                url = f"https://{static_url}" if static_url and not static_url.startswith("http") else static_url
                return RailwayDeployResult(
                    success=True,
                    url=url or None,
                    environment_id=environment_id,
                    deployment_id=deployment.get("id"),
                )
            elif status in ("FAILED", "CRASHED", "REMOVED"):
                return RailwayDeployResult(
                    success=False,
                    environment_id=environment_id,
                    error=f"Railway deployment {status.lower()}",
                )

        return RailwayDeployResult(
            success=False,
            environment_id=environment_id,
            error=f"Railway deployment timed out after {DEPLOY_TIMEOUT}s",
        )

    except Exception as e:
        logger.exception("Railway deploy error")
        return RailwayDeployResult(success=False, error=str(e))


async def delete_preview_env(railway_token: str, environment_id: str) -> bool:
    """Delete a Railway preview environment (cleanup)."""
    try:
        query = """
        mutation($id: String!) {
            environmentDelete(id: $id)
        }
        """
        await _graphql(railway_token, query, {"id": environment_id})
        return True
    except Exception:
        return False
