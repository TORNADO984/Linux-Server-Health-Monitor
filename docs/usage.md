# Usage Guide

## Quick Start

### Installation

#### Option 1: Using pipx (Recommended for CLI tools)
```bash
pipx install .
```

#### Option 2: Standard pip
```bash
pip install -e .
```

#### Verification
```bash
server-health --version
```

---

## Commands & Examples

### 1. Full Health Check (Default)
Runs a full health audit across all subsystems:
```bash
server-health
# or explicitly:
server-health check
```

### 2. Individual Subsystems

#### CPU
```bash
server-health cpu
```
Displays usage %, core counts, and 1m/5m/15m load averages.

#### Memory
```bash
server-health memory
```
Displays physical RAM and swap space utilization.

#### Disk
```bash
server-health disk
```
Displays all real mounted partitions with usage percentages.

#### Network
```bash
server-health network
```
Displays network interfaces, assigned IP addresses, and byte counters.

#### Processes
```bash
server-health processes
```
Displays process summary (total, running, sleeping, zombies) and top consumers.

#### Systemd Services
```bash
server-health services
```
Checks if monitored systemd services (e.g. `ssh`, `docker`, `nginx`) are active.

#### Docker
```bash
server-health docker
```
Inspects Docker daemon status, container counts, and image counts.

---

## Output Options

### Machine-Readable JSON Output
Add `--json` to any command for structured JSON output:
```bash
server-health --json
server-health cpu --json
server-health disk --json
```

Example JSON response:
```json
{
  "system": {
    "hostname": "ubuntu-server",
    "os_name": "Ubuntu 24.04 LTS",
    "kernel_version": "6.8.0-31-generic",
    "architecture": "x86_64",
    "uptime_seconds": 309600.0,
    "uptime_human": "3 days, 14 hours"
  },
  "cpu": {
    "usage_percent": 23.4,
    "core_count": 4,
    "logical_count": 8,
    "load_avg_1m": 0.42,
    "load_avg_5m": 0.38,
    "load_avg_15m": 0.35,
    "status": "healthy"
  },
  "memory": {
    "total_gb": 16.0,
    "used_gb": 9.8,
    "available_gb": 6.2,
    "usage_percent": 61.2,
    "status": "healthy"
  },
  "disk": {
    "partitions": [
      {
        "mountpoint": "/",
        "total_gb": 100.0,
        "used_gb": 72.1,
        "free_gb": 27.9,
        "usage_percent": 72.1,
        "status": "warning"
      }
    ],
    "status": "warning"
  },
  "overall_status": "warning"
}
```

### Verbose / Quiet Modes
```bash
# Debug logging
server-health --verbose

# Quiet mode: suppress non-essential output (ideal for automation)
server-health --quiet
```

### Watch Mode
Continuously monitors server health with automatic screen refresh:
```bash
# Refresh every 30 seconds (default)
server-health --watch

# Refresh every 5 seconds
server-health --watch --interval 5
```

---

## Configuration

You can customize thresholds using a configuration file or environment variables.

### 1. YAML Configuration File
Place `server-health.yaml` in your working directory, `/etc/server-health/`, or `~/.config/server-health/`:

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
  - docker
  - nginx

log_level: INFO
```

Pass a custom file explicitly:
```bash
server-health --config /path/to/custom-config.yaml
```

### 2. Environment Variables
```bash
export SERVER_HEALTH_CPU_WARNING=60
export SERVER_HEALTH_MEMORY_CRITICAL=85
server-health
```

---

## Automation & Integration

### Shell Script Integration using Exit Codes
The tool returns standardized exit codes:
- `0`: Healthy
- `1`: Warning
- `2`: Critical

```bash
#!/usr/bin/env bash
server-health --quiet
STATUS=$?

if [ $STATUS -eq 2 ]; then
    echo "ALERT: Server is in CRITICAL state!"
    # Trigger PagerDuty, Slack, or webhook
elif [ $STATUS -eq 1 ]; then
    echo "WARNING: Server resources approaching capacity"
fi
```
