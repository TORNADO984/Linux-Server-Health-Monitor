"""Unit tests for reporters."""

from __future__ import annotations

import json

import pytest

from server_health.models.health import DockerMetrics, HealthReport
from server_health.reporters.json_reporter import JsonReporter
from server_health.reporters.terminal import TerminalReporter


class TestJsonReporter:
    def test_render_returns_valid_json(self, healthy_report: HealthReport):
        reporter = JsonReporter(pretty=True)
        output = reporter.render(healthy_report)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_render_contains_overall_status(self, healthy_report: HealthReport):
        reporter = JsonReporter(pretty=True)
        output = reporter.render(healthy_report)
        parsed = json.loads(output)
        assert "overall_status" in parsed
        assert parsed["overall_status"] == "healthy"

    def test_render_contains_all_sections(self, healthy_report: HealthReport):
        reporter = JsonReporter(pretty=True)
        output = reporter.render(healthy_report)
        parsed = json.loads(output)
        for section in [
            "system",
            "cpu",
            "memory",
            "disk",
            "network",
            "processes",
            "services",
            "docker",
        ]:
            assert section in parsed

    def test_compact_output(self, healthy_report: HealthReport):
        reporter = JsonReporter(pretty=False)
        output = reporter.render(healthy_report)
        assert "\n  " not in output
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_cpu_section_structure(self, healthy_report: HealthReport):
        reporter = JsonReporter()
        output = reporter.render(healthy_report)
        parsed = json.loads(output)
        cpu = parsed["cpu"]
        assert "usage_percent" in cpu
        assert "core_count" in cpu
        assert "status" in cpu

    def test_disk_section_has_partitions(self, healthy_report: HealthReport):
        reporter = JsonReporter()
        output = reporter.render(healthy_report)
        parsed = json.loads(output)
        disk = parsed["disk"]
        assert "partitions" in disk
        assert len(disk["partitions"]) > 0

    def test_docker_not_installed(self, healthy_report: HealthReport, no_docker: DockerMetrics):
        healthy_report.docker = no_docker
        reporter = JsonReporter()
        output = reporter.render(healthy_report)
        parsed = json.loads(output)
        assert parsed["docker"]["installed"] is False


class TestTerminalReporter:
    def test_terminal_reporter_runs_without_exception(
        self, healthy_report: HealthReport, capsys: pytest.CaptureFixture
    ):
        reporter = TerminalReporter(use_color=False, quiet=False)
        reporter.print(healthy_report)
        captured = capsys.readouterr()
        # Should contain key outputs
        assert "SERVER HEALTH MONITOR" in captured.out or "Overall Status" in captured.out

    def test_terminal_reporter_quiet_mode(
        self, healthy_report: HealthReport, capsys: pytest.CaptureFixture
    ):
        reporter = TerminalReporter(use_color=False, quiet=True)
        reporter.print(healthy_report)
        captured = capsys.readouterr()
        assert "Overall Status" in captured.out
