"""Unit tests for the CLI module using Typer CliRunner."""

from __future__ import annotations

from typer.testing import CliRunner

from server_health import __version__
from server_health.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Production-style Linux server health monitoring CLI" in result.stdout


def test_cli_cpu():
    result = runner.invoke(app, ["cpu", "--json"])
    assert result.exit_code in (0, 1, 2)
    assert '"cpu"' in result.stdout


def test_cli_cpu_plaintext():
    result = runner.invoke(app, ["cpu"])
    assert result.exit_code in (0, 1, 2)
    assert "CPU" in result.stdout


def test_cli_memory():
    result = runner.invoke(app, ["memory", "--json"])
    assert result.exit_code in (0, 1, 2)
    assert '"memory"' in result.stdout


def test_cli_memory_plaintext():
    result = runner.invoke(app, ["memory"])
    assert result.exit_code in (0, 1, 2)
    assert "Memory" in result.stdout


def test_cli_disk():
    result = runner.invoke(app, ["disk", "--json"])
    assert result.exit_code in (0, 1, 2)
    assert '"disk"' in result.stdout


def test_cli_disk_plaintext():
    result = runner.invoke(app, ["disk"])
    assert result.exit_code in (0, 1, 2)
    assert "DISK" in result.stdout


def test_cli_network():
    result = runner.invoke(app, ["network", "--json"])
    assert result.exit_code in (0, 1, 2)
    assert '"network"' in result.stdout


def test_cli_network_plaintext():
    result = runner.invoke(app, ["network"])
    assert result.exit_code in (0, 1, 2)
    assert "NETWORK" in result.stdout


def test_cli_processes():
    result = runner.invoke(app, ["processes", "--json"])
    assert result.exit_code in (0, 1, 2)
    assert '"processes"' in result.stdout


def test_cli_processes_plaintext():
    result = runner.invoke(app, ["processes"])
    assert result.exit_code in (0, 1, 2)
    assert "PROCESSES" in result.stdout


def test_cli_services():
    result = runner.invoke(app, ["services", "--json"])
    assert result.exit_code in (0, 1, 2, 3)
    assert '"services"' in result.stdout


def test_cli_services_plaintext():
    result = runner.invoke(app, ["services"])
    assert result.exit_code in (0, 1, 2, 3)
    assert "SERVICES" in result.stdout


def test_cli_docker():
    result = runner.invoke(app, ["docker", "--json"])
    assert result.exit_code in (0, 1, 2, 3)
    assert '"docker"' in result.stdout


def test_cli_docker_plaintext():
    result = runner.invoke(app, ["docker"])
    assert result.exit_code in (0, 1, 2, 3)
    assert "DOCKER" in result.stdout


def test_cli_check_json():
    result = runner.invoke(app, ["check", "--json"])
    assert result.exit_code in (0, 1, 2)
    assert '"overall_status"' in result.stdout


def test_cli_full_check_default():
    result = runner.invoke(app, ["--json"])
    assert result.exit_code in (0, 1, 2)
    assert '"overall_status"' in result.stdout
