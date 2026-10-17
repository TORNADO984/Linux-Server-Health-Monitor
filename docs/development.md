# Development Guide

## Environment Setup

### Requirements
- Python 3.12 or higher
- Git
- `make` (optional, for convenience)
- Docker (optional, for containerized builds)

### 1. Clone & Set Up Virtualenv
```bash
git clone https://github.com/yourusername/linux-server-health-monitor.git
cd linux-server-health-monitor

python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
```

### 2. Install Editable Package with Dev Dependencies
```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

---

## Makefile Commands

A comprehensive `Makefile` is included to streamline development:

```bash
# Install dependencies
make install
make install-dev

# Run tests
make test             # Run all tests with HTML and terminal coverage
make test-unit        # Run unit tests only
make test-integration # Run integration tests

# Code quality
make lint             # Check code with Ruff
make format           # Auto-format with Ruff
make format-check     # Verify formatting without altering files
make typecheck        # Run MyPy type checking
make check            # Run all quality gates (lint + format-check + typecheck + test-unit)

# Running locally
make run              # Run full health check
make run-json         # Run health check with JSON output
make run-cpu          # Run CPU collector
make run-watch        # Run in watch mode

# Docker
make docker-build     # Build the Docker image
make docker-run       # Run health check in container with host mounts
```

---

## Testing Strategy

Tests are divided into:
- **`tests/unit/`**: Fast, isolated tests. Subsystem collectors and external commands (`psutil`, `systemctl`, `docker`) are mocked to guarantee deterministic runs on any developer workstation (Linux, macOS, Windows).
- **`tests/integration/`**: End-to-end execution of the collectors and reporters against the actual host environment.

Run pytest directly:
```bash
pytest -v
pytest --cov=server_health --cov-report=term-missing
```

---

## Code Quality Standards

### Formatting and Linting
We adhere to PEP 8 using **Ruff**:
```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Type Checking
All modules in `src/server_health` are fully type-annotated:
```bash
mypy src/server_health/
```

---

## Release Process

1. Ensure the changelog in `CHANGELOG.md` is updated.
2. Bump the version in:
   - `src/server_health/__init__.py`
   - `pyproject.toml`
3. Commit and tag:
   ```bash
   git commit -am "chore(release): v0.1.0"
   git tag v0.1.0
   git push origin main --tags
   ```
4. The GitHub Actions release workflow (`.github/workflows/release.yml`) will automatically validate the release, build wheel packages, and create a GitHub Release draft.
