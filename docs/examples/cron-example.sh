#!/usr/bin/env bash
# =============================================================================
# Linux Server Health Monitor - Cron Automation Reference
# =============================================================================
# This script illustrates common production patterns for scheduling
# server-health via standard cron (crontab -e).
# =============================================================================

set -euo pipefail

# Pattern 1: Run every 15 minutes, append JSON report to log directory
# ---------------------------------------------------------------------
# */15 * * * * /usr/local/bin/server-health check --json >> /var/log/server-health/report.jsonl 2>&1

# Pattern 2: Run hourly, dispatch alert on WARNING (1) or CRITICAL (2)
# ---------------------------------------------------------------------
# 0 * * * * /usr/local/bin/server-health --quiet; STATUS=$?; if [ $STATUS -gt 0 ]; then echo "Server health degraded (Exit code: $STATUS)" | mail -s "[ALERT] Server Health Degraded" sysadmin@example.com; fi

# Pattern 3: Log rotation / cleanup (keep last 14 days of reports)
# ---------------------------------------------------------------------
# 0 2 * * * find /var/log/server-health -type f -name "*.jsonl" -mtime +14 -delete

echo "This script contains cron pattern examples. View file comments for crontab syntax."
