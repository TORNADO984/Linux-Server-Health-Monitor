"""Disk metrics collector.

Collects usage statistics for all real, mounted filesystems.
Skips pseudo-filesystems (tmpfs, devtmpfs, etc.) and handles
permission errors gracefully.
"""

from __future__ import annotations

import logging

import psutil

from server_health.models.health import DiskMetrics, DiskPartition, HealthStatus

logger = logging.getLogger(__name__)

# Filesystem types that carry no useful disk usage data
_PSEUDO_FS_TYPES = frozenset(
    {
        "tmpfs",
        "devtmpfs",
        "devfs",
        "proc",
        "sysfs",
        "cgroup",
        "cgroup2",
        "pstore",
        "bpf",
        "debugfs",
        "tracefs",
        "securityfs",
        "fusectl",
        "hugetlbfs",
        "mqueue",
        "ramfs",
        "overlay",
        "squashfs",
        "autofs",
        "efivarfs",
    }
)

# Mountpoint prefixes that are typically uninteresting
_SKIP_MOUNTPOINTS = ("/proc", "/sys", "/dev", "/run")


def collect_disk() -> DiskMetrics:
    """Collect disk usage for all important mounted filesystems.

    Returns:
        A populated :class:`DiskMetrics` instance. Individual partition
        statuses are set to UNKNOWN; callers should apply threshold evaluation.
    """
    logger.debug("Collecting disk metrics")

    partitions: list[DiskPartition] = []

    try:
        all_parts = psutil.disk_partitions(all=False)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to enumerate disk partitions: %s", exc)
        return DiskMetrics(partitions=[], status=HealthStatus.UNKNOWN)

    seen_devices: set[str] = set()

    for part in all_parts:
        if _should_skip(part, seen_devices):
            continue

        seen_devices.add(part.device)

        usage = _safe_disk_usage(part.mountpoint)
        if usage is None:
            continue

        partition = DiskPartition(
            mountpoint=part.mountpoint,
            device=part.device,
            filesystem_type=part.fstype,
            total_bytes=usage.total,
            used_bytes=usage.used,
            free_bytes=usage.free,
            usage_percent=usage.percent,
            status=HealthStatus.UNKNOWN,
        )
        partitions.append(partition)
        logger.debug(
            "Disk partition: %s (%s) %.1f%% used",
            part.mountpoint,
            part.fstype,
            usage.percent,
        )

    logger.debug("Collected metrics for %d disk partitions", len(partitions))
    return DiskMetrics(partitions=partitions, status=HealthStatus.UNKNOWN)


def _should_skip(part: psutil._common.sdiskpart, seen_devices: set[str]) -> bool:  # type: ignore[name-defined]
    """Determine whether a partition should be skipped."""
    if part.fstype.lower() in _PSEUDO_FS_TYPES:
        return True
    for prefix in _SKIP_MOUNTPOINTS:
        if part.mountpoint.startswith(prefix):
            return True
    # Skip duplicate device entries (e.g. bind mounts reporting the same device)
    return bool(part.device and part.device in seen_devices)


def _safe_disk_usage(mountpoint: str) -> psutil._common.sdiskusage | None:  # type: ignore[name-defined]
    """Return disk usage for *mountpoint*, or None on error."""
    try:
        return psutil.disk_usage(mountpoint)
    except PermissionError:
        logger.warning("Permission denied reading disk usage for %s", mountpoint)
        return None
    except FileNotFoundError:
        logger.warning("Mountpoint no longer exists: %s", mountpoint)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read disk usage for %s: %s", mountpoint, exc)
        return None
