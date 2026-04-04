"""Tests for harness_config.py — loading harness.yaml from repos."""

from backend.core.harness_config import HarnessConfig, load_harness_config


class TestLoadHarnessConfig:
    def test_defaults_when_no_file(self, tmp_path):
        config = load_harness_config(str(tmp_path))
        assert config.version == "1.0"
        assert config.deploy.provider == "none"
        assert config.agent.max_iterations == 20
        assert config.agent.model_tier == "balanced"
        assert config.notifications.on_complete is True

    def test_loads_harness_yaml(self, tmp_path):
        (tmp_path / "harness.yaml").write_text(
            "version: '2.0'\ndeploy:\n  provider: railway\n  health_timeout: 60\nagent:\n  model_tier: premium\n"
        )
        config = load_harness_config(str(tmp_path))
        assert config.version == "2.0"
        assert config.deploy.provider == "railway"
        assert config.deploy.health_timeout == 60
        assert config.agent.model_tier == "premium"

    def test_loads_dot_harness_yaml(self, tmp_path):
        (tmp_path / ".harness.yaml").write_text("deploy:\n  provider: docker\n")
        config = load_harness_config(str(tmp_path))
        assert config.deploy.provider == "docker"

    def test_harness_yaml_takes_precedence(self, tmp_path):
        (tmp_path / "harness.yaml").write_text("deploy:\n  provider: railway\n")
        (tmp_path / ".harness.yaml").write_text("deploy:\n  provider: docker\n")
        config = load_harness_config(str(tmp_path))
        assert config.deploy.provider == "railway"

    def test_invalid_yaml_returns_defaults(self, tmp_path):
        (tmp_path / "harness.yaml").write_text(": bad: yaml: [[")
        config = load_harness_config(str(tmp_path))
        assert config.version == "1.0"

    def test_empty_file_returns_defaults(self, tmp_path):
        (tmp_path / "harness.yaml").write_text("")
        config = load_harness_config(str(tmp_path))
        assert config.version == "1.0"

    def test_partial_config(self, tmp_path):
        (tmp_path / "harness.yaml").write_text("skills:\n  always_load:\n    - typescript\n    - testing\n")
        config = load_harness_config(str(tmp_path))
        assert config.skills.always_load == ["typescript", "testing"]
        assert config.deploy.provider == "none"  # default

    def test_skills_extra_dirs(self, tmp_path):
        (tmp_path / "harness.yaml").write_text(
            "skills:\n  extra_dirs:\n    - ./custom-skills\n    - /shared/skills\n"
        )
        config = load_harness_config(str(tmp_path))
        assert config.skills.extra_dirs == ["./custom-skills", "/shared/skills"]

    def test_own_repo_config(self):
        """Dog-food: load this repo's own harness.yaml."""
        import os

        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config = load_harness_config(repo_root)
        assert config.version == "1.0"
        assert config.deploy.provider == "docker"
