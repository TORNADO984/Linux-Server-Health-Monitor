"""Unit tests for metric collectors using mocked psutil."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCpuCollector:
    def test_returns_cpu_metrics(self):
        with (
            patch("server_health.collectors.cpu.psutil.cpu_percent", return_value=42.5),
            patch("server_health.collectors.cpu.psutil.cpu_count", return_value=8),
            patch(
                "server_health.collectors.cpu.os.getloadavg",
                return_value=(1.5, 1.2, 1.0),
                create=True,
            ),
        ):
            from server_health.collectors.cpu import collect_cpu

            metrics = collect_cpu(interval=0)
            assert metrics.usage_percent == 42.5
            assert metrics.logical_count == 8
            assert metrics.load_avg_1m == 1.5

    def test_handles_missing_loadavg(self):
        with (
            patch("server_health.collectors.cpu.psutil.cpu_percent", return_value=10.0),
            patch("server_health.collectors.cpu.psutil.cpu_count", return_value=4),
            patch(
                "server_health.collectors.cpu.os.getloadavg",
                side_effect=AttributeError,
                create=True,
            ),
        ):
            from server_health.collectors.cpu import collect_cpu

            metrics = collect_cpu(interval=0)
            assert metrics.load_avg_1m == 0.0
            assert metrics.load_avg_5m == 0.0

    def test_handles_psutil_exception(self):
        with (
            patch("server_health.collectors.cpu.psutil.cpu_percent", side_effect=Exception("fail")),
            patch("server_health.collectors.cpu.psutil.cpu_count", return_value=4),
        ):
            from server_health.collectors.cpu import collect_cpu

            metrics = collect_cpu(interval=0)
            assert metrics.usage_percent == 0.0


class TestMemoryCollector:
    def test_returns_memory_metrics(self):
        mock_vm = MagicMock()
        mock_vm.total = 8 * 1024**3
        mock_vm.available = 4 * 1024**3
        mock_vm.used = 4 * 1024**3
        mock_vm.percent = 50.0

        mock_swap = MagicMock()
        mock_swap.total = 2 * 1024**3
        mock_swap.used = 512 * 1024**2
        mock_swap.percent = 25.0

        with (
            patch("server_health.collectors.memory.psutil.virtual_memory", return_value=mock_vm),
            patch("server_health.collectors.memory.psutil.swap_memory", return_value=mock_swap),
        ):
            from server_health.collectors.memory import collect_memory

            metrics = collect_memory()
            assert metrics.total_bytes == 8 * 1024**3
            assert metrics.usage_percent == 50.0
            assert metrics.swap_usage_percent == 25.0

    def test_handles_psutil_exception(self):
        with (
            patch(
                "server_health.collectors.memory.psutil.virtual_memory",
                side_effect=Exception("fail"),
            ),
            patch(
                "server_health.collectors.memory.psutil.swap_memory", side_effect=Exception("fail")
            ),
        ):
            from server_health.collectors.memory import collect_memory

            metrics = collect_memory()
            assert metrics.total_bytes == 0
            assert metrics.usage_percent == 0.0


class TestDiskCollector:
    def test_returns_disk_metrics(self):
        mock_part = MagicMock()
        mock_part.mountpoint = "/"
        mock_part.device = "/dev/sda1"
        mock_part.fstype = "ext4"

        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024**3
        mock_usage.used = 40 * 1024**3
        mock_usage.free = 60 * 1024**3
        mock_usage.percent = 40.0

        with (
            patch("server_health.collectors.disk.psutil.disk_partitions", return_value=[mock_part]),
            patch("server_health.collectors.disk.psutil.disk_usage", return_value=mock_usage),
        ):
            from server_health.collectors.disk import collect_disk

            metrics = collect_disk()
            assert len(metrics.partitions) == 1
            assert metrics.partitions[0].mountpoint == "/"
            assert metrics.partitions[0].usage_percent == 40.0

    def test_skips_pseudo_filesystems(self):
        mock_part = MagicMock()
        mock_part.mountpoint = "/run"
        mock_part.device = "tmpfs"
        mock_part.fstype = "tmpfs"

        with patch(
            "server_health.collectors.disk.psutil.disk_partitions", return_value=[mock_part]
        ):
            from server_health.collectors.disk import collect_disk

            metrics = collect_disk()
            assert len(metrics.partitions) == 0

    def test_handles_permission_error(self):
        mock_part = MagicMock()
        mock_part.mountpoint = "/secret"
        mock_part.device = "/dev/sdb1"
        mock_part.fstype = "ext4"

        with (
            patch("server_health.collectors.disk.psutil.disk_partitions", return_value=[mock_part]),
            patch("server_health.collectors.disk.psutil.disk_usage", side_effect=PermissionError),
        ):
            from server_health.collectors.disk import collect_disk

            metrics = collect_disk()
            assert len(metrics.partitions) == 0

    def test_handles_partition_enum_failure(self):
        with patch(
            "server_health.collectors.disk.psutil.disk_partitions", side_effect=Exception("oops")
        ):
            from server_health.collectors.disk import collect_disk

            metrics = collect_disk()
            assert metrics.partitions == []


class TestDockerCollector:
    def test_not_installed_when_no_binary(self):
        with patch("server_health.collectors.docker.DOCKER_PATH", None):
            from server_health.collectors.docker import collect_docker

            metrics = collect_docker()
            assert metrics.installed is False
            assert metrics.running is False

    def test_installed_but_not_running(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with (
            patch("server_health.collectors.docker.DOCKER_PATH", "/usr/bin/docker"),
            patch("server_health.collectors.docker._run_docker", return_value=mock_result),
        ):
            from server_health.collectors.docker import collect_docker

            metrics = collect_docker()
            assert metrics.installed is True
            assert metrics.running is False

    def test_running_docker(self):
        def mock_run(*args, **kwargs):
            cmd = args
            result = MagicMock()
            result.returncode = 0
            if "version" in cmd:
                result.stdout = "24.0.5"
            elif "ps" in cmd:
                result.stdout = '{"State":"running"}\n{"State":"exited"}'
            elif "images" in cmd:
                result.stdout = "sha256:abc123\nsha256:def456"
            else:
                result.stdout = ""
            return result

        with (
            patch("server_health.collectors.docker.DOCKER_PATH", "/usr/bin/docker"),
            patch("server_health.collectors.docker._run_docker", side_effect=mock_run),
        ):
            from server_health.collectors.docker import collect_docker

            metrics = collect_docker()
            assert metrics.installed is True
            assert metrics.running is True
            assert metrics.total_containers == 2
            assert metrics.running_containers == 1
            assert metrics.stopped_containers == 1
            assert metrics.images_count == 2
