"""Memory metrics collector.

Uses psutil to collect RAM and swap usage statistics.
"""

from __future__ import annotations

import logging

import psutil

from server_health.models.health import HealthStatus, MemoryMetrics

logger = logging.getLogger(__name__)


def collect_memory() -> MemoryMetrics:
    """Collect physical memory and swap usage statistics.

    Returns:
        A populated :class:`MemoryMetrics` instance with status=UNKNOWN.
        Callers should apply threshold evaluation to set the status.
    """
    logger.debug("Collecting memory metrics")

    ram = _safe_virtual_memory()
    swap = _safe_swap_memory()

    metrics = MemoryMetrics(
        total_bytes=ram.total,
        available_bytes=ram.available,
        used_bytes=ram.used,
        usage_percent=ram.percent,
        swap_total_bytes=swap.total,
        swap_used_bytes=swap.used,
        swap_usage_percent=swap.percent,
        status=HealthStatus.UNKNOWN,
    )

    logger.debug(
        "Memory metrics: usage=%.1f%% (%s GB used / %s GB total), swap=%.1f%%",
        metrics.usage_percent,
        metrics.used_gb,
        metrics.total_gb,
        metrics.swap_usage_percent,
    )
    return metrics


class _MemoryFallback:
    """Fallback object when psutil.virtual_memory() fails."""

    total: int = 0
    available: int = 0
    used: int = 0
    percent: float = 0.0


class _SwapFallback:
    """Fallback object when psutil.swap_memory() fails."""

    total: int = 0
    used: int = 0
    percent: float = 0.0


def _safe_virtual_memory() -> psutil._common.sswap | _MemoryFallback:  # type: ignore[name-defined]
    try:
        return psutil.virtual_memory()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not collect RAM metrics: %s", exc)
        return _MemoryFallback()


def _safe_swap_memory() -> psutil._common.sswap | _SwapFallback:  # type: ignore[name-defined]
    try:
        return psutil.swap_memory()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not collect swap metrics: %s", exc)
        return _SwapFallback()
