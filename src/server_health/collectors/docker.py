"""Docker metrics collector.

Detects Docker installation and collects container/image statistics.
Uses the `docker` CLI via subprocess rather than the Docker SDK to
avoid an optional heavy dependency. The Docker SDK is optional.

Never crashes if Docker is not installed or not running.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess

from server_health.models.health import DockerMetrics, HealthStatus

logger = logging.getLogger(__name__)

DOCKER_PATH = shutil.which("docker")


def collect_docker() -> DockerMetrics:
    """Detect Docker and collect container/image statistics.

    Returns:
        A :class:`DockerMetrics` instance. If Docker is not installed,
        ``installed=False`` is returned. If Docker is installed but not
        running, ``running=False``.
    """
    logger.debug("Collecting Docker metrics")

    if DOCKER_PATH is None:
        logger.info("Docker is not installed (docker binary not found in PATH).")
        return DockerMetrics(
            installed=False,
            running=False,
            status=HealthStatus.UNKNOWN,
        )

    version = _get_docker_version()
    if version is None:
        logger.warning("Docker is installed but the daemon does not appear to be running.")
        return DockerMetrics(
            installed=True,
            running=False,
            status=HealthStatus.UNKNOWN,
        )

    containers = _get_container_counts()
    images_count = _get_image_count()

    metrics = DockerMetrics(
        installed=True,
        running=True,
        total_containers=containers["total"],
        running_containers=containers["running"],
        stopped_containers=containers["stopped"],
        paused_containers=containers["paused"],
        images_count=images_count,
        docker_version=version,
        status=HealthStatus.UNKNOWN,
    )

    logger.debug(
        "Docker metrics: version=%s, containers=%d (running=%d, stopped=%d)",
        version,
        metrics.total_containers,
        metrics.running_containers,
        metrics.stopped_containers,
    )
    return metrics


def _run_docker(*args: str, timeout: int = 10) -> subprocess.CompletedProcess | None:
    """Run a docker sub-command safely without shell interpretation.

    Args:
        *args: Arguments to pass to docker (e.g. "info", "--format", "{{json .}}").
        timeout: Maximum seconds to wait.

    Returns:
        CompletedProcess or None on failure.
    """
    assert DOCKER_PATH is not None

    try:
        result = subprocess.run(  # noqa: S603
            [DOCKER_PATH, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result
    except subprocess.TimeoutExpired:
        logger.warning("Docker command timed out: docker %s", " ".join(args))
        return None
    except OSError as exc:
        logger.warning("Failed to run docker %s: %s", " ".join(args), exc)
        return None


def _get_docker_version() -> str | None:
    """Return the Docker daemon version string or None if not reachable."""
    result = _run_docker("version", "--format", "{{.Server.Version}}", timeout=5)
    if result is None or result.returncode != 0:
        return None
    version = result.stdout.strip()
    return version or None


def _get_container_counts() -> dict[str, int]:
    """Return a dict with container counts by state."""
    defaults: dict[str, int] = {"total": 0, "running": 0, "stopped": 0, "paused": 0}

    result = _run_docker(
        "ps",
        "--all",
        "--format",
        '{"State":"{{.State}}"}',
        timeout=10,
    )
    if result is None or result.returncode != 0:
        return defaults

    total = running = stopped = paused = 0
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            state = obj.get("State", "").lower()
            total += 1
            if state == "running":
                running += 1
            elif state in ("exited", "created", "dead", "removing"):
                stopped += 1
            elif state == "paused":
                paused += 1
            else:
                stopped += 1
        except json.JSONDecodeError as exc:
            logger.debug("Could not parse docker ps output line %r: %s", line, exc)

    return {"total": total, "running": running, "stopped": stopped, "paused": paused}


def _get_image_count() -> int:
    """Return the number of locally available Docker images."""
    result = _run_docker("images", "--quiet", timeout=10)
    if result is None or result.returncode != 0:
        return 0
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    return len(lines)
