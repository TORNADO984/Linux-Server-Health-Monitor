"""Unit tests for system, network, and processes collectors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from server_health.collectors.network import collect_network
from server_health.collectors.processes import collect_processes
from server_health.collectors.system import (
    _safe_hostname,
    _safe_kernel_version,
    _safe_os_name,
    _safe_uptime,
    collect_system,
)


def test_collect_system():
    sys_info = collect_system()
    assert sys_info.hostname != ""
    assert sys_info.os_name != ""
    assert sys_info.architecture != ""


def test_safe_system_helpers():
    assert _safe_hostname() != ""
    assert _safe_kernel_version() != ""
    assert _safe_os_name() != ""
    boot, uptime = _safe_uptime()
    assert uptime >= 0


def test_collect_network():
    net = collect_network()
    assert isinstance(net.interfaces, list)


def test_collect_processes():
    procs = collect_processes(top_n=3)
    assert procs.total_count >= 1
    assert len(procs.top_by_cpu) <= 3
    assert len(procs.top_by_memory) <= 3


def test_collect_processes_mocked():
    mock_proc = MagicMock()
    mock_proc.as_dict.return_value = {
        "pid": 9999,
        "name": "mocked",
        "username": "tester",
        "cpu_percent": 15.0,
        "memory_percent": 2.5,
        "status": "running",
        "cmdline": ["mocked", "arg1"],
    }
    with patch("server_health.collectors.processes.psutil.process_iter", return_value=[mock_proc]):
        metrics = collect_processes(top_n=1)
        assert metrics.total_count == 1
        assert len(metrics.top_by_cpu) == 1
        assert metrics.top_by_cpu[0].name == "mocked"
