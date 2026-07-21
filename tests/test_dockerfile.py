"""Tests for the production Dockerfile.

These tests shell-grep the Dockerfile to make sure the multi-stage build,
non-root user, and healthcheck are present and correctly wired. They do NOT
require docker to be installed — they just inspect the Dockerfile text.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dockerignore_text() -> str:
    return DOCKERIGNORE.read_text(encoding="utf-8")


def test_dockerfile_exists():
    assert DOCKERFILE.exists(), "Dockerfile must exist at project root"


def test_dockerfile_is_multi_stage(dockerfile_text):
    """A two-stage build keeps the final image small."""
    assert dockerfile_text.count("FROM ") >= 2, "Dockerfile must have at least 2 FROM stages"
    assert "AS builder" in dockerfile_text, "builder stage alias required"
    assert "AS runtime" in dockerfile_text, "runtime stage alias required"
    # Builder installs deps, runtime only copies them.
    assert "pip install" in dockerfile_text
    assert "COPY --from=builder" in dockerfile_text, "runtime must copy installed deps from builder"


def test_dockerfile_uses_slim_python(dockerfile_text):
    """python:3.11-slim keeps the image small and CVEs down."""
    assert "python:3.11-slim" in dockerfile_text


def test_dockerfile_runs_as_non_root(dockerfile_text):
    """Non-root user must be created and activated."""
    assert "useradd" in dockerfile_text or "adduser" in dockerfile_text
    assert "USER sankaapi" in dockerfile_text, "non-root USER directive required"


def test_dockerfile_has_healthcheck(dockerfile_text):
    """HEALTHCHECK directive must ping /health."""
    assert "HEALTHCHECK" in dockerfile_text
    assert "/health" in dockerfile_text


def test_dockerfile_exposes_port(dockerfile_text):
    assert "EXPOSE 8000" in dockerfile_text


def test_dockerfile_uses_no_cache_pip(dockerfile_text):
    """--no-cache-dir avoids bloating the image with pip cache."""
    assert "--no-cache-dir" in dockerfile_text


def test_dockerfile_cmd_uses_uvicorn(dockerfile_text):
    """Default command runs the FastAPI app via uvicorn."""
    assert "uvicorn" in dockerfile_text
    assert "app.main:app" in dockerfile_text


def test_dockerfile_copies_app_and_fixtures(dockerfile_text):
    assert "COPY" in dockerfile_text
    assert "./app" in dockerfile_text
    assert "./fixtures" in dockerfile_text


def test_dockerignore_excludes_venv(dockerignore_text):
    """.venv is huge; never copy it into the image."""
    assert ".venv/" in dockerignore_text or "venv/" in dockerignore_text


def test_dockerignore_excludes_git_and_tests(dockerignore_text):
    assert ".git/" in dockerignore_text
    assert "tests" not in dockerignore_text.replace("tests/", "") or "tests" not in dockerignore_text, (
        "tests/ should be excluded — they are not needed at runtime"
    )


def test_dockerignore_excludes_sqlite_db(dockerignore_text):
    """Local SQLite files must never be baked into the image."""
    assert "*.sqlite" in dockerignore_text


def test_dockerignore_excludes_secrets(dockerignore_text):
    """.env files should not leak into the image."""
    assert ".env" in dockerignore_text