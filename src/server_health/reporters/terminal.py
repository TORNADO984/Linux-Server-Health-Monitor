"""Terminal reporter.

Renders the health report as a human-readable, coloured terminal output
using Rich for formatting. Falls back gracefully to plain text if Rich
is not available or if the terminal encoding lacks unicode support.
"""

from __future__ import annotations

import logging
import sys

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
    SystemInfo,
)

logger = logging.getLogger(__name__)

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _RICH_AVAILABLE = False
    logger.debug("Rich not available; falling back to plain text output.")


def _supports_unicode() -> bool:
    """Check if stdout encoding can handle unicode symbols."""
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "✓⚠✗●○—".encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


_UNICODE_SUPPORTED = _supports_unicode()

_STATUS_COLORS = {
    HealthStatus.HEALTHY: "green",
    HealthStatus.WARNING: "yellow",
    HealthStatus.CRITICAL: "red",
    HealthStatus.UNKNOWN: "dim",
}

if _UNICODE_SUPPORTED:
    _STATUS_ICONS = {
        HealthStatus.HEALTHY: "✓",
        HealthStatus.WARNING: "⚠",
        HealthStatus.CRITICAL: "✗",
        HealthStatus.UNKNOWN: "?",
    }
    _UP_ICON = "✓"
    _DOWN_ICON = "✗"
    _BULLET_ACTIVE = "●"
    _BULLET_INACTIVE = "○"
    _DASH = "—"
    _TABLE_BOX = box.SIMPLE if _RICH_AVAILABLE else None
    _RULE_CHAR = "─"
else:
    _STATUS_ICONS = {
        HealthStatus.HEALTHY: "[OK]",
        HealthStatus.WARNING: "[WARN]",
        HealthStatus.CRITICAL: "[CRIT]",
        HealthStatus.UNKNOWN: "[?]",
    }
    _UP_ICON = "UP"
    _DOWN_ICON = "DOWN"
    _BULLET_ACTIVE = "*"
    _BULLET_INACTIVE = "o"
    _DASH = "-"
    _TABLE_BOX = box.ASCII if _RICH_AVAILABLE else None
    _RULE_CHAR = "-"


def _format_bytes(num_bytes: int) -> str:
    """Format bytes as a human-readable string (GB/MB)."""
    if num_bytes >= 1024**3:
        return f"{num_bytes / 1024**3:.1f} GB"
    if num_bytes >= 1024**2:
        return f"{num_bytes / 1024**2:.1f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes} B"


