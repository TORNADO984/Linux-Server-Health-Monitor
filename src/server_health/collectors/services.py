"""Systemd services collector.

Checks the status of a configurable list of Linux services via
`systemctl is-active`. Falls back gracefully when systemd is not
available (e.g. inside containers or on non-systemd systems).

Security note: service names are validated against a strict allowlist
pattern before being passed to subprocess to prevent injection.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess

from server_health.models.health import HealthStatus, ServiceInfo, ServiceMetrics

logger = logging.getLogger(__name__)

# Strict regex: service names may only contain alphanumeric chars, hyphens,
# underscores, and dots. This prevents any form of shell injection.
_SAFE_SERVICE_NAME = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")

SYSTEMCTL_PATH = shutil.which("systemctl")


def collect_services(service_names: list[str]) -> ServiceMetrics:
    """Check the active status of the given systemd services.

    Args:
        service_names: List of service names to check (e.g. ["ssh", "docker"]).

    Returns:
        A populated :class:`ServiceMetrics` instance.
    """
    logger.debug("Collecting service metrics for: %s", service_names)

    if SYSTEMCTL_PATH is None:
        logger.warning("systemctl not found; skipping service checks.")
        return ServiceMetrics(
            services=[],
            systemd_available=False,
            status=HealthStatus.UNKNOWN,
        )

    services: list[ServiceInfo] = []
    for name in service_names:
        info = _check_service(name)
        if info is not None:
            services.append(info)

    logger.debug("Collected status for %d services", len(services))
    return ServiceMetrics(
        services=services,
        systemd_available=True,
        status=HealthStatus.UNKNOWN,
    )


def _check_service(name: str) -> ServiceInfo | None:
    """Query systemd for the status of a single service.

    Args:
        name: The service unit name (e.g. "ssh" or "nginx").

    Returns:
        A :class:`ServiceInfo` or None if the service does not exist.
    """
    if not _SAFE_SERVICE_NAME.match(name):
        logger.warning("Skipping service with invalid name: %r", name)
        return None

    active_status = _run_systemctl("is-active", name)
    if active_status is None:
        return None  # systemctl itself failed; already logged

    if active_status == "not-found" or active_status.startswith("not-found"):
        logger.debug("Service not found: %s", name)
        return None  # Don't report services that don't exist at all

    is_active = active_status == "active"
    enabled_status = _run_systemctl("is-enabled", name)
    enabled: bool | None = None
    if enabled_status is not None:
        enabled = enabled_status == "enabled"

    info = ServiceInfo(
        name=name,
        active=is_active,
        status=active_status,
        enabled=enabled,
    )
    logger.debug("Service %s: active=%s, status=%s", name, is_active, active_status)
    return info


def _run_systemctl(command: str, unit: str) -> str | None:
    """Run `systemctl <command> <unit>` and return the stdout output.

    Args:
        command: A safe systemctl sub-command (e.g. "is-active").
        unit: The validated unit name.

    Returns:
        Stripped stdout string, or None if the command could not be executed.
    """
    assert SYSTEMCTL_PATH is not None  # guarded by caller

    try:
        result = subprocess.run(  # noqa: S603
            [SYSTEMCTL_PATH, command, unit],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip() or result.stderr.strip() or "unknown"
    except subprocess.TimeoutExpired:
        logger.warning("Timeout querying systemctl %s %s", command, unit)
        return None
    except OSError as exc:
        logger.warning("Could not run systemctl %s %s: %s", command, unit, exc)
        return None
