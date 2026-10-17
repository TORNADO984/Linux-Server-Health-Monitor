"""Unit tests for threshold evaluation logic."""

from __future__ import annotations

from server_health.checks.thresholds import (
    _classify,
    evaluate_cpu,
    evaluate_disk,
    evaluate_docker,
    evaluate_memory,
    evaluate_network,
    evaluate_overall,
    evaluate_processes,
    evaluate_services,
)
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


class TestClassify:
    def test_below_warning_is_healthy(self):
        assert _classify(50.0, 70.0, 90.0) == HealthStatus.HEALTHY

    def test_at_warning_is_warning(self):
        assert _classify(70.0, 70.0, 90.0) == HealthStatus.WARNING

    def test_above_warning_below_critical_is_warning(self):
        assert _classify(80.0, 70.0, 90.0) == HealthStatus.WARNING

    def test_at_critical_is_critical(self):
        assert _classify(90.0, 70.0, 90.0) == HealthStatus.CRITICAL

    def test_above_critical_is_critical(self):
        assert _classify(99.0, 70.0, 90.0) == HealthStatus.CRITICAL

    def test_zero_is_healthy(self):
        assert _classify(0.0, 70.0, 90.0) == HealthStatus.HEALTHY


class TestEvaluateCpu:
    def test_healthy_cpu(self, healthy_cpu: CpuMetrics, default_thresholds: ThresholdConfig):
        result = evaluate_cpu(healthy_cpu, default_thresholds)
        assert result.status == HealthStatus.HEALTHY

    def test_warning_cpu(self, warning_cpu: CpuMetrics, default_thresholds: ThresholdConfig):
        result = evaluate_cpu(warning_cpu, default_thresholds)
        assert result.status == HealthStatus.WARNING

    def test_critical_cpu(self, critical_cpu: CpuMetrics, default_thresholds: ThresholdConfig):
        result = evaluate_cpu(critical_cpu, default_thresholds)
        assert result.status == HealthStatus.CRITICAL

    def test_modifies_status_in_place(
        self, healthy_cpu: CpuMetrics, default_thresholds: ThresholdConfig
    ):
        result = evaluate_cpu(healthy_cpu, default_thresholds)
        assert result is healthy_cpu


class TestEvaluateMemory:
    def test_healthy_memory(
        self, healthy_memory: MemoryMetrics, default_thresholds: ThresholdConfig
    ):
        result = evaluate_memory(healthy_memory, default_thresholds)
        assert result.status == HealthStatus.HEALTHY

    def test_critical_memory(
        self, critical_memory: MemoryMetrics, default_thresholds: ThresholdConfig
    ):
        result = evaluate_memory(critical_memory, default_thresholds)
        assert result.status == HealthStatus.CRITICAL


class TestEvaluateDisk:
    def test_healthy_disk(self, healthy_disk: DiskMetrics, default_thresholds: ThresholdConfig):
        result = evaluate_disk(healthy_disk, default_thresholds)
        assert result.status == HealthStatus.HEALTHY
        assert result.partitions[0].status == HealthStatus.HEALTHY

    def test_warning_disk(self, warning_disk: DiskMetrics, default_thresholds: ThresholdConfig):
        result = evaluate_disk(warning_disk, default_thresholds)
        assert result.status == HealthStatus.WARNING
        assert result.partitions[0].status == HealthStatus.WARNING

    def test_empty_disk_is_unknown(self, default_thresholds: ThresholdConfig):
        empty = DiskMetrics(partitions=[], status=HealthStatus.UNKNOWN)
        result = evaluate_disk(empty, default_thresholds)
        assert result.status == HealthStatus.UNKNOWN


class TestEvaluateNetwork:
    def test_healthy_network_when_interface_up(self, healthy_network: NetworkMetrics):
        result = evaluate_network(healthy_network)
        assert result.status == HealthStatus.HEALTHY

    def test_warning_when_all_interfaces_down(self, healthy_network: NetworkMetrics):
        for iface in healthy_network.interfaces:
            iface.is_up = False
        result = evaluate_network(healthy_network)
        assert result.status == HealthStatus.WARNING


class TestEvaluateProcesses:
    def test_healthy_when_no_zombies(self, healthy_processes: ProcessMetrics):
        result = evaluate_processes(healthy_processes)
        assert result.status == HealthStatus.HEALTHY

    def test_warning_with_zombies(self, healthy_processes: ProcessMetrics):
        healthy_processes.zombie_count = 3
        result = evaluate_processes(healthy_processes)
        assert result.status == HealthStatus.WARNING


class TestEvaluateServices:
    def test_healthy_when_all_active(self, healthy_services: ServiceMetrics):
        result = evaluate_services(healthy_services)
        assert result.status == HealthStatus.HEALTHY

    def test_unknown_when_no_systemd(self):
        no_systemd = ServiceMetrics(services=[], systemd_available=False)
        result = evaluate_services(no_systemd)
        assert result.status == HealthStatus.UNKNOWN

    def test_warning_when_service_failed(self, healthy_services: ServiceMetrics):
        healthy_services.services[0].status = "failed"
        healthy_services.services[0].active = False
        result = evaluate_services(healthy_services)
        assert result.status == HealthStatus.WARNING


class TestEvaluateDocker:
    def test_unknown_when_not_installed(self, no_docker: DockerMetrics):
        result = evaluate_docker(no_docker)
        assert result.status == HealthStatus.UNKNOWN

    def test_warning_when_not_running(self, no_docker: DockerMetrics):
        no_docker.installed = True
        no_docker.running = False
        result = evaluate_docker(no_docker)
        assert result.status == HealthStatus.WARNING

    def test_healthy_when_running(self, healthy_docker: DockerMetrics):
        result = evaluate_docker(healthy_docker)
        assert result.status == HealthStatus.HEALTHY


class TestEvaluateOverall:
    def test_healthy_overall(self, healthy_report: HealthReport):
        assert healthy_report.overall_status == HealthStatus.HEALTHY

    def test_overall_critical_when_any_critical(self, healthy_report: HealthReport):
        healthy_report.cpu.status = HealthStatus.CRITICAL
        result = evaluate_overall(healthy_report)
        assert result.overall_status == HealthStatus.CRITICAL

    def test_overall_warning_when_any_warning(self, healthy_report: HealthReport):
        healthy_report.disk.status = HealthStatus.WARNING
        result = evaluate_overall(healthy_report)
        assert result.overall_status == HealthStatus.WARNING

    def test_unknown_when_all_unknown(self, healthy_report: HealthReport):
        for attr in ["cpu", "memory", "disk", "network", "processes", "services", "docker"]:
            getattr(healthy_report, attr).status = HealthStatus.UNKNOWN
        result = evaluate_overall(healthy_report)
        assert result.overall_status == HealthStatus.UNKNOWN
