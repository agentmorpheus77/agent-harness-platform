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
    # Bundled skills (checked into repo under /skills/)
    "/app/skills",
    # Railway/production paths (cloned at startup)
    "/app/skills/cdb-skills/skills",
    "/app/skills/cdb-skills",
    # Local development paths
    os.path.expanduser("~/.agents/skills"),
    os.path.expanduser("~/clawd/skills"),
    os.path.expanduser("~/Projects/cdb-skills/skills"),
    os.path.expanduser("~/Projects/cdb-skills"),
    # Bundled skills in project root (dev)
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills"),
]


@dataclass
class SkillInfo:
    name: str
    description: str = ""
    version: str = "0.0.0"
    status: str = "available"  # 'loaded' | 'available' | 'outdated'
    path: str = ""
    keywords: list[str] = field(default_factory=list)
    required_keys: list[str] = field(default_factory=list)
    has_all_keys: bool = False


_KNOWN_API_KEYS = [
    "FIRECRAWL_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "ELEVENLABS_API_KEY",
    "WHISPER_API_KEY",
    "GITHUB_TOKEN",
    "RAILWAY_API_KEY",
    "VERCEL_TOKEN",
    "SENTRY_AUTH_TOKEN",
]


def parse_required_keys(skill_content: str) -> list[str]:
    """Extract API key requirements from SKILL.md content.

    Looks for known API key names (e.g. FIRECRAWL_API_KEY) and common patterns
    like 'requires ... API key' in the skill content.
    """
    found: list[str] = []
    upper_content = skill_content.upper()
    for key in _KNOWN_API_KEYS:
        if key in upper_content:
            found.append(key)
    return sorted(set(found))


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
            required_keys = parse_required_keys(content)

            skills.append(
                SkillInfo(
                    name=name,
                    description=desc,
                    version=meta.get("version", "0.0.0"),
                    status=git_status,
                    path=str(skill_dir),
                    keywords=keywords,
                    required_keys=required_keys,
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


# ── Auto Skill Loading: detect skills from repo file tree ────────────────────

INLINE_SKILL_CONTENTS: dict[str, str] = {
    "typescript": """## TypeScript/React Best Practices
- Use typed props and interfaces for all components
- Prefer functional components with hooks over class components
- Use `const` assertions and discriminated unions for type safety
- Avoid `any` — use `unknown` + type guards when types are uncertain
- Use barrel exports (index.ts) for clean imports
- Keep components small and focused; extract logic into custom hooks
- Use React.memo() only when profiling shows unnecessary re-renders
- Prefer named exports over default exports for better refactoring support""",

    "python": """## Python Best Practices
- Use type hints for all function signatures and return types
- Prefer async/await for I/O-bound operations
- Use dataclasses or Pydantic models for structured data
- Follow PEP 8 naming: snake_case for functions/variables, PascalCase for classes
- Use context managers (with statements) for resource management
- Prefer pathlib.Path over os.path for file operations
- Use logging module instead of print statements
- Write docstrings for public functions and classes""",

    "railway": """## Railway Deployment
- Use nixpacks.toml for build configuration when possible
- Set environment variables via Railway dashboard or CLI, never in code
- Use railway.json for service configuration (start command, healthcheck)
- Enable auto-deploys from the main branch
- Use Railway volumes for persistent storage, not local filesystem
- Configure healthcheck endpoints for zero-downtime deploys
- Use Railway's built-in PostgreSQL/Redis instead of external providers""",

    "testing": """## Testing Best Practices
- Write tests that verify behavior, not implementation details
- Use descriptive test names that explain the expected outcome
- Follow Arrange-Act-Assert pattern for test structure
- Mock external dependencies (APIs, databases) at the boundary
- Aim for high coverage on business logic, lower on glue code
- Use fixtures/factories for test data setup
- Run tests in CI on every push; block merges on failure
- Prefer integration tests over unit tests for API endpoints""",

    "tailwind": """## Tailwind CSS Best Practices
- Use utility classes directly in JSX; avoid @apply in most cases
- Leverage Tailwind's design system (spacing, colors) for consistency
- Use responsive prefixes (sm:, md:, lg:) for mobile-first design
- Extract repeated patterns into components, not CSS classes
- Use dark: prefix for dark mode support
- Prefer gap utilities over margin for flex/grid layouts
- Use cn() or clsx() for conditional class composition
- Keep custom theme extensions minimal; use existing scale values""",

    "i18n": """## Internationalization Best Practices
- Extract ALL user-facing strings into translation files
- Use namespaced keys (e.g., 'settings.title') for organization
- Never concatenate translated strings; use interpolation
- Support RTL layouts if targeting Arabic/Hebrew locales
- Use ICU message format for plurals and gender
- Keep translation keys in English as the source of truth
- Test with longer translations (German is ~30% longer than English)
- Lazy-load translations for non-default locales""",
}


def detect_repo_skills(file_tree: list[str]) -> list[str]:
    """Detect relevant skills based on files present in a repository.

    Args:
        file_tree: List of file/directory names at the repo root level.

    Returns:
        List of skill names that should be loaded.
    """
    skills: list[str] = []
    file_set = set(file_tree)
    file_lower = {f.lower() for f in file_tree}

    # TypeScript / React
    if "package.json" in file_set or "tsconfig.json" in file_set:
        skills.append("typescript")

    # Railway
    if "railway.toml" in file_set or "nixpacks.toml" in file_set or "railway.json" in file_set:
        skills.append("railway")

    # Python
    if "requirements.txt" in file_set or "pyproject.toml" in file_set or "setup.py" in file_set:
        skills.append("python")

    # Testing — check for test directories or test file patterns
    test_indicators = {"tests", "test", "__tests__", "spec", "pytest.ini", "jest.config.js", "vitest.config.ts"}
    if test_indicators & file_lower:
        skills.append("testing")
    elif any(f for f in file_tree if ".test." in f or ".spec." in f or "_test." in f):
        skills.append("testing")

    # Tailwind
    if any(f.startswith("tailwind.config") for f in file_tree):
        skills.append("tailwind")
    # Also check for tailwind in CSS files — but we can only check filenames here
    # The caller can do deeper analysis if needed

    # i18n
    i18n_indicators = {"i18n", "locales", "translations", "lang"}
    if i18n_indicators & file_lower:
        skills.append("i18n")

    return skills


def load_inline_skill(skill_name: str) -> str | None:
    """Load inline skill content by name."""
    return INLINE_SKILL_CONTENTS.get(skill_name)



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
