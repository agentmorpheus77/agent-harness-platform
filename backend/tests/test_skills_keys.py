"""Tests for skill API key requirements parsing and has_all_keys logic."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.core.skills_manager import SkillInfo, parse_required_keys


class TestParseRequiredKeys:
    def test_firecrawl_key(self):
        content = """---
name: firecrawl-interact
---
## Prerequisites
- Environment variable `FIRECRAWL_API_KEY` must be set
"""
        keys = parse_required_keys(content)
        assert "FIRECRAWL_API_KEY" in keys

    def test_openai_key(self):
        content = """
const apiKey = process.env.OPENAI_API_KEY
throw new Error('OPENAI_API_KEY not configured')
"""
        keys = parse_required_keys(content)
        assert "OPENAI_API_KEY" in keys

    def test_multiple_keys(self):
        content = """
Uses FIRECRAWL_API_KEY for scraping.
Also needs OPENAI_API_KEY for completions.
And ANTHROPIC_API_KEY for Claude.
"""
        keys = parse_required_keys(content)
        assert "FIRECRAWL_API_KEY" in keys
        assert "OPENAI_API_KEY" in keys
        assert "ANTHROPIC_API_KEY" in keys
        assert len(keys) == 3

    def test_no_keys(self):
        content = """---
name: testing-qa
description: QA guidelines
---
# Testing Best Practices
Write tests for all code.
"""
        keys = parse_required_keys(content)
        assert keys == []

    def test_case_insensitive_matching(self):
        content = "You need a firecrawl_api_key to use this."
        keys = parse_required_keys(content)
        assert "FIRECRAWL_API_KEY" in keys

    def test_deduplicates(self):
        content = """
Set FIRECRAWL_API_KEY in your env.
Make sure FIRECRAWL_API_KEY is configured.
"""
        keys = parse_required_keys(content)
        assert keys.count("FIRECRAWL_API_KEY") == 1

    def test_github_token(self):
        content = "Requires GITHUB_TOKEN with repo scope."
        keys = parse_required_keys(content)
        assert "GITHUB_TOKEN" in keys

    def test_vercel_and_sentry(self):
        content = """
VERCEL_TOKEN for deployment.
SENTRY_AUTH_TOKEN for monitoring.
"""
        keys = parse_required_keys(content)
        assert "VERCEL_TOKEN" in keys
        assert "SENTRY_AUTH_TOKEN" in keys


class TestHasAllKeysAPI:
    @patch("backend.api.skills.scan_skills")
    def test_has_all_keys_true_no_keys_required(
        self, mock_scan, client: TestClient, auth_headers: dict
    ):
        mock_scan.return_value = [
            SkillInfo(
                name="testing-qa",
                description="QA",
                version="1.0.0",
                status="available",
                path="/skills/testing-qa",
                keywords=["testing"],
                required_keys=[],
            ),
        ]
        resp = client.get("/api/skills", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["has_all_keys"] is True
        assert data[0]["required_keys"] == []

    @patch("backend.api.skills.scan_skills")
    def test_has_all_keys_false_when_missing(
        self, mock_scan, client: TestClient, auth_headers: dict
    ):
        mock_scan.return_value = [
            SkillInfo(
                name="firecrawl",
                description="Scraping",
                version="1.0.0",
                status="available",
                path="/skills/firecrawl",
                keywords=["firecrawl"],
                required_keys=["FIRECRAWL_API_KEY"],
            ),
        ]
        resp = client.get("/api/skills", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["has_all_keys"] is False
        assert data[0]["required_keys"] == ["FIRECRAWL_API_KEY"]

    @patch("backend.api.skills.scan_skills")
    def test_has_all_keys_true_when_configured(
        self, mock_scan, client: TestClient, auth_headers: dict
    ):
        # First save the required key in settings
        client.put(
            "/api/settings",
            json=[{"key": "FIRECRAWL_API_KEY", "value": "fc-test-key-123"}],
            headers=auth_headers,
        )

        mock_scan.return_value = [
            SkillInfo(
                name="firecrawl",
                description="Scraping",
                version="1.0.0",
                status="available",
                path="/skills/firecrawl",
                keywords=["firecrawl"],
                required_keys=["FIRECRAWL_API_KEY"],
            ),
        ]
        resp = client.get("/api/skills", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["has_all_keys"] is True

    @patch("backend.api.skills.scan_skills")
    def test_has_all_keys_partial(
        self, mock_scan, client: TestClient, auth_headers: dict
    ):
        # Save one key but not the other
        client.put(
            "/api/settings",
            json=[{"key": "OPENAI_API_KEY", "value": "sk-test"}],
            headers=auth_headers,
        )

        mock_scan.return_value = [
            SkillInfo(
                name="audio",
                description="Audio processing",
                version="1.0.0",
                status="available",
                path="/skills/audio",
                keywords=["audio"],
                required_keys=["OPENAI_API_KEY", "ELEVENLABS_API_KEY"],
            ),
        ]
        resp = client.get("/api/skills", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["has_all_keys"] is False

    @patch("backend.api.skills.scan_skills")
    def test_response_includes_new_fields(
        self, mock_scan, client: TestClient, auth_headers: dict
    ):
        mock_scan.return_value = [
            SkillInfo(
                name="test-skill",
                description="Test",
                version="1.0.0",
                status="available",
                path="/skills/test",
                keywords=[],
                required_keys=["GITHUB_TOKEN"],
            ),
        ]
        resp = client.get("/api/skills", headers=auth_headers)
        data = resp.json()
        assert "required_keys" in data[0]
        assert "has_all_keys" in data[0]
