"""Configuration management for Server Health Monitor.

Supports layered configuration:
  1. Default values (built-in)
  2. Configuration file (YAML, from XDG config dir or project root)
  3. Environment variables (SERVER_HEALTH_* prefix)
  4. CLI arguments (handled by CLI layer)

No secrets should ever be stored in configuration.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default threshold values
# ---------------------------------------------------------------------------

DEFAULT_CPU_WARNING: int = 70
DEFAULT_CPU_CRITICAL: int = 90

DEFAULT_MEMORY_WARNING: int = 75
DEFAULT_MEMORY_CRITICAL: int = 90

DEFAULT_DISK_WARNING: int = 80
DEFAULT_DISK_CRITICAL: int = 90

DEFAULT_LOAD_WARNING: float = 2.0
DEFAULT_LOAD_CRITICAL: float = 4.0

DEFAULT_TOP_PROCESSES: int = 5

DEFAULT_SERVICES: list[str] = [
    "ssh",
    "sshd",
    "docker",
    "nginx",
    "apache2",
    "mysql",
    "postgresql",
    "redis",
    "fail2ban",
    "ufw",
    "cron",
    "rsyslog",
]

# ---------------------------------------------------------------------------
# Config file search paths
# ---------------------------------------------------------------------------

CONFIG_FILE_NAMES = [
    "server-health.yaml",
    "server-health.yml",
    ".server-health.yaml",
    ".server-health.yml",
]

CONFIG_SEARCH_PATHS = [
    Path.home() / ".config" / "server-health",
    Path("/etc/server-health"),
    Path.cwd(),
]


class ThresholdConfig:
    """Holds threshold values for health evaluation."""

    def __init__(
        self,
        cpu_warning: int = DEFAULT_CPU_WARNING,
        cpu_critical: int = DEFAULT_CPU_CRITICAL,
        memory_warning: int = DEFAULT_MEMORY_WARNING,
        memory_critical: int = DEFAULT_MEMORY_CRITICAL,
        disk_warning: int = DEFAULT_DISK_WARNING,
        disk_critical: int = DEFAULT_DISK_CRITICAL,
        load_warning: float = DEFAULT_LOAD_WARNING,
        load_critical: float = DEFAULT_LOAD_CRITICAL,
    ) -> None:
        self.cpu_warning = cpu_warning
        self.cpu_critical = cpu_critical
        self.memory_warning = memory_warning
        self.memory_critical = memory_critical
        self.disk_warning = disk_warning
        self.disk_critical = disk_critical
        self.load_warning = load_warning
        self.load_critical = load_critical

    def validate(self) -> None:
        """Validate that thresholds are logically consistent."""
        pairs = [
            ("cpu_warning", self.cpu_warning, "cpu_critical", self.cpu_critical),
            ("memory_warning", self.memory_warning, "memory_critical", self.memory_critical),
            ("disk_warning", self.disk_warning, "disk_critical", self.disk_critical),
            ("load_warning", self.load_warning, "load_critical", self.load_critical),
        ]
        for warn_name, warn_val, crit_name, crit_val in pairs:
            if warn_val >= crit_val:
                raise ValueError(
                    f"Configuration error: {warn_name} ({warn_val}) must be less than "
                    f"{crit_name} ({crit_val})"
                )
            if warn_val <= 0 or crit_val <= 0:
                raise ValueError(
                    f"Configuration error: threshold values must be positive "
                    f"(got {warn_name}={warn_val}, {crit_name}={crit_val})"
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize thresholds to a plain dictionary."""
        return {
            "cpu_warning": self.cpu_warning,
            "cpu_critical": self.cpu_critical,
            "memory_warning": self.memory_warning,
            "memory_critical": self.memory_critical,
            "disk_warning": self.disk_warning,
            "disk_critical": self.disk_critical,
            "load_warning": self.load_warning,
            "load_critical": self.load_critical,
        }


