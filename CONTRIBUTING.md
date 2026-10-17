# Contributing to Server Health Monitor

Thank you for your interest in contributing to **Server Health Monitor**! We welcome bug reports, feature suggestions, documentation enhancements, and code contributions.

---

## Code of Conduct

Please maintain a welcoming, respectful, and constructive environment for all contributors.

---

## Development Workflow

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/linux-server-health-monitor.git
cd linux-server-health-monitor
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# .venv\Scripts\Activate.ps1  # On Windows PowerShell

pip install --upgrade pip
pip install -e ".[dev]"
```

### 3. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

---

## Coding Standards

- **Python Version**: Target Python 3.12+.
- **Type Annotations**: All public and internal functions must include complete Python type hints (`mypy` compliant).
- **Architecture**:
  - Keep collectors isolated from presentation and threshold logic.
  - Return typed dataclasses from `models/health.py`.
  - Evaluate statuses in `checks/thresholds.py`.
  - Handle exceptions gracefully—never let collectors crash the CLI.
- **Style & Linting**: We use **Ruff** for linting and code formatting:
  ```bash
  # Check code style and lint issues
  make lint
  # or: ruff check src/ tests/

  # Auto-format code
  make format
  # or: ruff format src/ tests/
  ```

---

## Running Quality Checks and Tests

Before submitting your pull request, ensure all checks pass:

```bash
# Run unit tests with coverage
make test-unit

# Run full test suite
make test

# Run all checks (lint, format check, typecheck, tests)
make check
```

---

## Pull Request Guidelines

1. Ensure all new features or bug fixes have corresponding unit tests under `tests/unit/`.
2. Update documentation under `docs/` or `README.md` if your change modifies CLI behavior or adds commands.
3. Keep commits atomic and use clear commit messages following Conventional Commits (e.g., `feat: add swap memory threshold check`, `fix: handle non-existent mountpoints`).
4. Ensure the GitHub Actions CI pipeline passes on all Python matrix versions (3.12 and 3.13).
