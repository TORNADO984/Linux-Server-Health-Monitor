# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2024-10-17

### Added
- Core CLI framework built with Typer (`server-health`)
- Subsystem collectors:
  - System metadata (hostname, distribution, kernel, architecture, uptime)
  - CPU usage, core count, and 1/5/15-minute load averages
  - Physical RAM and swap memory metrics
  - Mounted filesystem disk usage (skipping pseudo filesystems)
  - Network interface addresses, state, and byte transfer counters
  - Process inspector with top consumers by CPU and memory
  - Systemd service health inspection with input sanitization
  - Docker daemon detection, container counts, and image counts
- Health status evaluation engine (`HEALTHY`, `WARNING`, `CRITICAL`, `UNKNOWN`)
- Rich colored terminal reporter with fallback to clean plaintext
- Machine-readable JSON reporting via `--json`
- Continuous watch mode (`--watch` / `--interval`)
- Multi-source configuration system (YAML file, environment variables, default values)
- Containerization:
  - Minimal multi-stage non-root Dockerfile
  - Docker Compose file with host `/proc` and `/sys` volume mounts
- CI/CD automation:
  - GitHub Actions CI workflow (linting, typechecking, pytest matrix on 3.12/3.13, coverage, package build, Docker build)
  - GitHub Actions Release workflow for automated PyPI and Docker Hub packaging
- Linux Automation examples:
  - Systemd `.service` and `.timer` units
  - Cron automation examples
- Comprehensive test suite with high unit test coverage and integration tests
- Full documentation suite (`architecture.md`, `usage.md`, `development.md`)
