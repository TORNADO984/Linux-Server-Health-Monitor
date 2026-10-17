"""Unit tests for the services collector."""

from __future__ import annotations

from unittest.mock import patch


class TestServicesCollector:
    def test_returns_unknown_when_no_systemctl(self):
        with patch("server_health.collectors.services.SYSTEMCTL_PATH", None):
            from server_health.collectors.services import collect_services

            metrics = collect_services(["ssh", "docker"])
            assert metrics.systemd_available is False
            assert metrics.services == []

    def test_checks_active_services(self):
        def mock_run(cmd: str, unit: str):
            if cmd == "is-active":
                return "active"
            if cmd == "is-enabled":
                return "enabled"
            return None

        with (
            patch("server_health.collectors.services.SYSTEMCTL_PATH", "/bin/systemctl"),
            patch("server_health.collectors.services._run_systemctl", side_effect=mock_run),
        ):
            from server_health.collectors.services import collect_services

            metrics = collect_services(["ssh"])
            assert metrics.systemd_available is True
            assert len(metrics.services) == 1
            assert metrics.services[0].name == "ssh"
            assert metrics.services[0].active is True

    def test_skips_not_found_services(self):
        def mock_run(cmd: str, unit: str):
            return "not-found"

        with (
            patch("server_health.collectors.services.SYSTEMCTL_PATH", "/bin/systemctl"),
            patch("server_health.collectors.services._run_systemctl", side_effect=mock_run),
        ):
            from server_health.collectors.services import collect_services

            metrics = collect_services(["nonexistent-service"])
            assert metrics.services == []

    def test_rejects_invalid_service_name(self):
        with patch("server_health.collectors.services.SYSTEMCTL_PATH", "/bin/systemctl"):
            from server_health.collectors.services import collect_services

            # Injection attempt containing command separator
            metrics = collect_services(["ssh; rm -rf /"])
            assert metrics.services == []

    def test_handles_inactive_service(self):
        def mock_run(cmd: str, unit: str):
            if cmd == "is-active":
                return "inactive"
            if cmd == "is-enabled":
                return "disabled"
            return None

        with (
            patch("server_health.collectors.services.SYSTEMCTL_PATH", "/bin/systemctl"),
            patch("server_health.collectors.services._run_systemctl", side_effect=mock_run),
        ):
            from server_health.collectors.services import collect_services

            metrics = collect_services(["nginx"])
            assert len(metrics.services) == 1
            assert metrics.services[0].active is False
            assert metrics.services[0].status == "inactive"
