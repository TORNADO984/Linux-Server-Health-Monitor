"""Process metrics collector.

Lists top processes by CPU and memory consumption using psutil.
Process information is collected carefully to avoid permission errors
when querying other users' processes.
"""

from __future__ import annotations

import contextlib
import logging

import psutil

from server_health.models.health import HealthStatus, ProcessInfo, ProcessMetrics

logger = logging.getLogger(__name__)

# Fields to request from psutil to minimise system calls
_PROC_ATTRS = ["pid", "name", "username", "cpu_percent", "memory_percent", "status", "cmdline"]


def collect_processes(top_n: int = 5) -> ProcessMetrics:
    """Collect process statistics and identify top resource consumers.

    Args:
        top_n: Number of top processes to return for each ranking (CPU, memory).

    Returns:
        A populated :class:`ProcessMetrics` instance.
    """
    logger.debug("Collecting process metrics (top_n=%d)", top_n)

    all_procs: list[dict] = []
    total = running = sleeping = zombie = 0

    # Initialise CPU percent measurement so the second call returns meaningful data.
    try:
        for proc in psutil.process_iter(["pid", "cpu_percent"]):
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                proc.cpu_percent(interval=None)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed initial CPU percent measurement: %s", exc)

    for proc in psutil.process_iter(_PROC_ATTRS):
        try:
            info = proc.as_dict(attrs=_PROC_ATTRS, ad_value=None)
            total += 1
            proc_status = str(info.get("status") or "")
            if proc_status == psutil.STATUS_RUNNING:
                running += 1
            elif proc_status == psutil.STATUS_SLEEPING:
                sleeping += 1
            elif proc_status == psutil.STATUS_ZOMBIE:
                zombie += 1
            all_procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            total += 1  # count it even if we can't read it

    top_by_cpu = _top_processes(all_procs, key="cpu_percent", n=top_n)
    top_by_mem = _top_processes(all_procs, key="memory_percent", n=top_n)

    metrics = ProcessMetrics(
        total_count=total,
        running_count=running,
        sleeping_count=sleeping,
        zombie_count=zombie,
        top_by_cpu=top_by_cpu,
        top_by_memory=top_by_mem,
        status=HealthStatus.UNKNOWN,
    )

    logger.debug(
        "Process metrics: total=%d, running=%d, sleeping=%d, zombies=%d",
        total,
        running,
        sleeping,
        zombie,
    )
    return metrics


def _top_processes(procs: list[dict], key: str, n: int) -> list[ProcessInfo]:
    """Return the top *n* processes sorted descending by *key*."""
    valid = [p for p in procs if p.get(key) is not None]
    valid.sort(key=lambda p: p[key] or 0.0, reverse=True)

    result: list[ProcessInfo] = []
    for info in valid[:n]:
        cmdline_raw = info.get("cmdline")
        if isinstance(cmdline_raw, list):
            cmdline = " ".join(cmdline_raw)[:200]
        else:
            cmdline = str(cmdline_raw or "")[:200]

        result.append(
            ProcessInfo(
                pid=int(info.get("pid") or 0),
                name=str(info.get("name") or "unknown"),
                username=str(info.get("username") or "unknown"),
                cpu_percent=float(info.get("cpu_percent") or 0.0),
                memory_percent=float(info.get("memory_percent") or 0.0),
                status=str(info.get("status") or "unknown"),
                cmdline=cmdline,
            )
        )
    return result
