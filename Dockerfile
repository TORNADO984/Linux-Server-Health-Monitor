# =============================================================================
# Server Health Monitor - Dockerfile
# =============================================================================
# Multi-stage build for a minimal, secure container image.
#
# IMPORTANT LIMITATION:
# When running in a container, the health monitor sees the CONTAINER's
# filesystem and processes, not the host. To monitor the host, you must
# mount host /proc and /sys filesystems (see docker-compose.yml).
# =============================================================================

# --- Build stage ---
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    linux-headers-generic \
    && rm -rf /var/lib/apt/lists/* 2>/dev/null || true

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip install --no-cache-dir --prefix=/install .

# --- Runtime stage ---
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Server Health Monitor"
LABEL org.opencontainers.image.description="Production-style Linux server health monitoring CLI"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/TORNADO984/Linux-Server-Health-Monitor"

# Create a dedicated non-root user
RUN groupadd --gid 1001 monitor \
    && useradd --uid 1001 --gid monitor --shell /bin/bash --create-home monitor

COPY --from=builder /install /usr/local

USER monitor
WORKDIR /home/monitor

HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD server-health cpu --quiet || exit 1

ENTRYPOINT ["server-health"]
CMD ["check"]
