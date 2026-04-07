"""Tests for config.yml loading correctness (audit finding 10.8).

Verifies that the application config file is well-formed and that the
dependency injection container can load its values.
"""

import os
from pathlib import Path

import yaml
import pytest


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "app" / "config.yml"


class TestConfigYml:

    @pytest.fixture
    def config(self):
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f)

    def test_config_file_exists(self):
        assert _CONFIG_PATH.exists()

    def test_concurrency_section(self, config):
        assert "concurrency" in config
        conc = config["concurrency"]
        assert "queue_size" in conc
        assert "max_retries" in conc
        assert "num_workers" in conc
        assert isinstance(conc["queue_size"], int)
        assert isinstance(conc["max_retries"], int)
        assert isinstance(conc["num_workers"], int)

    def test_prompt_provider_section(self, config):
        pp = config["prompt_provider"]
        assert "base_url" in pp
        assert "max_retries" in pp
        assert "timeout_seconds" in pp
        assert "circuit_breaker_fail_threshold" in pp
        assert "circuit_breaker_reset_timeout" in pp
        assert "system_prompt" in pp

    def test_notification_provider_section(self, config):
        np = config["notification_provider"]
        assert "base_url" in np
        assert "max_retries" in np
        assert "timeout_seconds" in np
        assert "circuit_breaker_fail_threshold" in np
        assert "circuit_breaker_reset_timeout" in np

    def test_provider_urls_are_strings(self, config):
        assert isinstance(config["prompt_provider"]["base_url"], str)
        assert isinstance(config["notification_provider"]["base_url"], str)

    def test_auth_headers_from_env(self):
        """Auth headers are now sourced from environment variables, not config."""
        from dependencies import _build_auth_header
        header = _build_auth_header('TEST_API_KEY', 'fallback')
        assert isinstance(header, dict)
        assert 'X-API-Key' in header

    def test_positive_numeric_values(self, config):
        for section in ("prompt_provider", "notification_provider"):
            assert config[section]["max_retries"] > 0
            assert config[section]["timeout_seconds"] > 0
            assert config[section]["circuit_breaker_fail_threshold"] > 0
            assert config[section]["circuit_breaker_reset_timeout"] > 0
