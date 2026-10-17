# Architecture

## Overview

**Server Health Monitor** follows a clean, modular architecture with strict separation of concerns. Each layer has an explicit responsibility, guaranteeing that metric collection, threshold evaluation, and presentation remain loosely coupled and fully unit-testable.

```text
                 ┌───────────────────────────────────┐
                 │          User / CLI               │
                 │     server-health [command]       │
                 └─────────────────┬─────────────────┘
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │       CLI Layer (cli.py)          │
                 │  • Typer command parsing          │
                 │  • Configuration resolution       │
                 │  • Exit code management           │
                 └─────────────────┬─────────────────┘
                                   │
             ┌─────────────────────┴─────────────────────┐
             ▼                                           ▼
┌─────────────────────────┐                 ┌─────────────────────────┐
│       Collectors        │                 │      Configuration      │
│  (src/server_health/    │                 │  (src/server_health/    │
│       collectors/)      │                 │        config.py)       │
│                         │                 │                         │
│  • cpu.py               │                 │  • Default values       │
│  • memory.py            │                 │  • YAML file            │
│  • disk.py              │                 │  • Environment variables│
│  • network.py           │                 │  • Threshold validation │
│  • processes.py         │                 └─────────────────────────┘
│  • services.py          │
│  • docker.py            │
│  • system.py            │
└────────────┬────────────┘
             │
             ▼ (returns raw dataclasses)
┌─────────────────────────────────────────────────────────────┐
│                 Data Models (models/health.py)              │
│                                                             │
│  CpuMetrics · MemoryMetrics · DiskMetrics · NetworkMetrics │
│  ProcessMetrics · ServiceMetrics · DockerMetrics            │
│  SystemInfo · HealthStatus · HealthReport                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Checks (checks/thresholds.py)               │
│                                                             │
│  Pure evaluation functions (zero I/O side effects)          │
│  • evaluate_cpu()                                           │
│  • evaluate_memory()                                        │
│  • evaluate_disk()                                          │
│  • evaluate_overall()                                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│    Terminal Reporter    │       │      JSON Reporter      │
│ (reporters/terminal.py) │       │(reporters/json_reporter)│
│                         │       │                         │
│  • Rich colored panels  │       │  • Structured JSON      │
│  • Health indicators    │       │  • Pipeline-ready       │
│  • Plaintext fallback   │       │  • Machine-readable     │
└─────────────────────────┘       └─────────────────────────┘
```

---

## Component Breakdown

### 1. CLI Layer (`src/server_health/cli.py`)
- Built on top of **Typer** (backed by Click).
- Exposes top-level commands: `check`, `cpu`, `memory`, `disk`, `network`, `processes`, `services`, `docker`.
- Global flags: `--json`, `--verbose`, `--quiet`, `--watch`, `--interval`, `--config`, `--version`.
- Maps the highest severity status into standard POSIX exit codes:
  - `0`: All subsystems `HEALTHY`
  - `1`: At least one subsystem is in `WARNING` state
  - `2`: At least one subsystem is in `CRITICAL` state
  - `3`: Status `UNKNOWN`

### 2. Collectors Layer (`src/server_health/collectors/`)
Collects raw operating system metrics safely without crashing or leaking sensitive info:
- **`system.py`**: OS release info, kernel version, hostname, and uptime.
- **`cpu.py`**: CPU utilization percentage, logical/physical core counts, 1/5/15-minute load averages via `psutil` and `os.getloadavg()`.
- **`memory.py`**: RAM and swap total, used, available, and percentage.
- **`disk.py`**: Iterates physical mounts, ignores pseudo/virtual filesystems (tmpfs, devfs, cgroup, proc, sysfs), handles `PermissionError` on restricted mountpoints.
- **`network.py`**: Interfaces, assigned IP addresses, MAC addresses, and byte transfer counters.
- **`processes.py`**: Process count (total, sleeping, running, zombies) and top consumers sorted by CPU and memory.
- **`services.py`**: Tests systemd service states via `systemctl is-active`. Service names are strictly validated against `^[a-zA-Z0-9._-]{1,64}$` to eliminate shell injection risks.
- **`docker.py`**: Detects if Docker daemon is running, container states (running, stopped, paused), and local image count. Gracefully falls back if Docker is absent.

### 3. Data Models (`src/server_health/models/health.py`)
- Python 3.12 dataclasses with complete type annotations.
- Include `.to_dict()` helpers for direct JSON serialization without third-party ORM overhead.
- `HealthStatus` Enum with severity comparison (`worse_than()`) and exit code resolution.

### 4. Threshold Engine (`src/server_health/checks/thresholds.py`)
- Pure functions: no disk, network, or external process calls.
- Classifies metrics into `HEALTHY`, `WARNING`, `CRITICAL`, or `UNKNOWN`.
- `evaluate_overall()` evaluates the worst severity across all monitored subsystems.

### 5. Configuration Layer (`src/server_health/config.py`)
Multi-tier configuration resolution with clear hierarchy:
```text
CLI Arguments > Environment Variables (SERVER_HEALTH_*) > YAML Configuration > Built-in Defaults
```
Validates that `warning < critical` on initialization.

### 6. Reporters Layer (`src/server_health/reporters/`)
- **`terminal.py`**: Formats output using Rich panels, tables, and color highlights based on health status. Falls back cleanly to plaintext when terminal formatting is unavailable.
- **`json_reporter.py`**: Produces clean, indented or compact JSON for automated consumption by monitoring pipelines, cron jobs, and webhooks.
