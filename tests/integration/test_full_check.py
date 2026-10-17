"""Integration tests for the full health check pipeline.

These tests execute the real collectors on the host machine to verify that the
entire pipeline functions end-to-end without unhandled exceptions.
"""

from __future__ import annotations

import json

from server_health.config import AppConfig
from server_health.models.health import HealthReport, HealthStatus


def _build_report() -> HealthReport:
    """Build a real health report from the current machine."""
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
    from server_health.collectors import (
        collect_cpu,
        collect_disk,
        collect_docker,
        collect_memory,
        collect_network,
        collect_processes,
        collect_services,
        collect_system,
    )

    cfg = AppConfig()
    system = collect_system()
    cpu = evaluate_cpu(collect_cpu(interval=0), cfg.thresholds)
    memory = evaluate_memory(collect_memory(), cfg.thresholds)
    disk = evaluate_disk(collect_disk(), cfg.thresholds)
    network = evaluate_network(collect_network())
    processes = evaluate_processes(collect_processes(top_n=3))
    services = evaluate_services(collect_services(["ssh", "docker"]))
    docker = evaluate_docker(collect_docker())

    report = HealthReport(
        system=system,
        cpu=cpu,
        memory=memory,
        disk=disk,
        network=network,
        processes=processes,
        services=services,
        docker=docker,
    )
    return evaluate_overall(report)


class TestFullHealthCheck:
    def test_report_completes_without_error(self):
        """The full pipeline must not raise any exception."""
        report = _build_report()
        assert report is not None

    def test_report_has_valid_overall_status(self):
        report = _build_report()
        assert report.overall_status in list(HealthStatus)

    def test_report_system_has_hostname(self):
        report = _build_report()
        assert report.system.hostname != ""
        assert report.system.hostname != "unknown"

    def test_report_cpu_has_core_count(self):
        report = _build_report()
        assert report.cpu.core_count >= 1

    def test_report_memory_has_total(self):
        report = _build_report()
        assert report.memory.total_bytes > 0

    def test_report_is_json_serialisable(self):
        report = _build_report()
        from server_health.reporters.json_reporter import JsonReporter

        output = JsonReporter().render(report)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        assert "overall_status" in parsed

    def test_docker_does_not_crash_when_not_installed(self):
        from server_health.checks.thresholds import evaluate_docker
        from server_health.collectors.docker import collect_docker

        metrics = evaluate_docker(collect_docker())
        assert isinstance(metrics.installed, bool)

    def test_services_does_not_crash_without_systemd(self):
        from server_health.checks.thresholds import evaluate_services
        from server_health.collectors.services import collect_services

        metrics = evaluate_services(collect_services(["ssh"]))
        assert metrics is not None
