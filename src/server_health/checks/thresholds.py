"""Threshold evaluation for health metrics.

Applies configurable warning/critical thresholds to raw metric values
and returns HealthStatus enumerations. This module is pure Python with
no I/O side-effects, making it easy to unit-test.
"""

from __future__ import annotations

import logging

from server_health.config import ThresholdConfig
from server_health.models.health import (
    CpuMetrics,
    DiskMetrics,
    DockerMetrics,
    HealthReport,
    HealthStatus,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    ServiceMetrics,
)

logger = logging.getLogger(__name__)


def _classify(value: float, warning: float, critical: float) -> HealthStatus:
    """Classify a numeric value into a :class:`HealthStatus`.

    Args:
        value: The measured metric value.
        warning: Threshold at or above which the status becomes WARNING.
        critical: Threshold at or above which the status becomes CRITICAL.

    Returns:
        HEALTHY, WARNING, or CRITICAL.
    """
    if value >= critical:
        return HealthStatus.CRITICAL
    if value >= warning:
        return HealthStatus.WARNING
    return HealthStatus.HEALTHY


def evaluate_cpu(metrics: CpuMetrics, thresholds: ThresholdConfig) -> CpuMetrics:
    """Evaluate CPU metrics and set the status field.

    Args:
        metrics: Raw CPU metrics (status will be overwritten).
        thresholds: Configured threshold values.

    Returns:
        The same *metrics* instance with status set.
    """
    status = _classify(
        metrics.usage_percent,
        thresholds.cpu_warning,
        thresholds.cpu_critical,
    )
    # Also factor in load average relative to core count.
    if metrics.logical_count > 0:
        load_per_core = metrics.load_avg_1m / metrics.logical_count
        load_status = _classify(
            load_per_core * 100,
            thresholds.load_warning * 100,
            thresholds.load_critical * 100,
        )
        if load_status.worse_than(status):
            status = load_status

    metrics.status = status
    logger.debug(
        "CPU status: %s (usage=%.1f%%, load_1m=%.2f)",
        status.value,
        metrics.usage_percent,
        metrics.load_avg_1m,
    )
    return metrics


def evaluate_memory(metrics: MemoryMetrics, thresholds: ThresholdConfig) -> MemoryMetrics:
    """Evaluate memory metrics and set the status field.

    Args:
        metrics: Raw memory metrics (status will be overwritten).
        thresholds: Configured threshold values.

    Returns:
        The same *metrics* instance with status set.
    """
    status = _classify(
        metrics.usage_percent,
        thresholds.memory_warning,
        thresholds.memory_critical,
    )
    metrics.status = status
    logger.debug(
        "Memory status: %s (usage=%.1f%%)",
        status.value,
        metrics.usage_percent,
    )
    return metrics


def evaluate_disk(metrics: DiskMetrics, thresholds: ThresholdConfig) -> DiskMetrics:
    """Evaluate disk metrics; sets status on each partition and the aggregate.

    Args:
        metrics: Raw disk metrics (statuses will be overwritten).
        thresholds: Configured threshold values.

    Returns:
        The same *metrics* instance with statuses set.
    """
    worst = HealthStatus.HEALTHY

    for partition in metrics.partitions:
        pstatus = _classify(
            partition.usage_percent,
            thresholds.disk_warning,
            thresholds.disk_critical,
        )
        partition.status = pstatus
        if pstatus.worse_than(worst):
            worst = pstatus
        logger.debug(
            "Disk %s status: %s (%.1f%%)",
            partition.mountpoint,
            pstatus.value,
            partition.usage_percent,
        )

    metrics.status = worst if metrics.partitions else HealthStatus.UNKNOWN
    return metrics


def evaluate_network(metrics: NetworkMetrics) -> NetworkMetrics:
    """Evaluate network metrics.

    Currently marks status as HEALTHY if any interface is up, UNKNOWN otherwise.
    Future versions could add packet-error-rate checks.

    Args:
        metrics: Raw network metrics.

    Returns:
        The same *metrics* instance with status set.
    """
    if any(i.is_up for i in metrics.interfaces):
        metrics.status = HealthStatus.HEALTHY
    elif metrics.interfaces:
        metrics.status = HealthStatus.WARNING
    else:
        metrics.status = HealthStatus.UNKNOWN
    return metrics


def evaluate_processes(metrics: ProcessMetrics) -> ProcessMetrics:
    """Evaluate process metrics.

    Flags WARNING if zombie processes are detected.

    Args:
        metrics: Raw process metrics.

    Returns:
        The same *metrics* instance with status set.
    """
    if metrics.zombie_count > 0:
        metrics.status = HealthStatus.WARNING
        logger.warning("Zombie processes detected: %d", metrics.zombie_count)
    else:
        metrics.status = HealthStatus.HEALTHY
    return metrics


def evaluate_services(metrics: ServiceMetrics) -> ServiceMetrics:
    """Evaluate service metrics.

    Marks WARNING if any configured service is inactive/failed.

    Args:
        metrics: Raw service metrics.

    Returns:
        The same *metrics* instance with status set.
    """
    if not metrics.systemd_available:
        metrics.status = HealthStatus.UNKNOWN
        return metrics

    failed = [s for s in metrics.services if s.status == "failed"]
    inactive = [s for s in metrics.services if not s.active and s.status != "failed"]

    if failed:
        metrics.status = HealthStatus.WARNING
        logger.warning("Failed services: %s", [s.name for s in failed])
    elif inactive:
        metrics.status = HealthStatus.HEALTHY  # inactive services are not errors by default
    else:
        metrics.status = HealthStatus.HEALTHY

    return metrics


def evaluate_docker(metrics: DockerMetrics) -> DockerMetrics:
    """Evaluate Docker metrics.

    Args:
        metrics: Raw docker metrics.

    Returns:
        The same *metrics* instance with status set.
    """
    if not metrics.installed:
        metrics.status = HealthStatus.UNKNOWN
    elif not metrics.running:
        metrics.status = HealthStatus.WARNING
        logger.warning("Docker daemon is not running.")
    else:
        metrics.status = HealthStatus.HEALTHY
    return metrics


def evaluate_overall(report: HealthReport) -> HealthReport:
    """Compute the overall health status from all subsystem statuses.

    The overall status is the worst of all individual statuses,
    excluding UNKNOWN statuses from the aggregate.

    Args:
        report: A :class:`HealthReport` with all subsystem statuses already set.

    Returns:
        The same *report* instance with ``overall_status`` set.
    """
    statuses = [
        report.cpu.status,
        report.memory.status,
        report.disk.status,
        report.network.status,
        report.processes.status,
        report.services.status,
        report.docker.status,
    ]

    # Filter out UNKNOWN; only count evaluated statuses.
    known = [s for s in statuses if s != HealthStatus.UNKNOWN]

    if not known:
        report.overall_status = HealthStatus.UNKNOWN
    elif any(s == HealthStatus.CRITICAL for s in known):
        report.overall_status = HealthStatus.CRITICAL
    elif any(s == HealthStatus.WARNING for s in known):
        report.overall_status = HealthStatus.WARNING
    else:
        report.overall_status = HealthStatus.HEALTHY

    logger.info("Overall server health status: %s", report.overall_status.value.upper())
    return report
