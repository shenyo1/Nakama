"""Tests for multi-platform deploy configs (Railway / Render / Fly).

These tests only inspect file contents — no network, no docker required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def railway_toml() -> str:
    p = ROOT / "railway.toml"
    assert p.exists(), "railway.toml missing"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def render_yaml() -> str:
    p = ROOT / "render.yaml"
    assert p.exists(), "render.yaml missing"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def fly_toml() -> str:
    p = ROOT / "fly.toml"
    assert p.exists(), "fly.toml missing"
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def deploy_md() -> str:
    p = ROOT / "DEPLOY.md"
    assert p.exists(), "DEPLOY.md missing"
    return p.read_text(encoding="utf-8")


def test_railway_uses_dockerfile(railway_toml):
    assert 'builder = "DOCKERFILE"' in railway_toml or "DOCKERFILE" in railway_toml
    assert "Dockerfile" in railway_toml


def test_railway_healthcheck(railway_toml):
    assert "healthcheckPath" in railway_toml
    assert "/health" in railway_toml


def test_railway_start_command_uvicorn(railway_toml):
    assert "uvicorn" in railway_toml
    assert "app.main:app" in railway_toml


def test_render_web_service(render_yaml):
    assert "type: web" in render_yaml
    assert "dockerfilePath" in render_yaml
    assert "/health" in render_yaml


def test_render_has_env_vars(render_yaml):
    assert "OFFLINE_MODE" in render_yaml
    assert "PORT" in render_yaml


def test_fly_primary_region_sin(fly_toml):
    """Singapore is closest free region to Indonesia."""
    assert 'primary_region = "sin"' in fly_toml or "sin" in fly_toml


def test_fly_http_healthcheck(fly_toml):
    assert "/health" in fly_toml
    assert "http_service" in fly_toml or "services" in fly_toml


def test_fly_force_https(fly_toml):
    assert "force_https" in fly_toml


def test_deploy_md_covers_three_platforms(deploy_md):
    lower = deploy_md.lower()
    assert "railway" in lower
    assert "render" in lower
    assert "fly" in lower


def test_deploy_md_has_verify_steps(deploy_md):
    assert "/health" in deploy_md
    assert "/stats" in deploy_md
