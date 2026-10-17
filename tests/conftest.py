"""Shared pytest fixtures for Server Health Monitor tests."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Ensure src/ is on sys.path for test execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from server_health.config import AppConfig, ThresholdConfig
from server_health.models.health import (
    CpuMetrics,
    DiskMetrics,
    DiskPartition,
    DockerMetrics,
    HealthReport,
    HealthStatus,
    MemoryMetrics,
    NetworkInterface,
    NetworkMetrics,
    ProcessInfo,
    ProcessMetrics,
    ServiceInfo,
    ServiceMetrics,
    SystemInfo,
)


@pytest.fixture
def default_thresholds() -> ThresholdConfig:
    """Return a ThresholdConfig with default values."""
    return ThresholdConfig()


@pytest.fixture
def strict_thresholds() -> ThresholdConfig:
    """Return very strict thresholds (easy to trigger)."""
    return ThresholdConfig(
        cpu_warning=10,
        cpu_critical=20,
        memory_warning=10,
        memory_critical=20,
        disk_warning=10,
        disk_critical=20,
        load_warning=0.1,
        load_critical=0.5,
    )


@pytest.fixture
def default_config() -> AppConfig:
    """Return a default AppConfig."""
    return AppConfig()


@pytest.fixture
def healthy_cpu() -> CpuMetrics:
    return CpuMetrics(
        usage_percent=5.0,
        core_count=4,
        logical_count=8,
        load_avg_1m=0.5,
        load_avg_5m=0.4,
        load_avg_15m=0.3,
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def warning_cpu() -> CpuMetrics:
    return CpuMetrics(
        usage_percent=75.0,
        core_count=4,
        logical_count=8,
        load_avg_1m=1.5,
        load_avg_5m=1.2,
        load_avg_15m=1.0,
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def critical_cpu() -> CpuMetrics:
    return CpuMetrics(
        usage_percent=95.0,
        core_count=4,
        logical_count=8,
        load_avg_1m=9.0,
        load_avg_5m=8.0,
        load_avg_15m=7.0,
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def healthy_memory() -> MemoryMetrics:
    return MemoryMetrics(
        total_bytes=8 * 1024**3,
        available_bytes=4 * 1024**3,
        used_bytes=4 * 1024**3,
        usage_percent=50.0,
        swap_total_bytes=2 * 1024**3,
        swap_used_bytes=512 * 1024**2,
        swap_usage_percent=25.0,
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def critical_memory() -> MemoryMetrics:
    return MemoryMetrics(
        total_bytes=8 * 1024**3,
        available_bytes=512 * 1024**2,
        used_bytes=int(7.5 * 1024**3),
        usage_percent=94.0,
        swap_total_bytes=2 * 1024**3,
        swap_used_bytes=2 * 1024**3,
        swap_usage_percent=100.0,
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def healthy_disk() -> DiskMetrics:
    return DiskMetrics(
        partitions=[
            DiskPartition(
                mountpoint="/",
                device="/dev/sda1",
                filesystem_type="ext4",
                total_bytes=100 * 1024**3,
                used_bytes=40 * 1024**3,
                free_bytes=60 * 1024**3,
                usage_percent=40.0,
                status=HealthStatus.UNKNOWN,
            )
        ],
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def warning_disk() -> DiskMetrics:
    return DiskMetrics(
        partitions=[
            DiskPartition(
                mountpoint="/",
                device="/dev/sda1",
                filesystem_type="ext4",
                total_bytes=100 * 1024**3,
                used_bytes=82 * 1024**3,
                free_bytes=18 * 1024**3,
                usage_percent=82.0,
                status=HealthStatus.UNKNOWN,
            )
        ],
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def healthy_network() -> NetworkMetrics:
    return NetworkMetrics(
        interfaces=[
            NetworkInterface(
                name="eth0",
                ip_addresses=["192.168.1.100"],
                mac_address="aa:bb:cc:dd:ee:ff",
                bytes_sent=1000000,
                bytes_recv=2000000,
                packets_sent=1000,
                packets_recv=2000,
                is_up=True,
            )
        ],
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def healthy_processes() -> ProcessMetrics:
    return ProcessMetrics(
        total_count=150,
        running_count=3,
        sleeping_count=140,
        zombie_count=0,
        top_by_cpu=[
            ProcessInfo(
                pid=1234,
                name="python",
                username="root",
                cpu_percent=5.0,
                memory_percent=1.0,
                status="running",
                cmdline="python /app/server.py",
            )
        ],
        top_by_memory=[
            ProcessInfo(
                pid=5678,
                name="postgres",
                username="postgres",
                cpu_percent=0.5,
                memory_percent=8.0,
                status="sleeping",
                cmdline="postgres: checkpointer",
            )
        ],
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def healthy_services() -> ServiceMetrics:
    return ServiceMetrics(
        services=[
            ServiceInfo(name="ssh", active=True, status="active", enabled=True),
            ServiceInfo(name="docker", active=True, status="active", enabled=True),
        ],
        systemd_available=True,
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def no_docker() -> DockerMetrics:
    return DockerMetrics(installed=False, running=False, status=HealthStatus.UNKNOWN)


@pytest.fixture
def healthy_docker() -> DockerMetrics:
    return DockerMetrics(
        installed=True,
        running=True,
        total_containers=5,
        running_containers=4,
        stopped_containers=1,
        paused_containers=0,
        images_count=10,
        docker_version="24.0.5",
        status=HealthStatus.UNKNOWN,
    )


@pytest.fixture
def sample_system_info() -> SystemInfo:
    return SystemInfo(
        hostname="test-server",
        os_name="Ubuntu 24.04 LTS",
        kernel_version="6.8.0-31-generic",
        architecture="x86_64",
        uptime_seconds=3600 * 24 * 3 + 3600 * 14,
        boot_time=datetime(2024, 1, 1, 0, 0, 0),
        collected_at=datetime(2024, 1, 4, 14, 0, 0),
    )


@pytest.fixture
def healthy_report(
    sample_system_info: SystemInfo,
    healthy_cpu: CpuMetrics,
    healthy_memory: MemoryMetrics,
    healthy_disk: DiskMetrics,
    healthy_network: NetworkMetrics,
    healthy_processes: ProcessMetrics,
    healthy_services: ServiceMetrics,
    healthy_docker: DockerMetrics,
) -> HealthReport:
    """A complete HealthReport with all systems healthy."""
    from server_health.checks.thresholds import (
        evaluate_cpu,
        evaluate_disk,
        evaluate_docker,
        evaluate_memory,
        evaluate_network,
        evaluate_overall,
        evaluate_processes,
        evaluate_services,
    )

    tc = ThresholdConfig()
    report = HealthReport(
        system=sample_system_info,
        cpu=evaluate_cpu(healthy_cpu, tc),
        memory=evaluate_memory(healthy_memory, tc),
        disk=evaluate_disk(healthy_disk, tc),
        network=evaluate_network(healthy_network),
        processes=evaluate_processes(healthy_processes),
        services=evaluate_services(healthy_services),
        docker=evaluate_docker(healthy_docker),
    )
    return evaluate_overall(report)
