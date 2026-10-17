"""Unit tests for health data models."""

from __future__ import annotations

from datetime import datetime

from server_health.models.health import (
    DiskMetrics,
    HealthReport,
    HealthStatus,
    MemoryMetrics,
    SystemInfo,
)


class TestHealthStatus:
    def test_exit_code_healthy(self):
        assert HealthStatus.HEALTHY.exit_code == 0

    def test_exit_code_warning(self):
        assert HealthStatus.WARNING.exit_code == 1

    def test_exit_code_critical(self):
        assert HealthStatus.CRITICAL.exit_code == 2

    def test_exit_code_unknown(self):
        assert HealthStatus.UNKNOWN.exit_code == 3

    def test_worse_than_critical_beats_warning(self):
        assert HealthStatus.CRITICAL.worse_than(HealthStatus.WARNING)

    def test_worse_than_warning_beats_healthy(self):
        assert HealthStatus.WARNING.worse_than(HealthStatus.HEALTHY)

    def test_worse_than_healthy_does_not_beat_warning(self):
        assert not HealthStatus.HEALTHY.worse_than(HealthStatus.WARNING)

    def test_worse_than_self_is_false(self):
        assert not HealthStatus.WARNING.worse_than(HealthStatus.WARNING)


class TestSystemInfo:
    def test_uptime_human_days(self, sample_system_info: SystemInfo):
        human = sample_system_info.uptime_human
        assert "3 days" in human
        assert "14 hours" in human

    def test_uptime_human_zero(self):
        si = SystemInfo(
            hostname="h",
            os_name="Linux",
            kernel_version="6.0",
            architecture="x86_64",
            uptime_seconds=0,
            boot_time=datetime.now(),
        )
        assert "0 minutes" in si.uptime_human or "minute" in si.uptime_human

    def test_to_dict_contains_required_keys(self, sample_system_info: SystemInfo):
        d = sample_system_info.to_dict()
        for key in ["hostname", "os_name", "kernel_version", "uptime_seconds", "uptime_human"]:
            assert key in d


class TestMemoryMetrics:
    def test_total_gb_property(self, healthy_memory: MemoryMetrics):
        assert healthy_memory.total_gb == 8.0

    def test_used_gb_property(self, healthy_memory: MemoryMetrics):
        assert healthy_memory.used_gb == 4.0

    def test_to_dict_contains_gb_fields(self, healthy_memory: MemoryMetrics):
        d = healthy_memory.to_dict()
        assert "total_gb" in d
        assert "used_gb" in d
        assert "available_gb" in d


class TestDiskPartition:
    def test_total_gb(self, healthy_disk: DiskMetrics):
        part = healthy_disk.partitions[0]
        assert part.total_gb == 100.0

    def test_used_gb(self, healthy_disk: DiskMetrics):
        part = healthy_disk.partitions[0]
        assert part.used_gb == 40.0

    def test_to_dict(self, healthy_disk: DiskMetrics):
        d = healthy_disk.partitions[0].to_dict()
        assert d["mountpoint"] == "/"
        assert d["filesystem_type"] == "ext4"
        assert "usage_percent" in d


class TestHealthReport:
    def test_to_dict_contains_all_sections(self, healthy_report: HealthReport):
        d = healthy_report.to_dict()
        for key in [
            "system",
            "cpu",
            "memory",
            "disk",
            "network",
            "processes",
            "services",
            "docker",
            "overall_status",
        ]:
            assert key in d

    def test_to_dict_overall_status_is_string(self, healthy_report: HealthReport):
        d = healthy_report.to_dict()
        assert isinstance(d["overall_status"], str)
        assert d["overall_status"] == "healthy"
