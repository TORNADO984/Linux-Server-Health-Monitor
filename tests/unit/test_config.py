"""Unit tests for the configuration module."""

from __future__ import annotations

from pathlib import Path

import pytest

from server_health.config import (
    DEFAULT_CPU_CRITICAL,
    DEFAULT_CPU_WARNING,
    DEFAULT_DISK_WARNING,
    DEFAULT_MEMORY_WARNING,
    AppConfig,
    ThresholdConfig,
    load_config,
)


class TestThresholdConfig:
    def test_default_values(self):
        tc = ThresholdConfig()
        assert tc.cpu_warning == DEFAULT_CPU_WARNING
        assert tc.cpu_critical == DEFAULT_CPU_CRITICAL
        assert tc.memory_warning == DEFAULT_MEMORY_WARNING
        assert tc.disk_warning == DEFAULT_DISK_WARNING

    def test_validation_passes_on_valid_config(self):
        tc = ThresholdConfig(cpu_warning=50, cpu_critical=90)
        tc.validate()

    def test_validation_fails_when_warning_exceeds_critical(self):
        tc = ThresholdConfig(cpu_warning=95, cpu_critical=90)
        with pytest.raises(ValueError, match="cpu_warning"):
            tc.validate()

    def test_validation_fails_when_values_are_zero(self):
        tc = ThresholdConfig(cpu_warning=0, cpu_critical=90)
        with pytest.raises(ValueError):
            tc.validate()

    def test_to_dict(self):
        tc = ThresholdConfig()
        d = tc.to_dict()
        assert "cpu_warning" in d
        assert "cpu_critical" in d
        assert "memory_warning" in d
        assert "disk_warning" in d
        assert "load_warning" in d


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.log_level == "INFO"
        assert cfg.top_processes > 0
        assert isinstance(cfg.services, list)
        assert len(cfg.services) > 0

    def test_to_dict(self):
        cfg = AppConfig()
        d = cfg.to_dict()
        assert "thresholds" in d
        assert "services" in d
        assert "top_processes" in d
        assert "log_level" in d


class TestLoadConfig:
    def test_loads_defaults_when_no_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        cfg = load_config(config_file=None)
        assert cfg.thresholds.cpu_warning == DEFAULT_CPU_WARNING

    def test_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SERVER_HEALTH_CPU_WARNING", "55")
        cfg = load_config(config_file=None)
        assert cfg.thresholds.cpu_warning == 55

    def test_invalid_env_var_uses_default(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SERVER_HEALTH_CPU_WARNING", "not_a_number")
        cfg = load_config(config_file=None)
        assert cfg.thresholds.cpu_warning == DEFAULT_CPU_WARNING

    def test_yaml_config_file_loaded(self, tmp_path: Path):
        yaml_content = """
thresholds:
  cpu_warning: 60
  cpu_critical: 85
  memory_warning: 65
  memory_critical: 88
  disk_warning: 70
  disk_critical: 88
  load_warning: 1.5
  load_critical: 3.0
services:
  - ssh
  - nginx
top_processes: 10
"""
        config_file = tmp_path / "server-health.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")
        cfg = load_config(config_file=config_file)
        assert cfg.thresholds.cpu_warning == 60
        assert cfg.thresholds.cpu_critical == 85
        assert cfg.top_processes == 10
        assert "nginx" in cfg.services

    def test_invalid_threshold_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SERVER_HEALTH_CPU_WARNING", "95")
        monkeypatch.setenv("SERVER_HEALTH_CPU_CRITICAL", "90")
        with pytest.raises(ValueError):
            load_config(config_file=None)

    def test_services_from_env_var(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SERVER_HEALTH_SERVICES", "nginx,mysql,redis")
        cfg = load_config(config_file=None)
        assert "nginx" in cfg.services
        assert "mysql" in cfg.services
        assert "redis" in cfg.services
