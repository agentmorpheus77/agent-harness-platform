"""Tests for complexity estimator."""

from backend.core.complexity import estimate_complexity


def test_simple_bug_fix():
    result = estimate_complexity("Fix typo in README")
    assert result.tier == "free"
    assert result.estimated_files >= 1
    assert result.score < 3.0


def test_moderate_feature():
    result = estimate_complexity("Add API endpoint for user profile")
    assert result.tier == "balanced"
    assert "backend" in result.categories


def test_complex_auth_feature():
    result = estimate_complexity(
        "Implement OAuth2 authentication with role-based authorization",
        "Add authentication and authorization middleware, database migration for user roles, "
        "encrypt sensitive tokens, update API endpoints and frontend components with security best practices"
    )
    assert result.tier == "premium"
    assert result.score >= 7.0
    assert "security" in result.categories


def test_frontend_only():
    result = estimate_complexity("Add dark mode toggle button")
    assert "frontend" in result.categories


def test_empty_body():
    result = estimate_complexity("Something")
    assert result.tier == "free"
    assert result.estimated_files >= 1


def test_long_description_increases_score():
    short = estimate_complexity("Add button", "Add a button to the page")
    long = estimate_complexity("Add button", " ".join(["word"] * 120))
    assert long.score > short.score
