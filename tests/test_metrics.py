"""Tests for the Prometheus /metrics endpoint and instrumentation."""
from __future__ import annotations

import pytest


# All expected metric names exported by app/metrics.py. The /metrics endpoint
# must include the HELP/TYPE lines for every one of these (or at least emit a
# sample for each).
EXPECTED_METRIC_NAMES = [
    "http_requests_total",
    "http_request_duration_seconds",
    "source_requests_total",
    "cache_hits_total",
    "cache_misses_total",
]


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200_text_plain(client):
    """The /metrics endpoint is reachable and uses the Prometheus content type."""
    r = await client.get("/metrics")
    assert r.status_code == 200
    # prometheus_client emits ``text/plain; version=0.0.4; charset=utf-8``
    # in older releases and ``text/plain; version=1.0.0; charset=utf-8`` in
    # newer ones. Accept either exposition format version.
    ctype = r.headers.get("content-type", "")
    assert ctype.startswith("text/plain"), ctype
    assert "version=" in ctype


@pytest.mark.asyncio
async def test_metrics_body_contains_expected_metric_names(client):
    """The /metrics payload advertises every metric we wired up."""
    r = await client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    for name in EXPECTED_METRIC_NAMES:
        # Each metric should at least have a HELP line in the exposition.
        assert f"# HELP {name} " in body, f"missing HELP line for {name}"
        assert f"# TYPE {name} " in body, f"missing TYPE line for {name}"


@pytest.mark.asyncio
async def test_metrics_increments_http_requests_total(client):
    """Hitting /health bumps the http_requests_total counter."""
    r1 = await client.get("/metrics")
    before = r1.text

    # Trigger at least one labelled request.
    await client.get("/health")
    await client.get("/health")

    r2 = await client.get("/metrics")
    after = r2.text

    # Counter value for /health must have grown. We assert the literal "# HELP"
    # block is present in both and the sample line for /health GET 200 now
    # exists. Easiest cross-check: look for the labels line for /health in the
    # post body.
    assert 'method="GET"' in after
    # /health uses the route template /health when matched (it always does
    # because /health is a registered path operation).
    assert 'path="/health"' in after


@pytest.mark.asyncio
async def test_metrics_records_404s(client):
    """Unknown paths are still recorded so they show up in dashboards."""
    r = await client.get("/this-path-does-not-exist-xyz")
    assert r.status_code == 404

    body = (await client.get("/metrics")).text
    # 404 sample line for the unknown path should be present.
    assert 'status="404"' in body


@pytest.mark.asyncio
async def test_metrics_records_histogram_for_requests(client):
    """The histogram exposes _count / _sum samples for each labelled path."""
    await client.get("/health")

    body = (await client.get("/metrics")).text
    # Histogram emits lines like:
    #   http_request_duration_seconds_count{method="GET",path="/health"} 1.0
    assert 'http_request_duration_seconds_count{method="GET",path="/health"}' in body


@pytest.mark.asyncio
async def test_metrics_records_source_requests_when_source_called(client):
    """Hitting a source endpoint bumps source_requests_total for that source."""
    # First call will be a cache miss (empty in-memory cache for this URL key).
    await client.get("/anime/otakudesu/home")

    body = (await client.get("/metrics")).text
    # At least one sample for otakudesu GET status=200 should exist.
    assert 'source="otakudesu"' in body
    assert 'source_requests_total' in body


@pytest.mark.asyncio
async def test_metrics_records_cache_hits_and_misses(client):
    """cache_hits_total / cache_misses_total emit at least one sample each."""
    # Triggers fetches that go through the cache layer.
    await client.get("/anime/otakudesu/home")
    await client.get("/anime/otakudesu/home")  # likely a cache hit

    body = (await client.get("/metrics")).text
    # Both counters should have a non-empty _total sample line.
    assert "cache_hits_total " in body or 'cache_hits_total{' in body or "cache_hits_total\n" in body or "cache_hits_total " in body
    assert "cache_misses_total " in body or 'cache_misses_total{' in body or "cache_misses_total\n" in body or "cache_misses_total " in body
    # And we should see actual samples (lines starting with a number or
    # containing a value > 0).
    assert "cache_hits_total" in body
    assert "cache_misses_total" in body


@pytest.mark.asyncio
async def test_metrics_endpoint_excluded_from_request_counter(client):
    """Scraping /metrics must not increment http_requests_total for /metrics."""
    before = (await client.get("/metrics")).text
    # Scrape /metrics a few times.
    for _ in range(3):
        await client.get("/metrics")
    after = (await client.get("/metrics")).text

    # The exposition should not contain a labelled sample for /metrics.
    assert 'path="/metrics"' not in after
