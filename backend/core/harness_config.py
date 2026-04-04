"""Reader for harness.yaml repo-level configuration files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class DeployConfig:
    provider: str = "none"
    seed_command: str = ""
    health_check: str = "/health"
    health_timeout: int = 30


@dataclass
class SkillsConfig:
    extra_dirs: list[str] = field(default_factory=list)
    always_load: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    max_iterations: int = 20
    model_tier: str = "balanced"


@dataclass
class NotificationsConfig:
    on_complete: bool = True
    on_error: bool = True


@dataclass
class HarnessConfig:
    version: str = "1.0"
    deploy: DeployConfig = field(default_factory=DeployConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)


def load_harness_config(repo_path: str) -> HarnessConfig:
    """Load harness.yaml from a repo directory. Returns defaults if not found."""
    config_path = Path(repo_path) / "harness.yaml"
    if not config_path.exists():
        # Also check .harness.yaml
        config_path = Path(repo_path) / ".harness.yaml"
    if not config_path.exists():
        return HarnessConfig()

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return HarnessConfig()

    if not isinstance(raw, dict):
        return HarnessConfig()

    deploy_raw = raw.get("deploy", {}) or {}
    skills_raw = raw.get("skills", {}) or {}
    agent_raw = raw.get("agent", {}) or {}
    notif_raw = raw.get("notifications", {}) or {}

    return HarnessConfig(
        version=str(raw.get("version", "1.0")),
        deploy=DeployConfig(
            provider=deploy_raw.get("provider", "none"),
            seed_command=deploy_raw.get("seed_command", ""),
            health_check=deploy_raw.get("health_check", "/health"),
            health_timeout=int(deploy_raw.get("health_timeout", 30)),
        ),
        skills=SkillsConfig(
            extra_dirs=list(skills_raw.get("extra_dirs", [])),
            always_load=list(skills_raw.get("always_load", [])),
        ),
        agent=AgentConfig(
            max_iterations=int(agent_raw.get("max_iterations", 20)),
            model_tier=agent_raw.get("model_tier", "balanced"),
        ),
        notifications=NotificationsConfig(
            on_complete=bool(notif_raw.get("on_complete", True)),
            on_error=bool(notif_raw.get("on_error", True)),
        ),
    )
