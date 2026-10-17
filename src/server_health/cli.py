"""Command-line interface for Server Health Monitor.

Built with Typer for a modern, documented CLI experience.

Commands:
    server-health           Full health check (default)
    server-health check     Explicit full check
    server-health cpu       CPU metrics only
    server-health memory    Memory metrics only
    server-health disk      Disk metrics only
    server-health network   Network metrics only
    server-health processes Process metrics only
    server-health services  Service status only
    server-health docker    Docker metrics only

Global options:
    --json          Machine-readable JSON output
    --verbose / -v  Verbose logging (DEBUG level)
    --quiet / -q    Suppress non-essential output
    --version       Show application version
    --config PATH   Custom configuration file path
    --watch         Continuously refresh at an interval
    --interval N    Refresh interval for --watch mode (default: 30)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Annotated

import typer

from server_health import __version__
from server_health.config import AppConfig, load_config
from server_health.logging_config import setup_logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="server-health",
    help="Production-style Linux server health monitoring CLI.",
    add_completion=True,
    no_args_is_help=False,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)


# ---------------------------------------------------------------------------
# Common option type annotations
# ---------------------------------------------------------------------------

JsonOption = Annotated[
    bool,
    typer.Option("--json", help="Output results as machine-readable JSON."),
]
VerboseOption = Annotated[
    bool,
    typer.Option("--verbose", "-v", help="Enable verbose (DEBUG) logging."),
]
QuietOption = Annotated[
    bool,
    typer.Option("--quiet", "-q", help="Suppress informational output."),
]
ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        "-c",
        help="Path to a YAML configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
]
WatchOption = Annotated[
    bool,
    typer.Option("--watch", "-w", help="Continuously refresh the health report."),
]
IntervalOption = Annotated[
    int,
    typer.Option(
        "--interval", "-i", help="Refresh interval in seconds (used with --watch).", min=1
    ),
]


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"server-health {__version__}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Shared setup helper
# ---------------------------------------------------------------------------


def _setup(
    verbose: bool,
    quiet: bool,
    config_file: Path | None,
    json_output: bool = False,
) -> AppConfig:
    """Initialise logging and load configuration."""
    effective_quiet = quiet or (json_output and not verbose)
    setup_logging(verbose=verbose, quiet=effective_quiet)
    if not effective_quiet:
        logger.info("Starting Server Health Monitor v%s", __version__)
    try:
        cfg = load_config(config_file)
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    return cfg


def _build_full_report(cfg: AppConfig, cpu_interval: float = 1.0):
    """Collect all metrics and return an evaluated HealthReport."""
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
    from server_health.models.health import HealthReport

    logger.info("Collecting system metrics")
    system = collect_system()
    cpu = evaluate_cpu(collect_cpu(interval=cpu_interval), cfg.thresholds)
    memory = evaluate_memory(collect_memory(), cfg.thresholds)
    disk = evaluate_disk(collect_disk(), cfg.thresholds)
    network = evaluate_network(collect_network())
    processes = evaluate_processes(collect_processes(top_n=cfg.top_processes))
    services = evaluate_services(collect_services(cfg.services))
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


def _output_report(report, as_json: bool, quiet: bool) -> int:
    """Print the report and return the exit code."""
    from server_health.reporters.json_reporter import JsonReporter
    from server_health.reporters.terminal import TerminalReporter

    if as_json:
        JsonReporter(pretty=True).print(report)
    else:
        TerminalReporter(quiet=quiet).print(report)

    return report.overall_status.exit_code


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
    watch: WatchOption = False,
    interval: IntervalOption = 30,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """Run a full server health check.

    When invoked without a sub-command, performs a complete health check
    across all subsystems and exits with an appropriate status code.
    """
    if ctx.invoked_subcommand is not None:
        return

    cfg = _setup(verbose, quiet, config, json_output=json_output)

    if watch:
        _watch_loop(cfg, as_json=json_output, quiet=quiet, interval=interval)
        return

    report = _build_full_report(cfg)
    exit_code = _output_report(report, as_json=json_output, quiet=quiet)
    raise typer.Exit(code=exit_code)


@app.command()
def check(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
    watch: WatchOption = False,
    interval: IntervalOption = 30,
) -> None:
    """Run a full health check across all subsystems."""
    cfg = _setup(verbose, quiet, config, json_output=json_output)

    if watch:
        _watch_loop(cfg, as_json=json_output, quiet=quiet, interval=interval)
        return

    report = _build_full_report(cfg)
    exit_code = _output_report(report, as_json=json_output, quiet=quiet)
    raise typer.Exit(code=exit_code)


@app.command()
def cpu(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
) -> None:
    """Show CPU metrics only."""
    import json as json_lib

    from server_health.checks.thresholds import evaluate_cpu
    from server_health.collectors import collect_cpu

    cfg = _setup(verbose, quiet, config, json_output=json_output)
    metrics = evaluate_cpu(collect_cpu(), cfg.thresholds)

    if json_output:
        typer.echo(json_lib.dumps({"cpu": metrics.to_dict()}, indent=2))
    else:
        _print_single_section(
            "CPU",
            [
                ("Usage", f"{metrics.usage_percent:.1f}%"),
                ("Cores", f"{metrics.core_count} physical / {metrics.logical_count} logical"),
                (
                    "Load Average (1m/5m/15m)",
                    f"{metrics.load_avg_1m:.2f} / {metrics.load_avg_5m:.2f} / {metrics.load_avg_15m:.2f}",
                ),
                ("Status", metrics.status.value.upper()),
            ],
        )

    raise typer.Exit(code=metrics.status.exit_code)


@app.command()
def memory(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
) -> None:
    """Show memory (RAM and swap) metrics."""
    import json as json_lib

    from server_health.checks.thresholds import evaluate_memory
    from server_health.collectors import collect_memory

    cfg = _setup(verbose, quiet, config, json_output=json_output)
    metrics = evaluate_memory(collect_memory(), cfg.thresholds)

    if json_output:
        typer.echo(json_lib.dumps({"memory": metrics.to_dict()}, indent=2))
    else:
        _print_single_section(
            "Memory",
            [
                ("Total RAM", f"{metrics.total_gb} GB"),
                ("Used", f"{metrics.used_gb} GB ({metrics.usage_percent:.1f}%)"),
                ("Available", f"{metrics.available_gb} GB"),
                ("Swap Total", f"{metrics.swap_total_gb} GB"),
                ("Swap Used", f"{metrics.swap_used_gb} GB ({metrics.swap_usage_percent:.1f}%)"),
                ("Status", metrics.status.value.upper()),
            ],
        )

    raise typer.Exit(code=metrics.status.exit_code)


@app.command()
def disk(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
) -> None:
    """Show disk usage for all mounted filesystems."""
    import json as json_lib

    from server_health.checks.thresholds import evaluate_disk
    from server_health.collectors import collect_disk

    cfg = _setup(verbose, quiet, config, json_output=json_output)
    metrics = evaluate_disk(collect_disk(), cfg.thresholds)

    if json_output:
        typer.echo(json_lib.dumps({"disk": metrics.to_dict()}, indent=2))
    else:
        typer.echo("\nDISK")
        typer.echo("-" * 60)
        for part in metrics.partitions:
            typer.echo(
                f"  {part.mountpoint:<20} {part.usage_percent:5.1f}%  "
                f"({part.used_gb:.1f} GB / {part.total_gb:.1f} GB)  "
                f"[{part.status.value.upper()}]"
            )
        typer.echo(f"\nOverall Status: {metrics.status.value.upper()}")

    raise typer.Exit(code=metrics.status.exit_code)


@app.command()
def network(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
) -> None:
    """Show network interface statistics."""
    import json as json_lib

    from server_health.checks.thresholds import evaluate_network
    from server_health.collectors import collect_network

    _setup(verbose, quiet, config, json_output=json_output)
    metrics = evaluate_network(collect_network())

    if json_output:
        typer.echo(json_lib.dumps({"network": metrics.to_dict()}, indent=2))
    else:
        typer.echo("\nNETWORK")
        typer.echo("-" * 60)
        for iface in metrics.interfaces:
            status = "UP" if iface.is_up else "DOWN"
            ips = ", ".join(iface.ip_addresses) or "—"
            typer.echo(f"  {iface.name:<12} {status:<6}  IPs: {ips}")
            typer.echo(
                f"  {'':12} Sent: {iface.bytes_sent:>12,} B  Recv: {iface.bytes_recv:>12,} B"
            )

    raise typer.Exit(code=metrics.status.exit_code)


@app.command()
def processes(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
) -> None:
    """Show top processes by CPU and memory usage."""
    import json as json_lib

    from server_health.checks.thresholds import evaluate_processes
    from server_health.collectors import collect_processes

    cfg = _setup(verbose, quiet, config, json_output=json_output)
    metrics = evaluate_processes(collect_processes(top_n=cfg.top_processes))

    if json_output:
        typer.echo(json_lib.dumps({"processes": metrics.to_dict()}, indent=2))
    else:
        typer.echo("\nPROCESSES")
        typer.echo("-" * 60)
        typer.echo(
            f"  Total: {metrics.total_count}  Running: {metrics.running_count}  "
            f"Sleeping: {metrics.sleeping_count}  Zombies: {metrics.zombie_count}"
        )
        typer.echo("\n  Top by CPU:")
        for p in metrics.top_by_cpu:
            typer.echo(
                f"    {p.pid:>6}  {p.name:<20}  CPU: {p.cpu_percent:5.1f}%  MEM: {p.memory_percent:5.1f}%"
            )
        typer.echo("\n  Top by Memory:")
        for p in metrics.top_by_memory:
            typer.echo(
                f"    {p.pid:>6}  {p.name:<20}  CPU: {p.cpu_percent:5.1f}%  MEM: {p.memory_percent:5.1f}%"
            )

    raise typer.Exit(code=metrics.status.exit_code)


@app.command()
def services(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
) -> None:
    """Show systemd service statuses."""
    import json as json_lib

    from server_health.checks.thresholds import evaluate_services
    from server_health.collectors import collect_services

    cfg = _setup(verbose, quiet, config, json_output=json_output)
    metrics = evaluate_services(collect_services(cfg.services))

    if json_output:
        typer.echo(json_lib.dumps({"services": metrics.to_dict()}, indent=2))
    else:
        typer.echo("\nSERVICES")
        typer.echo("-" * 60)
        if not metrics.systemd_available:
            typer.echo("  systemd not available on this system.")
        elif not metrics.services:
            typer.echo("  No monitored services found.")
        else:
            for s in metrics.services:
                active_str = "active" if s.active else s.status
                typer.echo(f"  {s.name:<20} {active_str}")

    raise typer.Exit(code=metrics.status.exit_code)


@app.command()
def docker(
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    quiet: QuietOption = False,
    config: ConfigOption = None,
) -> None:
    """Show Docker daemon and container status."""
    import json as json_lib

    from server_health.checks.thresholds import evaluate_docker
    from server_health.collectors import collect_docker

    _setup(verbose, quiet, config, json_output=json_output)
    metrics = evaluate_docker(collect_docker())

    if json_output:
        typer.echo(json_lib.dumps({"docker": metrics.to_dict()}, indent=2))
    else:
        typer.echo("\nDOCKER")
        typer.echo("-" * 60)
        if not metrics.installed:
            typer.echo("  Docker: Not installed")
        elif not metrics.running:
            typer.echo("  Docker: Installed but daemon is not running")
        else:
            typer.echo(f"  Version         : {metrics.docker_version}")
            typer.echo(f"  Total Containers: {metrics.total_containers}")
            typer.echo(f"  Running         : {metrics.running_containers}")
            typer.echo(f"  Stopped         : {metrics.stopped_containers}")
            typer.echo(f"  Images          : {metrics.images_count}")

    raise typer.Exit(code=metrics.status.exit_code)


# ---------------------------------------------------------------------------
# Watch loop
# ---------------------------------------------------------------------------


def _watch_loop(cfg: AppConfig, as_json: bool, quiet: bool, interval: int) -> None:
    """Continuously refresh the health report until Ctrl+C."""
    import os

    typer.echo(f"Watch mode active (interval: {interval}s). Press Ctrl+C to stop.", err=True)
    try:
        while True:
            # Clear screen on Linux/macOS; 'cls' on Windows.
            os.system("clear || cls")  # noqa: S605
            report = _build_full_report(cfg, cpu_interval=0.5)
            _output_report(report, as_json=as_json, quiet=quiet)
            time.sleep(interval)
    except KeyboardInterrupt:
        typer.echo("\nWatch mode stopped.", err=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_single_section(title: str, rows: list[tuple[str, str]]) -> None:
    """Print a simple two-column key/value section."""
    typer.echo(f"\n{title}")
    typer.echo("-" * 50)
    for key, value in rows:
        typer.echo(f"  {key:<30} {value}")
