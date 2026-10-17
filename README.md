# Linux Server Health Monitor

[![CI](https://github.com/yourusername/linux-server-health-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/linux-server-health-monitor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

> **A production-grade Linux server health monitoring CLI built with Python, Docker, automation, and CI/CD best practices.**

**Linux Server Health Monitor** (`server-health`) is a lightweight, zero-daemon, resilient command-line utility designed for system administrators, DevOps engineers, and site reliability teams. It inspects critical Linux system components, evaluates utilization against configurable thresholds, produces human-readable and machine-readable JSON reports, and integrates seamlessly into cron, systemd timers, or monitoring pipelines.

---

## Table of Contents

- [Project Purpose](#project-purpose)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Terminal Output Examples](#terminal-output-examples)
- [Installation](#installation)
- [Usage & CLI Reference](#usage--cli-reference)
- [Configuration](#configuration)
- [Machine-Readable JSON Output](#machine-readable-json-output)
- [Exit Codes & Alerting](#exit-codes--alerting)
- [Docker & Containerized Execution](#docker--containerized-execution)
- [Linux Automation (Systemd & Cron)](#linux-automation-systemd--cron)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [CI/CD Pipeline](#cicd-pipeline)
- [Security Model](#security-model)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Project Purpose

Modern server observability is often divided between heavyweight monitoring agents (Prometheus node-exporter, Datadog, Zabbix) and raw shell commands (`free -m`, `top`, `df -h`). 

**Server Health Monitor** fills the critical middle ground:
1. **Zero-friction diagnostics**: Instant single-binary health inspection over SSH or terminal without running a continuous background daemon.
2. **Deterministic status evaluation**: Built-in evaluation logic that categorizes metrics into `HEALTHY`, `WARNING`, or `CRITICAL` based on configurable thresholds.
3. **Pipeline & Automation First**: Standardized exit codes (`0`, `1`, `2`) and structured JSON output for easy integration into bash scripts, CI/CD runners, Kubernetes init containers, or notification webhooks.
4. **Resilient & Safe**: Never crashes due to missing packages, unmounted filesystems, or non-root permissions.

---

## Key Features

- **System Diagnostics**: Hostname, Linux distribution release, kernel version, CPU architecture, system uptime, and collection timestamps.
- **CPU Metrics**: Real-time CPU utilization %, logical and physical core counts, and 1-minute, 5-minute, and 15-minute load averages.
- **Memory & Swap**: Physical RAM capacity, utilized memory, free/available memory, and swap space consumption.
- **Filesystem & Disk Storage**: Dynamic mountpoint discovery, disk capacity, used/free bytes, and partition usage %. Automatically ignores virtual/pseudo filesystems (`tmpfs`, `devtmpfs`, `sysfs`, `procfs`).
- **Network Interfaces**: Network interface states (UP/DOWN), assigned IPv4/IPv6 addresses, MAC addresses, and sent/received byte counters.
- **Process Inspection**: Total process count, status breakdown (running, sleeping, zombies), and top resource consumers ranked by CPU and RAM.
- **Systemd Service Auditing**: Validates the operational state of critical services (`ssh`, `docker`, `nginx`, `cron`, etc.) with built-in command sanitization.
- **Docker Daemon & Containers**: Automatic Docker daemon detection, reporting total, running, stopped, and paused containers, plus local images count without crashing if Docker is missing.
- **Dual Output Modes**: Beautiful color-coded Rich terminal UI (with automatic plain-text fallback) and machine-readable JSON output.
- **Live Watch Mode**: Continuous live dashboard monitoring with customizable refresh intervals (`--watch --interval 5`).

---

## Architecture

The project adheres to a clean, modular architecture separating metric collection, threshold evaluation, and presentation:

```text
                 ┌──────────────────────────────────────┐
                 │          User / Terminal / CI        │
                 │        server-health [command]       │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │          CLI Layer (cli.py)          │
                 │   • Typer commands & flags           │
                 │   • Configuration resolution         │
                 │   • Standardized exit codes          │
                 └──────────────────┬───────────────────┘
                                    │
             ┌──────────────────────┴──────────────────────┐
             ▼                                             ▼
┌───────────────────────────┐                 ┌───────────────────────────┐
│     Collectors Layer      │                 │    Configuration Layer    │
│ (src/server_health/       │                 │   (config.py)             │
│        collectors/)       │                 │                           │
│  • cpu.py       • memory.py│                 │  • Defaults               │
│  • disk.py      • network.py│                │  • YAML configuration     │
│  • processes.py • services.py│               │  • Environment variables  │
│  • docker.py    • system.py │                │  • Validation rules       │
└─────────────┬─────────────┘                 └───────────────────────────┘
              │
              ▼ (raw dataclasses)
┌─────────────────────────────────────────────────────────────────────────┐
│                       Data Models (models/health.py)                    │
│                                                                         │
│   CpuMetrics · MemoryMetrics · DiskMetrics · NetworkMetrics · Docker    │
│   ProcessMetrics · ServiceMetrics · SystemInfo · HealthStatus (Enum)   │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Checks (checks/thresholds.py)                     │
│                                                                         │
│   Pure functional evaluation:                                           │
│   evaluate_cpu() · evaluate_memory() · evaluate_disk() · overall        │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
┌───────────────────────────┐                   ┌───────────────────────────┐
│     Terminal Reporter     │                   │       JSON Reporter       │
│  (reporters/terminal.py)  │                   │(reporters/json_reporter)  │
│                           │                   │                           │
│  • Color-coded panels     │                   │  • Structured schema      │
│  • Status icons (✓, ⚠, ✗) │                   │  • Pipeline-ready         │
│  • Plaintext fallback     │                   │  • Pretty / compact       │
└───────────────────────────┘                   └───────────────────────────┘
```

---

## Terminal Output Examples

### Standard Terminal Report

```text
────────────────────────── SERVER HEALTH MONITOR ──────────────────────────

╭─ System ────────────────────────────────────────────────────────────────╮
│ Hostname      ubuntu-production-01                                      │
│ OS            Ubuntu 24.04 LTS (Noble Numbat)                           │
│ Kernel        6.8.0-31-generic                                          │
│ Architecture  x86_64                                                    │
│ Uptime        4 days, 18 hours, 22 minutes                              │
│ Collected At  2026-10-17 18:30:00                                       │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ CPU ───────────────────────────────────────────────────────────────────╮
│ Usage         24.2%                                                     │
│ Cores         4 physical / 8 logical                                    │
│ Load Average  0.45  0.38  0.31  (1m / 5m / 15m)                         │
│ Status        ✓ HEALTHY                                                 │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ Memory ────────────────────────────────────────────────────────────────╮
│ Total RAM     15.6 GB                                                   │
│ Used          5.4 GB (34.6%)                                            │
│ Available     10.2 GB                                                   │
│ Swap Total    4.0 GB                                                    │
│ Swap Used     120.0 MB (3.0%)                                           │
│ Status        ✓ HEALTHY                                                 │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ Disk ──────────────────────────────────────────────────────────────────╮
│ Mountpoint     Device        FS Type    Total      Used     Avail  Use%  │
│ /              /dev/sda1     ext4       98.4 GB   78.7 GB  19.7 GB  80%  │
│ /data          /dev/sdb1     ext4      500.0 GB  120.0 GB 380.0 GB  24%  │
│                                                            ⚠ WARNING    │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ Docker ────────────────────────────────────────────────────────────────╮
│ Version           26.1.4                                                │
│ Total Containers  8                                                     │
│ Running           7                                                     │
│ Stopped           1                                                     │
│ Images            14                                                    │
╰─────────────────────────────────────────────────────────────────────────╯

───────────────────────────────────────────────────────────────────────────
  ⚠ Overall Status: WARNING
───────────────────────────────────────────────────────────────────────────
```

---

## Installation

### Recommended: pipx (Isolated CLI Environment)
[`pipx`](https://pypa.github.io/pipx/) installs the CLI into an isolated virtual environment while making the `server-health` command available globally:

```bash
pipx install git+https://github.com/yourusername/linux-server-health-monitor.git
```

Or from a local checkout:
```bash
git clone https://github.com/yourusername/linux-server-health-monitor.git
cd linux-server-health-monitor
pipx install .
```

### Standard pip Installation
```bash
git clone https://github.com/yourusername/linux-server-health-monitor.git
cd linux-server-health-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Quick Installer Script
```bash
bash scripts/install.sh
```

---

## Usage & CLI Reference

```bash
# Full server health check
server-health

# Equivalent explicit command
server-health check

# Output formatted JSON instead of terminal tables
server-health --json

# Suppress informational output (only errors/critical)
server-health --quiet

# Enable verbose debug logs
server-health --verbose

# Run in live watch mode, refreshing every 10 seconds
server-health --watch --interval 10
```

### Individual Subsystem Commands

```bash
# CPU utilization, core count, load averages
server-health cpu

# Memory (RAM and Swap) metrics
server-health memory

# Disk mounts and capacity usage
server-health disk

# Network interfaces, IPs, traffic stats
server-health network

# Process counts & top resource consumers
server-health processes

# Systemd services status
server-health services

# Docker daemon & container status
server-health docker
```

---

## Configuration

Server Health Monitor supports layered configuration. Settings are resolved in the following priority order:

1. **CLI Arguments & Flags** (highest precedence)
2. **Environment Variables** (`SERVER_HEALTH_*`)
3. **Configuration File** (`server-health.yaml`)
4. **Built-in Defaults** (fallback)

### Example `server-health.yaml`
Place this file in the working directory or in `~/.config/server-health/server-health.yaml`:

```yaml
thresholds:
  cpu_warning: 70
  cpu_critical: 90
  memory_warning: 75
  memory_critical: 90
  disk_warning: 80
  disk_critical: 90
  load_warning: 2.0
  load_critical: 4.0

top_processes: 5

services:
  - ssh
  - sshd
  - docker
  - nginx
  - cron

log_level: INFO
```

### Environment Variables
Copy `.env.example` to `.env` or set environment variables directly:

```bash
export SERVER_HEALTH_CPU_WARNING=75
export SERVER_HEALTH_CPU_CRITICAL=90
export SERVER_HEALTH_MEMORY_WARNING=80
export SERVER_HEALTH_DISK_CRITICAL=95
export SERVER_HEALTH_LOG_LEVEL=DEBUG
```

---

## Machine-Readable JSON Output

Pass `--json` to any command for pipeline consumption:

```bash
server-health --json
```

```json
{
  "system": {
    "hostname": "ubuntu-production-01",
    "os_name": "Ubuntu 24.04 LTS",
    "kernel_version": "6.8.0-31-generic",
    "architecture": "x86_64",
    "uptime_seconds": 360000.0,
    "uptime_human": "4 days, 4 hours",
    "boot_time": "2026-10-13T14:30:00",
    "collected_at": "2026-10-17T18:30:00"
  },
  "cpu": {
    "usage_percent": 24.2,
    "core_count": 4,
    "logical_count": 8,
    "load_avg_1m": 0.45,
    "load_avg_5m": 0.38,
    "load_avg_15m": 0.31,
    "status": "healthy"
  },
  "memory": {
    "total_gb": 15.6,
    "used_gb": 5.4,
    "available_gb": 10.2,
    "usage_percent": 34.6,
    "swap_total_gb": 4.0,
    "swap_used_gb": 0.12,
    "swap_usage_percent": 3.0,
    "status": "healthy"
  },
  "disk": {
    "partitions": [
      {
        "mountpoint": "/",
        "device": "/dev/sda1",
        "filesystem_type": "ext4",
        "total_gb": 98.4,
        "used_gb": 78.7,
        "free_gb": 19.7,
        "usage_percent": 80.0,
        "status": "warning"
      }
    ],
    "status": "warning"
  },
  "overall_status": "warning"
}
```

---

## Exit Codes & Alerting

`server-health` returns deterministic exit codes conforming to standard POSIX conventions:

| Exit Code | Status | Meaning |
|:---:|:---:|---|
| `0` | **HEALTHY** | All monitored metrics are within normal operating thresholds. |
| `1` | **WARNING** | At least one metric exceeded its warning threshold. |
| `2` | **CRITICAL** | At least one metric exceeded its critical threshold. |
| `3` | **UNKNOWN** | System information could not be determined. |

### Shell Integration Example
```bash
#!/usr/bin/env bash
server-health --quiet
STATUS=$?

case $STATUS in
  0) echo "Server is healthy." ;;
  1) echo "WARNING: Resource limits approaching threshold." ;;
  2) 
     echo "CRITICAL: Urgent server action required!"
     curl -X POST -H 'Content-type: application/json' \
       --data '{"text":"[ALERT] Server resources CRITICAL"}' \
       https://hooks.slack.com/services/YOUR/WEBHOOK/URL
     ;;
esac
```

---

## Docker & Containerized Execution

A minimal, secure multi-stage `Dockerfile` is provided. The image runs as an unprivileged non-root user (`monitor`, UID 1001).

### Build Docker Image
```bash
make docker-build
# or:
docker build -t server-health-monitor:latest .
```

### Run via Docker
```bash
# Run standalone health check inside container
docker run --rm server-health-monitor:latest check
```

### Monitoring the Host from Docker
> [!IMPORTANT]
> By default, container isolation prevents Docker from inspecting host processes and root filesystems. To monitor the host machine from within Docker, you must mount host `/proc`, `/sys`, and `/etc` filesystems and use host networking.

Use the provided `docker-compose.yml`:

```bash
docker compose run --rm server-health
```

Or using standard `docker run`:
```bash
docker run --rm \
  -v /proc:/proc:ro \
  -v /sys:/sys:ro \
  -v /etc:/etc:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --network host \
  server-health-monitor:latest check
```

---

## Linux Automation (Systemd & Cron)

### Systemd Timer (Recommended)
Systemd timers are the modern standard for scheduling recurring tasks on Linux. Production units are provided in `docs/examples/`:

1. Copy service and timer units:
   ```bash
   sudo cp docs/examples/server-health.service /etc/systemd/system/
   sudo cp docs/examples/server-health.timer /etc/systemd/system/
   ```
2. Create log directory:
   ```bash
   sudo mkdir -p /var/log/server-health
   sudo chown monitor:monitor /var/log/server-health
   ```
3. Enable and start the timer:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now server-health.timer
   ```
4. Verify execution:
   ```bash
   systemctl list-timers server-health.timer
   ```

### Cron Integration
To execute every 15 minutes and log output:
```bash
# In crontab -e
*/15 * * * * /usr/local/bin/server-health check --json >> /var/log/server-health/report.jsonl 2>&1
```

---

## Testing & Quality Assurance

The project includes unit and integration tests. Unit tests use mocked system interfaces to ensure deterministic test execution across any OS.

```bash
# Run unit tests
make test-unit

# Run full test suite with coverage
make test

# Run all quality checks (Ruff lint, format check, MyPy type check, unit tests)
make check
```

---

## CI/CD Pipeline

The project includes production-ready GitHub Actions workflows:

1. **Continuous Integration (`.github/workflows/ci.yml`)**:
   - Code style and linting with **Ruff**.
   - Strict formatting checks.
   - Type validation via **MyPy**.
   - Test execution across matrix (**Python 3.12** and **Python 3.13**).
   - Test coverage XML generation and reporting.
   - Package build verification (`python -m build`).
   - Multi-platform Docker Buildx image creation and container smoke test.
2. **Release Pipeline (`.github/workflows/release.yml`)**:
   - Triggers automatically upon pushing a semantic version tag (e.g., `v0.1.0`).
   - Validates test suites and builds source distributions and binary wheels.
   - Drafts automated GitHub Releases with release notes.

---

## Security Model

Security considerations are documented in [SECURITY.md](SECURITY.md):

- **No Shell Injection**: Subprocesses (`systemctl`, `docker`) strictly execute arguments as list tokens without shell invocation (`shell=False`).
- **Input Sanitization**: Service query arguments are matched against `^[a-zA-Z0-9._-]{1,64}$` before execution.
- **Least Privilege**: The CLI is built to run entirely as an unprivileged user without requiring `sudo` or root permissions.
- **Graceful Permission Degradation**: Restricted filesystems or proc entries caught with `PermissionError` are reported cleanly without crashing.
- **Zero Secrets**: No tokens, passwords, or credentials are required or logged.

---

## Known Limitations

- **Container Filesystem View**: Without host mounts (`-v /proc:/proc:ro`), running in Docker will inspect the container's isolated namespace rather than the host.
- **Windows / macOS Host Load Averages**: Linux load averages are sourced from `/proc/loadavg` via `os.getloadavg()`. On Windows development environments, load average defaults to `0.0` gracefully.
- **Systemd in Containers**: Inside standard minimal containers, `systemctl` is not present unless systemd is explicitly running as PID 1. The services collector handles this by marking service status `UNKNOWN` rather than failing.

---

## Troubleshooting

| Issue | Cause | Resolution |
|---|---|---|
| `Docker: Not installed` | Docker binary not found in system `$PATH` | Install Docker or verify `docker` is available in user `$PATH`. |
| `systemd not available` | System does not use systemd (e.g. Alpine, WSL, container) | Normal behavior on non-systemd environments. Collector gracefully bypasses service checks. |
| Exit code `1` or `2` in CI | A resource exceeded warning/critical threshold | Adjust threshold configuration in `server-health.yaml` or set `SERVER_HEALTH_*` environment variables. |
| Permission denied on disk | Mountpoint restricted to root access | The collector skips inaccessible mountpoints safely. Run with appropriate read permissions if needed. |

---

## Roadmap

- [ ] Optional Prometheus metrics exporter endpoint (`--export-prometheus`)
- [ ] Slack, Discord, and Telegram webhook notification dispatcher on CRITICAL states
- [ ] Historical trend tracking via SQLite local persistence
- [ ] GPU monitoring collector (NVIDIA NVML integration)

---

## Contributing

Contributions are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards, branching workflow, and testing requirements.

---

## License

This project is licensed under the terms of the [MIT License](LICENSE).