class AppConfig:
    """Application-wide configuration container."""

    def __init__(
        self,
        thresholds: ThresholdConfig | None = None,
        top_processes: int = DEFAULT_TOP_PROCESSES,
        services: list[str] | None = None,
        log_level: str = "INFO",
    ) -> None:
        self.thresholds = thresholds or ThresholdConfig()
        self.top_processes = top_processes
        self.services = services or list(DEFAULT_SERVICES)
        self.log_level = log_level

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to a plain dictionary."""
        return {
            "thresholds": self.thresholds.to_dict(),
            "top_processes": self.top_processes,
            "services": self.services,
            "log_level": self.log_level,
        }


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def _find_config_file() -> Path | None:
    """Search standard paths for a configuration file."""
    for directory in CONFIG_SEARCH_PATHS:
        for name in CONFIG_FILE_NAMES:
            candidate = directory / name
            if candidate.is_file():
                logger.debug("Found configuration file: %s", candidate)
                return candidate
    return None


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML config file safely, returning an empty dict on failure."""
    try:
        import yaml  # type: ignore[import]
    except ImportError:
        logger.warning("PyYAML is not installed; skipping config file: %s", path)
        return {}

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            if not isinstance(data, dict):
                logger.warning("Config file %s did not contain a mapping; ignoring.", path)
                return {}
            return data
    except OSError as exc:
        logger.warning("Could not read config file %s: %s", path, exc)
        return {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse config file %s: %s", path, exc)
        return {}


def _env(key: str, default: str | None = None) -> str | None:
    """Read a SERVER_HEALTH_ prefixed environment variable."""
    return os.environ.get(f"SERVER_HEALTH_{key}", default)


def _env_int(key: str, default: int) -> int:
    """Read an integer SERVER_HEALTH_ env var, falling back to default."""
    raw = _env(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "Environment variable SERVER_HEALTH_%s='%s' is not a valid integer; using default %d",
            key,
            raw,
            default,
        )
        return default


def _env_float(key: str, default: float) -> float:
    """Read a float SERVER_HEALTH_ env var, falling back to default."""
    raw = _env(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "Environment variable SERVER_HEALTH_%s='%s' is not a valid float; using default %f",
            key,
            raw,
            default,
        )
        return default


def load_config(config_file: Path | None = None) -> AppConfig:
    """Load and merge configuration from all sources.

    Priority (highest wins):
        1. Environment variables
        2. Config file (explicit path or auto-discovered)
        3. Built-in defaults

    Args:
        config_file: Optional explicit path to a YAML configuration file.

    Returns:
        A fully populated :class:`AppConfig` instance.
    """
    file_data: dict[str, Any] = {}

    path = config_file or _find_config_file()
    if path is not None:
        file_data = _load_yaml_file(path)
        logger.info("Loaded configuration from %s", path)
    else:
        logger.debug("No configuration file found; using defaults and environment variables.")

    raw_thresholds: dict[str, Any] = file_data.get("thresholds", {})

    thresholds = ThresholdConfig(
        cpu_warning=_env_int(
            "CPU_WARNING", int(raw_thresholds.get("cpu_warning", DEFAULT_CPU_WARNING))
        ),
        cpu_critical=_env_int(
            "CPU_CRITICAL", int(raw_thresholds.get("cpu_critical", DEFAULT_CPU_CRITICAL))
        ),
        memory_warning=_env_int(
            "MEMORY_WARNING", int(raw_thresholds.get("memory_warning", DEFAULT_MEMORY_WARNING))
        ),
        memory_critical=_env_int(
            "MEMORY_CRITICAL", int(raw_thresholds.get("memory_critical", DEFAULT_MEMORY_CRITICAL))
        ),
        disk_warning=_env_int(
            "DISK_WARNING", int(raw_thresholds.get("disk_warning", DEFAULT_DISK_WARNING))
        ),
        disk_critical=_env_int(
            "DISK_CRITICAL", int(raw_thresholds.get("disk_critical", DEFAULT_DISK_CRITICAL))
        ),
        load_warning=_env_float(
            "LOAD_WARNING", float(raw_thresholds.get("load_warning", DEFAULT_LOAD_WARNING))
        ),
        load_critical=_env_float(
            "LOAD_CRITICAL", float(raw_thresholds.get("load_critical", DEFAULT_LOAD_CRITICAL))
        ),
    )

    try:
        thresholds.validate()
    except ValueError as exc:
        logger.error("Invalid thresholds in configuration: %s", exc)
        raise

    services_from_file: list[str] = file_data.get("services", list(DEFAULT_SERVICES))
    services_from_env_raw = _env("SERVICES")
    services: list[str] = (
        [s.strip() for s in services_from_env_raw.split(",") if s.strip()]
        if services_from_env_raw
        else services_from_file
    )

    top_processes = _env_int(
        "TOP_PROCESSES",
        int(file_data.get("top_processes", DEFAULT_TOP_PROCESSES)),
    )

    log_level = _env("LOG_LEVEL", str(file_data.get("log_level", "INFO"))).upper()

    return AppConfig(
        thresholds=thresholds,
        top_processes=top_processes,
        services=services,
        log_level=log_level,
    )
