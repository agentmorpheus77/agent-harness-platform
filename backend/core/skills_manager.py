"""Skills manager — scans, parses, and manages skills from cdb-skills directories."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


DEFAULT_SKILL_DIRS = [
    os.path.expanduser("~/.agents/skills"),
    os.path.expanduser("~/clawd/skills"),
    os.path.expanduser("~/Projects/cdb-skills"),
]


@dataclass
class SkillInfo:
    name: str
    description: str = ""
    version: str = "0.0.0"
    status: str = "available"  # 'loaded' | 'available' | 'outdated'
    path: str = ""
    keywords: list[str] = field(default_factory=list)


def parse_skill_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from a SKILL.md file."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def check_git_status(skill_dir: str) -> str:
    """Check if a skill directory is up to date with origin."""
    try:
        result = subprocess.run(
            ["git", "fetch", "--dry-run"],
            cwd=skill_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        # If fetch --dry-run produces output, there are remote changes
        if result.stdout.strip() or result.stderr.strip():
            return "outdated"
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "available"


def scan_skills(dirs: Optional[list[str]] = None) -> list[SkillInfo]:
    """Scan skill directories for SKILL.md files and return structured list."""
    if dirs is None:
        dirs = DEFAULT_SKILL_DIRS

    skills: list[SkillInfo] = []
    seen_names: set[str] = set()

    for base_dir in dirs:
        base_path = Path(base_dir)
        if not base_path.exists():
            continue

        # Look for SKILL.md files in immediate subdirectories
        for skill_dir in sorted(base_path.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue

            meta = parse_skill_frontmatter(content)
            name = meta.get("name", skill_dir.name)

            if name in seen_names:
                continue
            seen_names.add(name)

            # Extract keywords from description and name
            desc = meta.get("description", "")
            keywords_raw = meta.get("keywords", [])
            if isinstance(keywords_raw, str):
                keywords_raw = [k.strip() for k in keywords_raw.split(",")]
            keywords = list(keywords_raw) if keywords_raw else []
            # Add name parts as keywords
            keywords.extend(name.lower().replace("-", " ").split())

            git_status = check_git_status(str(base_path))

            skills.append(
                SkillInfo(
                    name=name,
                    description=desc,
                    version=meta.get("version", "0.0.0"),
                    status=git_status,
                    path=str(skill_dir),
                    keywords=keywords,
                )
            )

    return skills


def get_relevant_skills(
    repo_path: Optional[str], issue_description: str, dirs: Optional[list[str]] = None
) -> list[str]:
    """Return skill names relevant to a repo and/or issue description via keyword matching."""
    all_skills = scan_skills(dirs)
    if not all_skills:
        return []

    # Build search terms from issue description + repo indicators
    search_terms: set[str] = set()

    if issue_description:
        for word in re.findall(r"[a-zA-Z]+", issue_description.lower()):
            if len(word) > 2:
                search_terms.add(word)

    if repo_path:
        repo = Path(repo_path)
        if (repo / "package.json").exists():
            search_terms.update(["typescript", "javascript", "frontend", "react", "node"])
        if (repo / "railway.toml").exists() or (repo / "railway.json").exists():
            search_terms.update(["cicd", "pipeline", "deploy", "railway"])
        if (repo / "tsconfig.json").exists():
            search_terms.add("typescript")
        if any((repo / d).exists() for d in ["i18n", "locales", "translations"]):
            search_terms.add("i18n")
        if any((repo / d).exists() for d in ["tests", "test", "__tests__", "spec"]):
            search_terms.update(["testing", "test", "qa"])
        if any((repo / d).exists() for d in ["src/components", "components", "pages", "views"]):
            search_terms.update(["ui", "ux", "frontend"])
        if (repo / "requirements.txt").exists() or (repo / "pyproject.toml").exists():
            search_terms.update(["python", "backend"])
        if (repo / "Dockerfile").exists():
            search_terms.update(["docker", "container"])

    # Score skills by semantic keyword overlap
    relevant: list[tuple[float, str]] = []
    for skill in all_skills:
        score = 0.0
        skill_words = set(skill.keywords)
        skill_words.update(w.lower() for w in re.findall(r"[a-zA-Z]+", skill.description))

        matched_terms = 0
        for term in search_terms:
            if term in skill_words:
                score += 1.0
                matched_terms += 1
            if term in skill.name.lower():
                score += 2.0
                matched_terms += 1

        # Require at least 2 keyword matches to filter out weak/coincidental hits
        if matched_terms >= 2:
            # Normalize by total search terms to favor precision over recall
            if search_terms:
                score *= matched_terms / len(search_terms)
            relevant.append((score, skill.name))

    relevant.sort(key=lambda x: x[0], reverse=True)
    return [name for _, name in relevant[:5]]


def update_skill(skill_dir: str) -> dict:
    """Git pull on a skill directory. Returns status dict."""
    try:
        result = subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=skill_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None,
        }
    except subprocess.SubprocessError as e:
        return {"success": False, "output": "", "error": str(e)}


def update_all_skills(dirs: Optional[list[str]] = None) -> list[dict]:
    """Git pull on all skill base directories."""
    if dirs is None:
        dirs = DEFAULT_SKILL_DIRS
    results = []
    for d in dirs:
        if Path(d).exists() and (Path(d) / ".git").exists():
            res = update_skill(d)
            res["dir"] = d
            results.append(res)
    return results


def load_skill_content(skill_name: str, dirs: Optional[list[str]] = None) -> Optional[str]:
    """Load and return the full SKILL.md content for a given skill name."""
    if dirs is None:
        dirs = DEFAULT_SKILL_DIRS

    for base_dir in dirs:
        skill_file = Path(base_dir) / skill_name / "SKILL.md"
        if skill_file.exists():
            try:
                return skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
    return None
