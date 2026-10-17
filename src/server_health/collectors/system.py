"""System information collector.

Gathers hostname, OS details, kernel version, architecture, and uptime
using Python standard library calls and psutil where available.
"""

from __future__ import annotations

import logging
import platform
import socket
from datetime import datetime

import psutil

from server_health.models.health import SystemInfo

logger = logging.getLogger(__name__)


def collect_system() -> SystemInfo:
    """Collect operating system and hardware metadata.

    Returns:
        A populated :class:`SystemInfo` instance.

    Raises:
        Never raises; errors are logged and sensible fallback values are used.
    """
    logger.debug("Collecting system information")

    hostname = _safe_hostname()
    os_name = _safe_os_name()
    kernel_version = _safe_kernel_version()
    architecture = platform.machine() or "unknown"
    boot_time, uptime_seconds = _safe_uptime()

    info = SystemInfo(
        hostname=hostname,
        os_name=os_name,
        kernel_version=kernel_version,
        architecture=architecture,
        uptime_seconds=uptime_seconds,
        boot_time=boot_time,
        collected_at=datetime.now(),
    )

    logger.debug(
        "System info collected: hostname=%s, os=%s, uptime=%.0fs",
        info.hostname,
        info.os_name,
        info.uptime_seconds,
    )
    return info


def _safe_hostname() -> str:
    try:
        return socket.gethostname()
    except OSError as exc:
        logger.warning("Could not determine hostname: %s", exc)
        return "unknown"


def _safe_os_name() -> str:
    try:
        # On Linux, platform.freedesktop_os_release() gives a richer name.
        release_info = platform.freedesktop_os_release()
        return release_info.get("PRETTY_NAME") or release_info.get("NAME", "Linux")
    except (AttributeError, OSError):
        pass
    try:
        dist = platform.platform(terse=False)
        return dist
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not determine OS name: %s", exc)
        return "Unknown OS"


def _safe_kernel_version() -> str:
    try:
        return platform.release()
    except OSError as exc:
        logger.warning("Could not determine kernel version: %s", exc)
        return "unknown"


def _safe_uptime() -> tuple[datetime, float]:
    try:
        boot_ts = psutil.boot_time()
        boot_dt = datetime.fromtimestamp(boot_ts)
        uptime = (datetime.now() - boot_dt).total_seconds()
        return boot_dt, uptime
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not determine uptime: %s", exc)
        return datetime.now(), 0.0
