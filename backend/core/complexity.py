"""Heuristic complexity estimator for issues."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

KEYWORD_WEIGHTS: dict[str, dict[str, float]] = {
    "ui": {"weight": 1.0, "category": "frontend"},
    "frontend": {"weight": 1.0, "category": "frontend"},
    "component": {"weight": 1.0, "category": "frontend"},
    "button": {"weight": 0.5, "category": "frontend"},
    "page": {"weight": 1.0, "category": "frontend"},
    "modal": {"weight": 1.0, "category": "frontend"},
    "form": {"weight": 1.0, "category": "frontend"},
    "style": {"weight": 0.5, "category": "frontend"},
    "css": {"weight": 0.5, "category": "frontend"},
    "tailwind": {"weight": 0.5, "category": "frontend"},
    "database": {"weight": 2.0, "category": "backend"},
    "migration": {"weight": 2.5, "category": "backend"},
    "schema": {"weight": 2.0, "category": "backend"},
    "model": {"weight": 1.5, "category": "backend"},
    "api": {"weight": 1.5, "category": "backend"},
    "endpoint": {"weight": 1.5, "category": "backend"},
    "route": {"weight": 1.0, "category": "backend"},
    "auth": {"weight": 3.0, "category": "security"},
    "authentication": {"weight": 3.0, "category": "security"},
    "authorization": {"weight": 3.0, "category": "security"},
    "security": {"weight": 3.0, "category": "security"},
    "encrypt": {"weight": 2.5, "category": "security"},
    "test": {"weight": 1.0, "category": "testing"},
    "refactor": {"weight": 2.0, "category": "architecture"},
    "architecture": {"weight": 3.0, "category": "architecture"},
    "deploy": {"weight": 2.0, "category": "devops"},
    "ci": {"weight": 1.5, "category": "devops"},
    "docker": {"weight": 2.0, "category": "devops"},
    "i18n": {"weight": 1.5, "category": "frontend"},
    "internationalization": {"weight": 1.5, "category": "frontend"},
    "websocket": {"weight": 2.0, "category": "backend"},
    "streaming": {"weight": 2.0, "category": "backend"},
    "performance": {"weight": 2.0, "category": "architecture"},
    "bug": {"weight": 1.0, "category": "fix"},
    "fix": {"weight": 0.5, "category": "fix"},
    "typo": {"weight": 0.2, "category": "fix"},
}


@dataclass
class ComplexityEstimate:
    tier: str  # "free", "balanced", "premium"
    reason: str
    estimated_files: int
    score: float
    categories: list[str]


def estimate_complexity(title: str, body: str = "") -> ComplexityEstimate:
    """Estimate issue complexity based on keywords in title and body."""
    text = f"{title} {body}".lower()
    words = set(re.findall(r'\b\w+\b', text))

    total_score = 0.0
    matched_categories: set[str] = set()

    for keyword, info in KEYWORD_WEIGHTS.items():
        if keyword in words:
            total_score += info["weight"]
            matched_categories.add(info["category"])

    # Estimate affected files based on categories
    estimated_files = max(1, len(matched_categories) * 2)

    # Longer descriptions usually mean more complex
    word_count = len(text.split())
    if word_count > 100:
        total_score += 1.5
    elif word_count > 50:
        total_score += 0.5

    # Determine tier
    if total_score < 3.0:
        tier = "free"
        reason = "Simple change — few affected areas"
    elif total_score < 7.0:
        tier = "balanced"
        reason = "Moderate complexity — multiple areas affected"
    else:
        tier = "premium"
        reason = "Complex change — multiple systems, security, or architecture involved"

    return ComplexityEstimate(
        tier=tier,
        reason=reason,
        estimated_files=estimated_files,
        score=round(total_score, 1),
        categories=sorted(matched_categories),
    )
