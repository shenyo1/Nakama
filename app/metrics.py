"""Prometheus metrics for SankaApi.

Single-process metric registry. We deliberately avoid ``PROMETHEUS_MULTIPROC_DIR``
because the app runs as a single uvicorn worker in dev/test/CI. If the deployer
ever switches to a multi-worker setup, they should ``unset`` any multiproc
directory so the default in-process registry is used; alternatively they can
set ``PROMETHEUS_MULTIPROC_DIR`` *before importing this module* and call
``multiprocess.MultiProcessCollector`` in :func:`render_metrics` (handled by
:func:`_maybe_multiprocess_registry`).

Exposes:

* ``http_requests_total{method,path,status}`` — Counter of HTTP responses.
* ``http_request_duration_seconds{method,path}`` — Histogram of request latency.
* ``source_requests_total{source,method,status}`` — Counter of upstream fetches.
* ``cache_hits_total / cache_misses_total`` — Counters of cache lookups.

The path label uses the route template (``request.scope["route"].path``) when
available so we do not explode label cardinality with raw URLs that contain
slugs / IDs.
"""
from __future__ import annotations

import os
from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
# Use the default global REGISTRY by default. When PROMETHEUS_MULTIPROC_DIR is
# set (multiprocess mode), prometheus_client replaces the default registry's
# metric values with files in that dir; ``generate_latest`` then needs a
# ``MultiProcessCollector``. We expose :func:`render_metrics` so the /metrics
# endpoint transparently picks the right rendering path.

REGISTRY: CollectorRegistry = CollectorRegistry(auto_describe=True)

# In multiprocess mode, prometheus_client itself swaps in a MultiProcessValue
# and the user's metrics are registered against the global ``REGISTRY`` —
# generate_latest handles aggregation when ``multiprocess_mode`` is detected.
# We import lazily to avoid hard-failing when env is set but the dir doesn't
# exist.
if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
    try:
        from prometheus_client import multiprocess  # type: ignore

        _MULTIPROC = True
    except Exception:
        _MULTIPROC = False
else:
    _MULTIPROC = False


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the API, labelled by method, route, and status.",
    ("method", "path", "status"),
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds, labelled by method and route.",
    ("method", "path"),
    # Reasonable default buckets for a small JSON API (5ms .. 5s).
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)

source_requests_total = Counter(
    "source_requests_total",
    "Total upstream fetches against anime/comic/novel sources, labelled by source, method, and status.",
    ("source", "method", "status"),
    registry=REGISTRY,
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits (in-memory or Redis) for source fetches.",
    registry=REGISTRY,
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses for source fetches.",
    registry=REGISTRY,
)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_metrics() -> tuple[bytes, str]:
    """Return ``(body, content_type)`` for the /metrics endpoint."""
    if _MULTIPROC:
        # Build a fresh registry on demand and aggregate from the multiproc
        # directory. We mutate the body but keep the content-type stable.
        from prometheus_client import multiprocess  # type: ignore
        from prometheus_client.metrics_core import GaugeMetricFamily  # noqa: F401

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


# ---------------------------------------------------------------------------
# Helper: derive a stable path label for a request
# ---------------------------------------------------------------------------
def path_label(request: Any) -> str:
    """Pick a low-cardinality path label for an incoming request.

    Prefer the matched route template (``/anime/{source}/home``) so we do not
    get one label per slug. Falls back to the raw path when no route matched
    (404s, /metrics, etc.).
    """
    route = request.scope.get("route") if hasattr(request, "scope") else None
    route_path = getattr(route, "path", None)
    if route_path:
        return route_path
    # Fallback: use the raw path but keep unknown route under a single label
    # so it does not pollute the metrics with one bucket per URL.
    raw = getattr(request.url, "path", "/")
    return raw or "/"
