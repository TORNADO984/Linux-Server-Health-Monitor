#!/usr/bin/env bash
# =============================================================================
# Server Health Monitor - Installation Script
# =============================================================================
# Installs server-health-monitor using pip or pipx.
#
# Usage:
#   bash scripts/install.sh          # auto-detect pip or pipx
#   bash scripts/install.sh --pipx   # force pipx
#   bash scripts/install.sh --pip    # force pip
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

check_python() {
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 is required but not found. Install Python 3.12+."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    REQUIRED_MAJOR=3
    REQUIRED_MINOR=12

    ACTUAL_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [ "$ACTUAL_MINOR" -lt "$REQUIRED_MINOR" ]; then
        log_error "Python $REQUIRED_MAJOR.$REQUIRED_MINOR+ is required. Found Python $PYTHON_VERSION."
        exit 1
    fi

    log_info "Python $PYTHON_VERSION found."
}

install_with_pipx() {
    log_info "Installing with pipx..."
    pipx install .
    log_info "Installation complete! Run: server-health --help"
}

install_with_pip() {
    log_warn "pipx not found. Installing with pip in user space."
    log_warn "Consider installing pipx for better isolation: pip install --user pipx"
    pip install --user -e .
    log_info "Installation complete! Ensure ~/.local/bin is in your PATH."
    log_info "Run: server-health --help"
}

main() {
    FORCE_PIPX=false
    FORCE_PIP=false

    for arg in "$@"; do
        case $arg in
            --pipx) FORCE_PIPX=true ;;
            --pip)  FORCE_PIP=true  ;;
            *) log_warn "Unknown argument: $arg" ;;
        esac
    done

    log_info "Server Health Monitor - Installer"
    log_info "=================================="

    check_python

    # Change to the project root (one level up from scripts/)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$PROJECT_ROOT"

    if $FORCE_PIPX; then
        install_with_pipx
    elif $FORCE_PIP; then
        install_with_pip
    elif command -v pipx &>/dev/null; then
        install_with_pipx
    else
        install_with_pip
    fi
}

main "$@"
