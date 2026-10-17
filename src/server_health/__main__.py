"""Entry point for running server_health as a module.

Usage:
    python -m server_health
    python -m server_health check
    python -m server_health --help
"""

from server_health.cli import app

if __name__ == "__main__":
    app()
