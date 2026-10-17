"""CPU metrics collector.

Uses psutil to gather CPU usage percentage, core counts, and load averages.
Falls back gracefully when information is unavailable.
"""

from __future__ import annotations

import logging
import os

import psutil

from server_health.models.health import CpuMetrics, HealthStatus

logger = logging.getLogger(__name__)


def collect_cpu(interval: float = 1.0) -> CpuMetrics:
    """Collect CPU usage and load statistics.

    Args:
        interval: Sampling interval in seconds for cpu_percent measurement.
                  Set to 0 to get a non-blocking measurement using the last
                  cached value (less accurate but instant).

    Returns:
        A populated :class:`CpuMetrics` instance with status=UNKNOWN.
        Callers should apply threshold evaluation to set the status.
    """
    logger.debug("Collecting CPU metrics (interval=%.1fs)", interval)

    usage_percent = _safe_cpu_percent(interval)
    core_count = _safe_cpu_count(logical=False)
    logical_count = _safe_cpu_count(logical=True)
    load_avg_1m, load_avg_5m, load_avg_15m = _safe_load_avg()

    metrics = CpuMetrics(
        usage_percent=usage_percent,
        core_count=core_count,
        logical_count=logical_count,
        load_avg_1m=load_avg_1m,
        load_avg_5m=load_avg_5m,
        load_avg_15m=load_avg_15m,
        status=HealthStatus.UNKNOWN,
    )

    logger.debug(
        "CPU metrics: usage=%.1f%%, cores=%d, load=%.2f/%.2f/%.2f",
        metrics.usage_percent,
        metrics.core_count,
        metrics.load_avg_1m,
        metrics.load_avg_5m,
        metrics.load_avg_15m,
    )
    return metrics


def _safe_cpu_percent(interval: float) -> float:
    try:
        pct = psutil.cpu_percent(interval=interval if interval > 0 else None)
        return float(pct)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not measure CPU usage: %s", exc)
        return 0.0


def _safe_cpu_count(logical: bool) -> int:
    try:
        count = psutil.cpu_count(logical=logical)
        return count if count is not None else 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not determine CPU count (logical=%s): %s", logical, exc)
        return 1


def _safe_load_avg() -> tuple[float, float, float]:
    """Return the 1, 5, and 15-minute load averages."""
    try:
        # getloadavg() is available on Unix/Linux; not on Windows.
        load = os.getloadavg()
        return load[0], load[1], load[2]
    except (AttributeError, OSError):
        # Windows or unsupported platform – return zeros.
        logger.debug("Load average not available on this platform.")
        return 0.0, 0.0, 0.0
