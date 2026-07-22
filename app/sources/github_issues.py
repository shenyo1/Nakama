"""Auto-create GitHub issues when an outage is detected.

When the auto-repair cron detects that a source has been down for >N
consecutive probes, it calls ``create_issue()`` to open a GitHub issue
so the engineer can triage. The issue is deduplicated per source — if
an open issue already exists, we add a comment instead.

Configuration (env):
- ``GITHUB_TOKEN``        personal access token with `repo` scope
- ``GITHUB_REPO``         "owner/repo" (defaults to env.github_repo in CI)
- ``GITHUB_ISSUE_LABELS`` comma-separated label names (default: "outage,auto-repair")
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, Optional


DEFAULT_LABELS = "outage,auto-repair"


def _gh_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "nakama-auto-repair/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _post(url: str, body: dict, token: str):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=_gh_headers(token),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return False, {"status": e.code, "error": e.read().decode("utf-8")[:200]}
    except Exception as e:
        return False, {"error": str(e)[:200]}


def _get(url: str, token: str):
    req = urllib.request.Request(url, headers=_gh_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return False, {"status": e.code}
    except Exception as e:
        return False, {"error": str(e)[:200]}


def _search_existing_issue(repo: str, source: str, token: str) -> Optional[int]:
    """Return issue number if an open auto-repair issue exists for source."""
    label = "outage"
    url = (
        f"https://api.github.com/search/issues?q=repo:{repo}+"
        f"is:issue+is:open+in:title+{source}+label:{label}"
    )
    ok, data = _get(url, token)
    if not ok:
        return None
    for it in data.get("items", []):
        if isinstance(it, dict) and source.lower() in it.get("title", "").lower():
            return it.get("number")
    return None


def create_issue(
    source: str,
    error_summary: str,
    probe_items: int = 0,
    threshold: int = 5,
    cooldown_active: bool = False,
) -> Dict[str, object]:
    """Open or comment on a GitHub issue for an outage.

    Returns dict with: ok (bool), action ("created"|"commented"|"skipped"|"error"),
    number, url, error.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO", "shenyo1/Nakama")
    labels_env = os.getenv("GITHUB_ISSUE_LABELS", DEFAULT_LABELS)
    labels = [s.strip() for s in labels_env.split(",") if s.strip()]

    if not token:
        return {"ok": False, "action": "skipped", "error": "GITHUB_TOKEN not set"}

    title = f"🚨 {source} provider down — auto-repair"
    body = (
        f"## Auto-repair alert\n\n"
        f"- **Source**: `{source}`\n"
        f"- **Probe items**: {probe_items} (threshold: {threshold})\n"
        f"- **Circuit breaker cooldown active**: {cooldown_active}\n"
        f"- **Error**: {error_summary}\n\n"
        "### Action items\n"
        f"- [ ] Check `https://mynakama.web.id/sources/health`\n"
        f"- [ ] Run live probe locally: `pytest tests/live/ -k {source}`\n"
        f"- [ ] Verify domain at `deploy/watchdog-domains.sh`\n"
        f"- [ ] Update adapter's `SourceMeta.version` after fix\n\n"
        "_Auto-created by `deploy/auto-repair.sh`_"
    )

    # Dedup: if an open issue exists for this source, comment instead
    existing = _search_existing_issue(repo, source, token)
    if existing:
        comment_url = f"https://api.github.com/repos/{repo}/issues/{existing}/comments"
        ok, data = _post(comment_url, {"body": body}, token)
        return {
            "ok": ok,
            "action": "commented",
            "number": existing,
            "url": f"https://github.com/{repo}/issues/{existing}",
            "error": None if ok else data.get("error"),
        }

    # Otherwise create a new issue
    issues_url = f"https://api.github.com/repos/{repo}/issues"
    ok, data = _post(
        issues_url,
        {"title": title, "body": body, "labels": labels},
        token,
    )
    if not ok:
        return {"ok": False, "action": "error", "error": data.get("error", "unknown")}
    return {
        "ok": True,
        "action": "created",
        "number": data.get("number"),
        "url": data.get("html_url"),
        "error": None,
    }