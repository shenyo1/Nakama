#!/usr/bin/env python3
"""Snapshot Nakama's live OpenAPI spec + regenerate the TypeScript SDK.

The committed ``backend/openapi.json`` (204K) used to drift silently because
nothing regenerated it. This script closes that loop:

1. Boots a FastAPI test client in-process (no live server needed).
2. Calls ``/openapi.json.export`` (the canonical cleaned spec — examples
   stripped — served at ``app/main.py:614``).
3. Writes ``backend/openapi.json`` if it differs from the live spec.
4. Regenerates ``backend/sdks/ts/src/index.ts`` via the existing
   ``scripts/gen_ts_sdk.render()`` function — no network needed.

Usage::

    cd /home/ubuntu/projects/nakama
    python scripts/sync_openapi.py
    python scripts/sync_openapi.py --check   # exit 1 if either file would change
    python scripts/sync_openapi.py --no-ts   # only refresh openapi.json

Designed to be called from the pre-push hook (item 1) so committing a route
addition is a hard error if the snapshot is left stale.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Tuple

# Resolve project root relative to this file so the script works from any cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
OPENAPI_PATH = BACKEND_DIR / "openapi.json"
TS_SDK_PATH = BACKEND_DIR / "sdks" / "ts" / "src" / "index.ts"


def _load_spec() -> dict:
    """Boot the FastAPI app in-process and grab the canonical cleaned spec."""
    # Set OFFLINE_MODE before any app import so sources don't spin up network
    # or Camoufox during boot.
    import os
    os.environ.setdefault("OFFLINE_MODE", "1")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/nakama-openapi-snapshot.sqlite")
    os.environ.setdefault("JWT_SECRET", "openapi-snapshot-test-secret-please-change-32b")
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]

    # Make ``app`` importable.
    sys.path.insert(0, str(BACKEND_DIR))
    from app.main import app  # noqa: E402  pylint: disable=wrong-import-position

    spec = app.openapi()
    # app.openapi() returns FastAPI's stock schema with examples; the
    # /openapi.json.export endpoint applies _clean_openapi_schema. Replicate
    # that here so the snapshot matches what gen_ts_sdk.py consumes.
    if hasattr(app, "_clean_openapi_schema"):
        spec = app._clean_openapi_schema(spec)  # type: ignore[attr-defined]
    return spec


def _write_if_changed(path: Path, new_content: str, check_only: bool) -> bool:
    """Return True if a write happened (or would happen, under --check)."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing == new_content:
        return False
    if check_only:
        print(f"  ❌ {path.relative_to(PROJECT_ROOT)} is stale — would change", file=sys.stderr)
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_content, encoding="utf-8")
    print(f"  ✏️  updated {path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
    return True


def _regen_ts_sdk(check_only: bool) -> bool:
    """Regenerate ``sdks/ts/src/index.ts`` via ``scripts/gen_ts_sdk.render``."""
    sys.path.insert(0, str(BACKEND_DIR / "scripts"))
    # gen_ts_sdk exposes fetch_spec + render; we bypass fetch_spec and
    # reuse the spec we just loaded.
    import gen_ts_sdk  # type: ignore[import-not-found]  # noqa: E402
    fresh = gen_ts_sdk.render(_load_spec())
    return _write_if_changed(TS_SDK_PATH, fresh, check_only)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Exit 1 if either file would change (CI mode).")
    parser.add_argument("--no-ts", action="store_true", help="Only refresh openapi.json, skip TS SDK regen.")
    parser.add_argument("--no-openapi", action="store_true", help="Only regen TS SDK, skip openapi.json snapshot.")
    args = parser.parse_args(argv)

    changed = False

    if not args.no_openapi:
        print("📦 Snapshotting /openapi.json.export → backend/openapi.json", file=sys.stderr)
        spec = _load_spec()
        body = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
        if _write_if_changed(OPENAPI_PATH, body, args.check):
            changed = True
        else:
            print("  ✅ backend/openapi.json is current", file=sys.stderr)

    if not args.no_ts:
        print("📦 Regenerating sdks/ts/src/index.ts", file=sys.stderr)
        if _regen_ts_sdk(args.check):
            changed = True
        else:
            print("  ✅ sdks/ts/src/index.ts is current", file=sys.stderr)

    if args.check and changed:
        print("\n❌ OpenAPI artifacts are stale. Run: python scripts/sync_openapi.py", file=sys.stderr)
        return 1
    if not changed:
        print("\n✅ All OpenAPI artifacts are in sync.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())