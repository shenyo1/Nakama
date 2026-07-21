# ---- builder stage ----
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build deps (needed for any wheels that compile C extensions)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install into /install prefix we will copy in the runtime stage.
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ---- runtime stage ----
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OFFLINE_MODE=0 \
    CACHE_TTL_SECONDS=900 \
    REQUEST_TIMEOUT=20 \
    RATE_LIMIT=60/minute \
    PORT=8000

# Create non-root user for runtime
RUN groupadd --system --gid 1001 sankaapi \
    && useradd --system --uid 1001 --gid sankaapi --no-create-home --shell /sbin/nologin sankaapi

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code and fixtures
COPY --chown=sankaapi:sankaapi app ./app
COPY --chown=sankaapi:sankaapi fixtures ./fixtures

USER sankaapi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]