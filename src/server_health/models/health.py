"""Data models for server health metrics and overall health status.

Uses Python dataclasses for lightweight, type-safe structured data.
All models are serialisable to plain dictionaries for JSON output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class HealthStatus(StrEnum):
    """Represents the evaluated health of a metric or subsystem."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

    @property
    def exit_code(self) -> int:
        """Map status to a POSIX exit code."""
        return {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 1,
            HealthStatus.CRITICAL: 2,
            HealthStatus.UNKNOWN: 3,
        }[self]

    def worse_than(self, other: HealthStatus) -> bool:
        """Return True if this status is more severe than *other*."""
        order = [
            HealthStatus.HEALTHY,
            HealthStatus.UNKNOWN,
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
        ]
        return order.index(self) > order.index(other)


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------


@dataclass
class SystemInfo:
    """Basic operating-system and hardware information."""

    hostname: str
    os_name: str
    kernel_version: str
    architecture: str
    uptime_seconds: float
    boot_time: datetime
    collected_at: datetime = field(default_factory=datetime.now)

    @property
    def uptime_human(self) -> str:
        """Human-readable uptime string (e.g. '3 days, 14 hours, 5 minutes')."""
        total_seconds = int(self.uptime_seconds)
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        parts: list[str] = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes or not parts:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        return ", ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "os_name": self.os_name,
            "kernel_version": self.kernel_version,
            "architecture": self.architecture,
            "uptime_seconds": self.uptime_seconds,
            "uptime_human": self.uptime_human,
            "boot_time": self.boot_time.isoformat(),
            "collected_at": self.collected_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------


@dataclass
class CpuMetrics:
    """CPU usage and load statistics."""

    usage_percent: float
    core_count: int
    logical_count: int
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "usage_percent": round(self.usage_percent, 1),
            "core_count": self.core_count,
            "logical_count": self.logical_count,
            "load_avg_1m": round(self.load_avg_1m, 2),
            "load_avg_5m": round(self.load_avg_5m, 2),
            "load_avg_15m": round(self.load_avg_15m, 2),
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


@dataclass
class MemoryMetrics:
    """Physical memory (RAM) and swap statistics."""

    total_bytes: int
    available_bytes: int
    used_bytes: int
    usage_percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_usage_percent: float
    status: HealthStatus = HealthStatus.UNKNOWN

    @property
    def total_gb(self) -> float:
        return round(self.total_bytes / 1024**3, 2)

    @property
    def used_gb(self) -> float:
        return round(self.used_bytes / 1024**3, 2)

    @property
    def available_gb(self) -> float:
        return round(self.available_bytes / 1024**3, 2)

    @property
    def swap_total_gb(self) -> float:
        return round(self.swap_total_bytes / 1024**3, 2)

    @property
    def swap_used_gb(self) -> float:
        return round(self.swap_used_bytes / 1024**3, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_bytes": self.total_bytes,
            "total_gb": self.total_gb,
            "used_bytes": self.used_bytes,
            "used_gb": self.used_gb,
            "available_bytes": self.available_bytes,
            "available_gb": self.available_gb,
            "usage_percent": round(self.usage_percent, 1),
            "swap_total_bytes": self.swap_total_bytes,
            "swap_total_gb": self.swap_total_gb,
            "swap_used_bytes": self.swap_used_bytes,
            "swap_used_gb": self.swap_used_gb,
            "swap_usage_percent": round(self.swap_usage_percent, 1),
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------


@dataclass
class DiskPartition:
    """Metrics for a single mounted filesystem."""

    mountpoint: str
    device: str
    filesystem_type: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float
    status: HealthStatus = HealthStatus.UNKNOWN

    @property
    def total_gb(self) -> float:
        return round(self.total_bytes / 1024**3, 2)

    @property
    def used_gb(self) -> float:
        return round(self.used_bytes / 1024**3, 2)

    @property
    def free_gb(self) -> float:
        return round(self.free_bytes / 1024**3, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mountpoint": self.mountpoint,
            "device": self.device,
            "filesystem_type": self.filesystem_type,
            "total_bytes": self.total_bytes,
            "total_gb": self.total_gb,
            "used_bytes": self.used_bytes,
            "used_gb": self.used_gb,
            "free_bytes": self.free_bytes,
            "free_gb": self.free_gb,
            "usage_percent": round(self.usage_percent, 1),
            "status": self.status.value,
        }


@dataclass
class DiskMetrics:
    """Aggregated disk metrics across all important partitions."""

    partitions: list[DiskPartition] = field(default_factory=list)
    status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "partitions": [p.to_dict() for p in self.partitions],
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------


@dataclass
class NetworkInterface:
    """A single network interface with addresses and traffic counters."""

    name: str
    ip_addresses: list[str]
    mac_address: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    is_up: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ip_addresses": self.ip_addresses,
            "mac_address": self.mac_address,
            "bytes_sent": self.bytes_sent,
            "bytes_recv": self.bytes_recv,
            "packets_sent": self.packets_sent,
            "packets_recv": self.packets_recv,
            "is_up": self.is_up,
        }


