# =============================================================================
# Server Health Monitor - Makefile
# =============================================================================
.PHONY: install install-dev test test-unit test-integration lint format typecheck check \
        run run-json run-cpu run-memory run-disk run-docker \
        docker-build docker-run docker-run-json clean build

# Variables
PYTHON ?= python3
PIP    ?= pip
SRC    = src/server_health
TESTS  = tests

# ---- Installation -----------------------------------------------------------

install:  ## Install the package (production)
	$(PIP) install -e .

install-dev:  ## Install the package with development dependencies
	$(PIP) install -e ".[dev]"

# ---- Testing ----------------------------------------------------------------

test:  ## Run all tests with coverage
	pytest $(TESTS)/ -v \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov

test-unit:  ## Run unit tests only
	pytest $(TESTS)/unit/ -v

test-integration:  ## Run integration tests only
	pytest $(TESTS)/integration/ -v

test-ci:  ## Run tests as they would run in CI (with XML coverage)
	pytest $(TESTS)/unit/ -v \
		--cov=$(SRC) \
		--cov-report=xml \
		--cov-report=term-missing

# ---- Code Quality -----------------------------------------------------------

lint:  ## Run Ruff linter
	ruff check $(SRC)/ $(TESTS)/

format:  ## Format code with Ruff
	ruff format $(SRC)/ $(TESTS)/

format-check:  ## Check formatting without modifying files
	ruff format --check $(SRC)/ $(TESTS)/

typecheck:  ## Run MyPy type checker
	mypy $(SRC)/

check: lint format-check typecheck test-unit  ## Run all quality checks

# ---- Running ----------------------------------------------------------------

run:  ## Run the full health check
	$(PYTHON) -m server_health

run-json:  ## Run the full health check with JSON output
	$(PYTHON) -m server_health --json

run-cpu:  ## Show CPU metrics
	$(PYTHON) -m server_health cpu

run-memory:  ## Show memory metrics
	$(PYTHON) -m server_health memory

run-disk:  ## Show disk metrics
	$(PYTHON) -m server_health disk

run-network:  ## Show network metrics
	$(PYTHON) -m server_health network

run-processes:  ## Show top processes
	$(PYTHON) -m server_health processes

run-services:  ## Show service status
	$(PYTHON) -m server_health services

run-docker:  ## Show Docker status
	$(PYTHON) -m server_health docker

run-watch:  ## Watch mode (refreshes every 30 seconds)
	$(PYTHON) -m server_health --watch --interval 30

# ---- Docker -----------------------------------------------------------------

docker-build:  ## Build the Docker image
	docker build -t server-health-monitor:latest .

docker-run:  ## Run a full health check in Docker
	docker run --rm \
		-v /proc:/proc:ro \
		-v /sys:/sys:ro \
		--network host \
		server-health-monitor:latest check

docker-run-json:  ## Run health check in Docker with JSON output
	docker run --rm \
		-v /proc:/proc:ro \
		-v /sys:/sys:ro \
		--network host \
		server-health-monitor:latest check --json

docker-compose-run:  ## Run using Docker Compose
	docker-compose run --rm server-health

# ---- Build ------------------------------------------------------------------

build:  ## Build the Python package
	$(PYTHON) -m build

# ---- Cleanup ----------------------------------------------------------------

clean:  ## Remove build artefacts and caches
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# ---- Help -------------------------------------------------------------------

help:  ## Show this help message
	@echo "Server Health Monitor - Makefile Commands"
	@echo "=========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
