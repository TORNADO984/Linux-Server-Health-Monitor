# Security Policy

## Reporting Security Vulnerabilities

We take the security of **Server Health Monitor** seriously. If you discover a security vulnerability, please do **NOT** open a public issue on GitHub.

Instead, please send an email to the maintainers or report via GitHub Security Advisories:
- **Email**: security@example.com (or repository maintainer contact)
- **GitHub**: Navigate to the "Security" tab and click "Report a vulnerability"

Please include:
1. Description of the vulnerability and its potential impact
2. Steps to reproduce or proof-of-concept
3. System details (OS, Python version, package version)
4. Any proposed remediations or patches

We will acknowledge receipt within 48 hours and provide regular updates on remediation progress.

---

## Security Architecture & Design Principles

Even though Server Health Monitor is a CLI tool, security principles have been embedded throughout the design:

### 1. No Shell Injection / Safe Subprocess Execution
- Subprocess execution (`systemctl`, `docker`) strictly uses arguments as a list of strings (`["systemctl", "is-active", unit]`), never `shell=True`.
- All service names are checked against a strict whitelist regular expression (`^[a-zA-Z0-9._-]{1,64}$`) before being executed. Any parameter containing command chaining characters (`;`, `&&`, `|`, `` ` ``, `$()`) is rejected before execution.

### 2. Least Privilege (No Root Required)
- `server-health` operates safely as a standard, unprivileged Linux user.
- Root privileges are **never** required for collecting CPU, RAM, disk, network, or process statistics.
- If root-level inspection of specific filesystems or daemon states is restricted, the collector catches permission errors gracefully without crashing or leaking sensitive information.

### 3. Safe Filesystem & Metric Access
- Handlers catch `PermissionError` and `FileNotFoundError` when accessing filesystems or procfs entries.
- Unmounted or disappeared devices do not cause crashes.

### 4. Zero Credential Storage & Safe Logging
- No secrets, credentials, tokens, or passwords are stored, required, or logged.
- The logging facility avoids printing environment variable bodies or external command environments.
- Process command lines are sanitized and truncated to prevent leaking sensitive inline arguments.

### 5. Dependency Hygiene
- Dependencies are pinned in `pyproject.toml` with established, well-maintained libraries (`psutil`, `typer`, `rich`, `PyYAML`).
- CI workflows continuously audit code for syntax, types, and vulnerabilities.