@dataclass
class NetworkMetrics:
    """Aggregated network metrics."""

    interfaces: list[NetworkInterface] = field(default_factory=list)
    status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "interfaces": [i.to_dict() for i in self.interfaces],
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Processes
# ---------------------------------------------------------------------------


@dataclass
class ProcessInfo:
    """Snapshot of a single process."""

    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str
    cmdline: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "username": self.username,
            "cpu_percent": round(self.cpu_percent, 1),
            "memory_percent": round(self.memory_percent, 1),
            "status": self.status,
            "cmdline": self.cmdline,
        }


@dataclass
class ProcessMetrics:
    """Top processes and aggregate process counts."""

    total_count: int
    running_count: int
    sleeping_count: int
    zombie_count: int
    top_by_cpu: list[ProcessInfo] = field(default_factory=list)
    top_by_memory: list[ProcessInfo] = field(default_factory=list)
    status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_count": self.total_count,
            "running_count": self.running_count,
            "sleeping_count": self.sleeping_count,
            "zombie_count": self.zombie_count,
            "top_by_cpu": [p.to_dict() for p in self.top_by_cpu],
            "top_by_memory": [p.to_dict() for p in self.top_by_memory],
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


@dataclass
class ServiceInfo:
    """Status of a single systemd service."""

    name: str
    active: bool
    status: str  # active/inactive/failed/unknown
    enabled: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "active": self.active,
            "status": self.status,
            "enabled": self.enabled,
        }


@dataclass
class ServiceMetrics:
    """Aggregated service health."""

    services: list[ServiceInfo] = field(default_factory=list)
    systemd_available: bool = True
    status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "systemd_available": self.systemd_available,
            "services": [s.to_dict() for s in self.services],
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------


@dataclass
class DockerMetrics:
    """Docker daemon status and container counts."""

    installed: bool
    running: bool
    total_containers: int = 0
    running_containers: int = 0
    stopped_containers: int = 0
    paused_containers: int = 0
    images_count: int = 0
    docker_version: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "installed": self.installed,
            "running": self.running,
            "total_containers": self.total_containers,
            "running_containers": self.running_containers,
            "stopped_containers": self.stopped_containers,
            "paused_containers": self.paused_containers,
            "images_count": self.images_count,
            "docker_version": self.docker_version,
            "status": self.status.value,
        }


# ---------------------------------------------------------------------------
# Overall health report
# ---------------------------------------------------------------------------


@dataclass
class HealthReport:
    """Complete server health report aggregating all subsystem metrics."""

    system: SystemInfo
    cpu: CpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics
    processes: ProcessMetrics
    services: ServiceMetrics
    docker: DockerMetrics
    overall_status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system.to_dict(),
            "cpu": self.cpu.to_dict(),
            "memory": self.memory.to_dict(),
            "disk": self.disk.to_dict(),
            "network": self.network.to_dict(),
            "processes": self.processes.to_dict(),
            "services": self.services.to_dict(),
            "docker": self.docker.to_dict(),
            "overall_status": self.overall_status.value,
        }