class TerminalReporter:
    """Renders a :class:`HealthReport` to the terminal."""

    def __init__(self, use_color: bool = True, quiet: bool = False) -> None:
        self.quiet = quiet
        if _RICH_AVAILABLE:
            self._console = Console(highlight=False, no_color=not use_color)
        else:
            self._console = None

    def print(self, report: HealthReport) -> None:
        """Print the full health report to stdout.

        Args:
            report: The completed :class:`HealthReport` to display.
        """
        if _RICH_AVAILABLE and self._console is not None:
            try:
                self._print_rich(report)
                return
            except UnicodeEncodeError:
                # If terminal fails encoding even with rich, fall back to plain
                pass
        self._print_plain(report)

    # ------------------------------------------------------------------
    # Rich output
    # ------------------------------------------------------------------

    def _print_rich(self, report: HealthReport) -> None:
        console = self._console
        assert console is not None

        overall_color = _STATUS_COLORS.get(report.overall_status, "white")
        overall_icon = _STATUS_ICONS.get(report.overall_status, "?")

        console.print()
        console.rule("[bold cyan]SERVER HEALTH MONITOR[/bold cyan]", characters=_RULE_CHAR)
        console.print()

        # System section
        self._print_system_rich(console, report.system)

        if not self.quiet:
            self._print_cpu_rich(console, report.cpu)
            self._print_memory_rich(console, report.memory)
            self._print_disk_rich(console, report.disk)
            self._print_network_rich(console, report.network)
            self._print_processes_rich(console, report.processes)
            self._print_services_rich(console, report.services)
            self._print_docker_rich(console, report.docker)

        # Overall status
        console.print()
        console.rule(characters=_RULE_CHAR)
        overall_text = Text()
        overall_text.append(f"  {overall_icon} Overall Status: ", style="bold")
        overall_text.append(
            report.overall_status.value.upper(),
            style=f"bold {overall_color}",
        )
        console.print(overall_text)
        console.rule(characters=_RULE_CHAR)
        console.print()

    def _print_system_rich(self, console: Console, info: SystemInfo) -> None:
        table = Table(box=_TABLE_BOX, show_header=False, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value")
        table.add_row("Hostname", info.hostname)
        table.add_row("OS", info.os_name)
        table.add_row("Kernel", info.kernel_version)
        table.add_row("Architecture", info.architecture)
        table.add_row("Uptime", info.uptime_human)
        table.add_row("Collected At", info.collected_at.strftime("%Y-%m-%d %H:%M:%S"))
        console.print(Panel(table, title="[bold]System[/bold]", border_style="blue"))

    def _print_cpu_rich(self, console: Console, cpu: CpuMetrics) -> None:
        color = _STATUS_COLORS.get(cpu.status, "white")
        icon = _STATUS_ICONS.get(cpu.status, "?")
        table = Table(box=_TABLE_BOX, show_header=False, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value")
        table.add_row("Usage", f"[{color}]{cpu.usage_percent:.1f}%[/{color}]")
        table.add_row("Cores", f"{cpu.core_count} physical / {cpu.logical_count} logical")
        table.add_row(
            "Load Average",
            f"{cpu.load_avg_1m:.2f}  {cpu.load_avg_5m:.2f}  {cpu.load_avg_15m:.2f}  (1m / 5m / 15m)",
        )
        table.add_row("Status", f"[{color}]{icon} {cpu.status.value.upper()}[/{color}]")
        console.print(Panel(table, title="[bold]CPU[/bold]", border_style="blue"))

    def _print_memory_rich(self, console: Console, mem: MemoryMetrics) -> None:
        color = _STATUS_COLORS.get(mem.status, "white")
        icon = _STATUS_ICONS.get(mem.status, "?")
        table = Table(box=_TABLE_BOX, show_header=False, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value")
        table.add_row("Total RAM", _format_bytes(mem.total_bytes))
        table.add_row(
            "Used",
            f"[{color}]{_format_bytes(mem.used_bytes)} ({mem.usage_percent:.1f}%)[/{color}]",
        )
        table.add_row("Available", _format_bytes(mem.available_bytes))
        if mem.swap_total_bytes > 0:
            table.add_row("Swap Total", _format_bytes(mem.swap_total_bytes))
            table.add_row(
                "Swap Used",
                f"{_format_bytes(mem.swap_used_bytes)} ({mem.swap_usage_percent:.1f}%)",
            )
        table.add_row("Status", f"[{color}]{icon} {mem.status.value.upper()}[/{color}]")
        console.print(Panel(table, title="[bold]Memory[/bold]", border_style="blue"))

    def _print_disk_rich(self, console: Console, disk: DiskMetrics) -> None:
        overall_color = _STATUS_COLORS.get(disk.status, "white")
        overall_icon = _STATUS_ICONS.get(disk.status, "?")

        table = Table(box=_TABLE_BOX, show_header=True, padding=(0, 2))
        table.add_column("Mountpoint", style="cyan")
        table.add_column("Device", style="dim")
        table.add_column("FS Type", style="dim")
        table.add_column("Total", justify="right")
        table.add_column("Used", justify="right")
        table.add_column("Available", justify="right")
        table.add_column("Use%", justify="right")
        table.add_column("Status")

        for part in disk.partitions:
            pcolor = _STATUS_COLORS.get(part.status, "white")
            picon = _STATUS_ICONS.get(part.status, "?")
            table.add_row(
                part.mountpoint,
                part.device,
                part.filesystem_type,
                _format_bytes(part.total_bytes),
                _format_bytes(part.used_bytes),
                _format_bytes(part.free_bytes),
                f"[{pcolor}]{part.usage_percent:.1f}%[/{pcolor}]",
                f"[{pcolor}]{picon}[/{pcolor}]",
            )

        summary_text = Text(
            f"{overall_icon} {disk.status.value.upper()}", style=f"bold {overall_color}"
        )
        console.print(
            Panel(table, title="[bold]Disk[/bold]", border_style="blue", subtitle=str(summary_text))
        )

    def _print_network_rich(self, console: Console, net: NetworkMetrics) -> None:
        table = Table(box=_TABLE_BOX, show_header=True, padding=(0, 2))
        table.add_column("Interface", style="cyan")
        table.add_column("IP Addresses")
        table.add_column("MAC")
        table.add_column("Sent", justify="right")
        table.add_column("Received", justify="right")
        table.add_column("Up?", justify="center")

        for iface in net.interfaces:
            up_str = f"[green]{_UP_ICON}[/green]" if iface.is_up else f"[red]{_DOWN_ICON}[/red]"
            table.add_row(
                iface.name,
                "\n".join(iface.ip_addresses) or _DASH,
                iface.mac_address or _DASH,
                _format_bytes(iface.bytes_sent),
                _format_bytes(iface.bytes_recv),
                up_str,
            )

        console.print(Panel(table, title="[bold]Network[/bold]", border_style="blue"))

    def _print_processes_rich(self, console: Console, procs: ProcessMetrics) -> None:
        summary = Table(box=_TABLE_BOX, show_header=False, padding=(0, 2))
        summary.add_column("Key", style="dim")
        summary.add_column("Value")
        summary.add_row("Total", str(procs.total_count))
        summary.add_row("Running", str(procs.running_count))
        summary.add_row("Sleeping", str(procs.sleeping_count))
        zombie_style = "red" if procs.zombie_count > 0 else ""
        summary.add_row(
            "Zombies",
            f"[{zombie_style}]{procs.zombie_count}[/{zombie_style}]"
            if zombie_style
            else str(procs.zombie_count),
        )
        console.print(Panel(summary, title="[bold]Processes (Summary)[/bold]", border_style="blue"))

        if procs.top_by_cpu:
            cpu_table = Table(box=_TABLE_BOX, show_header=True, padding=(0, 2))
            cpu_table.add_column("PID", justify="right")
            cpu_table.add_column("Name", style="cyan")
            cpu_table.add_column("User", style="dim")
            cpu_table.add_column("CPU%", justify="right")
            cpu_table.add_column("MEM%", justify="right")
            for p in procs.top_by_cpu:
                cpu_table.add_row(
                    str(p.pid),
                    p.name,
                    p.username,
                    f"{p.cpu_percent:.1f}",
                    f"{p.memory_percent:.1f}",
                )
            console.print(
                Panel(cpu_table, title="[bold]Top Processes by CPU[/bold]", border_style="blue")
            )

        if procs.top_by_memory:
            mem_table = Table(box=_TABLE_BOX, show_header=True, padding=(0, 2))
            mem_table.add_column("PID", justify="right")
            mem_table.add_column("Name", style="cyan")
            mem_table.add_column("User", style="dim")
            mem_table.add_column("CPU%", justify="right")
            mem_table.add_column("MEM%", justify="right")
            for p in procs.top_by_memory:
                mem_table.add_row(
                    str(p.pid),
                    p.name,
                    p.username,
                    f"{p.cpu_percent:.1f}",
                    f"{p.memory_percent:.1f}",
                )
            console.print(
                Panel(mem_table, title="[bold]Top Processes by Memory[/bold]", border_style="blue")
            )

    def _print_services_rich(self, console: Console, svc: ServiceMetrics) -> None:
        if not svc.systemd_available:
            console.print(
                Panel(
                    "[dim]systemd not available on this system.[/dim]",
                    title="[bold]Services[/bold]",
                    border_style="blue",
                )
            )
            return

        if not svc.services:
            console.print(
                Panel(
                    "[dim]No monitored services found.[/dim]",
                    title="[bold]Services[/bold]",
                    border_style="blue",
                )
            )
            return

        table = Table(box=_TABLE_BOX, show_header=True, padding=(0, 2))
        table.add_column("Service", style="cyan")
        table.add_column("Status")
        table.add_column("Enabled")

        for s in svc.services:
            if s.active:
                status_str = f"[green]{_BULLET_ACTIVE} active[/green]"
            elif s.status == "failed":
                status_str = f"[red]{_DOWN_ICON} failed[/red]"
            else:
                status_str = f"[yellow]{_BULLET_INACTIVE} {s.status}[/yellow]"

            enabled_str = (
                "[green]enabled[/green]"
                if s.enabled
                else "[dim]disabled[/dim]"
                if s.enabled is False
                else _DASH
            )
            table.add_row(s.name, status_str, enabled_str)

        console.print(Panel(table, title="[bold]Services[/bold]", border_style="blue"))

    def _print_docker_rich(self, console: Console, docker: DockerMetrics) -> None:
        if not docker.installed:
            console.print(
                Panel(
                    "[dim]Docker is not installed.[/dim]",
                    title="[bold]Docker[/bold]",
                    border_style="blue",
                )
            )
            return

        if not docker.running:
            warn_icon = _STATUS_ICONS.get(HealthStatus.WARNING, "!")
            console.print(
                Panel(
                    f"[yellow]{warn_icon} Docker is installed but the daemon is not running.[/yellow]",
                    title="[bold]Docker[/bold]",
                    border_style="blue",
                )
            )
            return

        table = Table(box=_TABLE_BOX, show_header=False, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value")
        table.add_row("Version", docker.docker_version)
        table.add_row("Total Containers", str(docker.total_containers))
        table.add_row("Running", f"[green]{docker.running_containers}[/green]")
        table.add_row("Stopped", str(docker.stopped_containers))
        if docker.paused_containers:
            table.add_row("Paused", str(docker.paused_containers))
        table.add_row("Images", str(docker.images_count))

        console.print(Panel(table, title="[bold]Docker[/bold]", border_style="blue"))

    # ------------------------------------------------------------------
    # Plain text fallback
    # ------------------------------------------------------------------

    def _print_plain(self, report: HealthReport) -> None:
        """Render a minimal plain-text report (no Rich dependency)."""
        width = 60
        sep = "=" * width
        thin = "-" * width

        print(sep)
        print("       SERVER HEALTH MONITOR")
        print(sep)
        print()
        info = report.system
        print(f"Hostname    : {info.hostname}")
        print(f"OS          : {info.os_name}")
        print(f"Kernel      : {info.kernel_version}")
        print(f"Architecture: {info.architecture}")
        print(f"Uptime      : {info.uptime_human}")
        print(f"Collected   : {info.collected_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if not self.quiet:
            cpu = report.cpu
            print("CPU")
            print(thin)
            print(f"Usage       : {cpu.usage_percent:.1f}%")
            print(f"Cores       : {cpu.core_count} physical / {cpu.logical_count} logical")
            print(
                f"Load Avg    : {cpu.load_avg_1m:.2f} / {cpu.load_avg_5m:.2f} / {cpu.load_avg_15m:.2f}"
            )
            print(f"Status      : {cpu.status.value.upper()}")
            print()

            mem = report.memory
            print("MEMORY")
            print(thin)
            print(f"Total       : {_format_bytes(mem.total_bytes)}")
            print(f"Used        : {_format_bytes(mem.used_bytes)} ({mem.usage_percent:.1f}%)")
            print(f"Available   : {_format_bytes(mem.available_bytes)}")
            print(f"Status      : {mem.status.value.upper()}")
            print()

            disk = report.disk
            print("DISK")
            print(thin)
            for part in disk.partitions:
                print(
                    f"  {part.mountpoint:<20} {part.usage_percent:.1f}%  ({_format_bytes(part.used_bytes)} / {_format_bytes(part.total_bytes)})"
                )
            print(f"Status      : {disk.status.value.upper()}")
            print()

            docker = report.docker
            print("DOCKER")
            print(thin)
            if not docker.installed:
                print("  Not installed")
            elif not docker.running:
                print("  Installed but daemon not running")
            else:
                print(f"  Running containers : {docker.running_containers}")
                print(f"  Stopped containers : {docker.stopped_containers}")
                print(f"  Images             : {docker.images_count}")
            print()

        print(sep)
        print(f"Overall Status: {report.overall_status.value.upper()}")
        print(sep)
