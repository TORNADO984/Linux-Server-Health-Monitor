"""Network metrics collector.

Gathers per-interface statistics including IP addresses, MAC addresses,
and traffic counters using psutil.
"""

from __future__ import annotations

import logging
import socket

import psutil

from server_health.models.health import HealthStatus, NetworkInterface, NetworkMetrics

logger = logging.getLogger(__name__)

# Interfaces to skip (loopback variants)
_LOOPBACK_INTERFACES = frozenset({"lo", "lo0"})


def collect_network(include_loopback: bool = False) -> NetworkMetrics:
    """Collect network interface statistics.

    Args:
        include_loopback: Whether to include loopback interfaces (lo/lo0).

    Returns:
        A populated :class:`NetworkMetrics` instance.
    """
    logger.debug("Collecting network metrics")

    interfaces: list[NetworkInterface] = []

    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to collect network metrics: %s", exc)
        return NetworkMetrics(interfaces=[], status=HealthStatus.UNKNOWN)

    for iface_name, addr_list in addrs.items():
        if not include_loopback and iface_name in _LOOPBACK_INTERFACES:
            logger.debug("Skipping loopback interface: %s", iface_name)
            continue

        ip_addresses = _extract_ip_addresses(addr_list)
        mac_address = _extract_mac(addr_list)

        iface_stats = stats.get(iface_name)
        is_up = bool(iface_stats and iface_stats.isup)

        iface_counters = counters.get(iface_name)
        bytes_sent = iface_counters.bytes_sent if iface_counters else 0
        bytes_recv = iface_counters.bytes_recv if iface_counters else 0
        packets_sent = iface_counters.packets_sent if iface_counters else 0
        packets_recv = iface_counters.packets_recv if iface_counters else 0

        interface = NetworkInterface(
            name=iface_name,
            ip_addresses=ip_addresses,
            mac_address=mac_address,
            bytes_sent=bytes_sent,
            bytes_recv=bytes_recv,
            packets_sent=packets_sent,
            packets_recv=packets_recv,
            is_up=is_up,
        )
        interfaces.append(interface)
        logger.debug(
            "Network interface: %s, up=%s, ips=%s",
            iface_name,
            is_up,
            ip_addresses,
        )

    logger.debug("Collected metrics for %d network interfaces", len(interfaces))
    return NetworkMetrics(interfaces=interfaces, status=HealthStatus.UNKNOWN)


def _extract_ip_addresses(addr_list: list) -> list[str]:
    """Extract IPv4 and IPv6 addresses from a psutil address list."""
    ips: list[str] = []
    for addr in addr_list:
        if addr.family in (socket.AF_INET, socket.AF_INET6):
            ips.append(addr.address)
    return ips


def _extract_mac(addr_list: list) -> str:
    """Extract the first MAC address from a psutil address list."""
    for addr in addr_list:
        # AF_LINK = 17 on Linux, psutil.AF_LINK on all platforms
        if addr.family == psutil.AF_LINK:
            return addr.address or ""
    return ""
