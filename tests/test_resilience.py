"""Unit tests for source_meta, proxy_rotation, domain_rotation."""
from __future__ import annotations
from datetime import date, timedelta
import pytest
from app.sources.source_meta import SourceMeta, days_since
from app.sources import proxy_rotation as pr
from app.sources import domain_rotation as dr


# source_meta
def test_meta_fresh():
    m = SourceMeta(verified_on=date.today().isoformat())
    assert m.age_days() == 0
    assert m.is_stale() is False


def test_meta_stale():
    old = (date.today() - timedelta(days=45)).isoformat()
    m = SourceMeta(verified_on=old)
    assert m.is_stale(threshold_days=30) is True
    assert m.age_days() == 45


def test_meta_invalid_date():
    m = SourceMeta(verified_on="bad")
    assert m.age_days() == 0


def test_days_since():
    assert days_since("bad") == -1
    assert days_since(date.today().isoformat()) == 0


def test_meta_to_dict():
    m = SourceMeta(
        version="x", verified_on=date.today().isoformat(),
        selectors=["a"], alt_domains=["b"],
    )
    d = m.to_dict()
    assert d["version"] == "x"
    assert d["age_days"] == 0


# proxy_rotation
def test_proxy_none(monkeypatch):
    monkeypatch.delenv("PROXY_URL", raising=False)
    monkeypatch.delenv("PROXY_POOL", raising=False)
    pr._ROTATION_INDEX.clear()
    assert pr.next_proxy("kiryuu") is None


def test_proxy_single(monkeypatch):
    monkeypatch.setenv("PROXY_URL", "http://p:8080")
    monkeypatch.delenv("PROXY_POOL", raising=False)
    pr._ROTATION_INDEX.clear()
    assert pr.next_proxy("kiryuu") == "http://p:8080"


def test_proxy_per_source(monkeypatch):
    monkeypatch.setenv("PROXY_URL_KOMIKCAST", "http://k:8080")
    pr._ROTATION_INDEX.clear()
    assert pr.next_proxy("komikcast") == "http://k:8080"


def test_proxy_disabled(monkeypatch):
    monkeypatch.setenv("PROXY_URL", "http://p:8080")
    monkeypatch.setenv("PROXY_DISABLE_FOR", "kiryuu")
    pr._ROTATION_INDEX.clear()
    assert pr.next_proxy("kiryuu") is None
    assert pr.next_proxy("samehadaku") == "http://p:8080"


def test_proxy_pool_round_robin(monkeypatch):
    monkeypatch.setenv("PROXY_POOL", "http://p1,http://p2,http://p3")
    monkeypatch.delenv("PROXY_URL", raising=False)
    pr._ROTATION_INDEX.clear()
    seen = {pr.next_proxy("kiryuu") for _ in range(3)}
    assert "http://p1" in seen
    assert "http://p2" in seen
    assert "http://p3" in seen


def test_proxy_status():
    st = pr.status()
    assert "kiryuu" in st
    assert "pool_size" in st["kiryuu"]


# domain_rotation
def test_domain_cache_clear_one():
    dr._CACHE["kiryuu"] = ("https://kiryuu.to", 1e10)
    dr.cache_clear("kiryuu")
    assert "kiryuu" not in dr._CACHE


def test_domain_cache_clear_all():
    dr._CACHE["a"] = ("x", 1e10)
    dr._CACHE["b"] = ("y", 1e10)
    dr.cache_clear()
    assert dr._CACHE == {}


def test_domain_cache_status():
    dr._CACHE.clear()
    dr._CACHE["kiryuu"] = ("https://kiryuu.to", 1e15)
    st = dr.cache_status()
    assert st["kiryuu"]["url"] == "https://kiryuu.to"
    assert st["kiryuu"]["expires_in_seconds"] > 0


# github_issues
def test_github_issue_no_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from app.sources import github_issues as gh
    res = gh.create_issue("kiryuu", "test error", probe_items=0)
    assert res["action"] == "skipped"
    assert res.get("error") is not None
    assert "GITHUB_TOKEN" in str(res.get("error"))