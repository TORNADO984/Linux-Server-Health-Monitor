"""Collectors package for gathering system metrics."""

from server_health.collectors.cpu import collect_cpu
from server_health.collectors.disk import collect_disk
from server_health.collectors.docker import collect_docker
from server_health.collectors.memory import collect_memory
from server_health.collectors.network import collect_network
from server_health.collectors.processes import collect_processes
from server_health.collectors.services import collect_services
from server_health.collectors.system import collect_system

__all__ = [
    "collect_cpu",
    "collect_disk",
    "collect_docker",
    "collect_memory",
    "collect_network",
    "collect_processes",
    "collect_services",
    "collect_system",
]
