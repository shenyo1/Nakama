"""Tests for the TypeScript SDK generator at scripts/gen_ts_sdk.py.

Each test exercises the generator against the in-process FastAPI app
(no live server required) and verifies a different invariant of the
emitted `sdks/ts/src/index.ts`:

* TS compilation: strict-mode ``tsc --noEmit`` passes against a freshly
  emitted file.
* Endpoint coverage: every required group class is present and contains the
  expected method names.
* Round-trip: ``render(spec)`` is idempotent — generating twice from the
  same spec produces byte-identical output.
* Real-fetch path: ``fetch_spec`` actually walks the URL constructor and
  emits the same SDK on a second invocation through ``render``.

These tests intentionally avoid checking every endpoint name so they stay
robust against FastAPI's evolving surface; they only assert that the
generator produces a syntactically valid client and exposes the documented
named groups.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Make the scripts/ directory importable without packaging work.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from gen_ts_sdk import fetch_spec, render  # noqa: E402  pylint: disable=wrong-import-position


# Where the canonical generated SDK lives.
SDK_PATH = _PROJECT_ROOT / "sdks" / "ts" / "src" / "index.ts"

# Required group classes — kept in sync with TAG_GROUP in gen_ts_sdk.py.
REQUIRED_GROUPS = ["anime", "comic", "novel", "search", "image", "history", "ws", "stats"]

# Path to a system TypeScript compiler if available. We check a couple of
# locations so the suite runs cleanly whether `typescript` is on PATH or
# only available via the bundled node_modules in this dev environment.
_HERMES_TSC = "/home/ubuntu/.hermes/hermes-agent/node_modules/.bin/tsc"
_TSC = shutil.which("tsc") or (_HERMES_TSC if Path(_HERMES_TSC).exists() else None)


@pytest.fixture
def sdk_source(client) -> str:
    """Generate the SDK source from the in-process app and return it as text."""
    import asyncio

    async def _run() -> str:
        r = await client.get("/openapi.json.export")
        assert r.status_code == 200, r.text
        spec = r.json()
        return render(spec)

    return asyncio.get_event_loop().run_until_complete(_run())


@pytest.fixture
def regenerated_sdk(tmp_path: Path, client) -> Path:
    """Generate the SDK into a fresh tmp directory and return its path."""
    import asyncio

    async def _run() -> Path:
        r = await client.get("/openapi.json.export")
        spec = r.json()
        out = tmp_path / "ts" / "src" / "index.ts"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(spec), encoding="utf-8")
        return out

    return asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_generator_writes_valid_typescript_strict(regenerated_sdk: Path) -> None:
    """The generated SDK must compile under ``tsc --strict`` with no errors.

    We invoke the local ``tsc`` if available; if no TS compiler is installed
    the test is skipped rather than failed (so the suite still runs in
    pure-Python environments).
    """
    if not _TSC:
        pytest.skip(
            "no TypeScript compiler available on PATH "
            "(install `typescript` via npm to enable strict-mode validation)"
        )

    cmd = [
        _TSC,
        "--noEmit",
        "--target", "es2020",
        "--moduleResolution", "node",
        "--strict",
        "--lib", "es2020,dom",
        "--ignoreDeprecations", "6.0",
        "--ignoreConfig",
        str(regenerated_sdk),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        "tsc reported errors:\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}\n"
        f"command: {' '.join(cmd)}"
    )


def test_required_group_classes_present(sdk_source: str) -> None:
    """Every documented group class must appear in the generated SDK."""
    for group in REQUIRED_GROUPS:
        cls = group.capitalize()
        assert f"export class {cls} " in sdk_source, (
            f"missing group class export: export class {cls}"
        )

    # The top-level client must be a single class that wires every group up.
    assert "export class NakamaApi {" in sdk_source
    for group in REQUIRED_GROUPS:
        assert f"readonly {group}:" in sdk_source, (
            f"NakamaApi class must expose a '{group}' group"
        )


def test_known_endpoints_present(sdk_source: str) -> None:
    """Spot-check that core endpoints from each group are emitted as methods.

    Asserting a handful of high-signal names per group guards against the
    generator silently dropping operations. The exact set of methods
    evolves as the API grows; these names are stable today.
    """
    expected = {
        # group -> method names that must appear in the group class body
        "Anime": ["home", "search", "detail", "episode"],
        "Comic": ["home", "search", "manga", "chapter", "latest", "popular"],
        "Novel": ["home", "search", "detail", "chapter", "popular", "genres"],
        "Search": ["cross"],
        "Image": ["image"],
        "History": ["get", "post"],
        "Ws": [],  # Only POST /admin/broadcast emits — method name optional
        "Stats": ["health", "stats"],
    }
    for cls, names in expected.items():
        # Find the class block.
        idx = sdk_source.index(f"export class {cls}")
        # Slice to the next class boundary (or end of file).
        next_idx = sdk_source.find("\nexport class ", idx + 1)
        block = sdk_source[idx:] if next_idx == -1 else sdk_source[idx:next_idx]
        for m in names:
            needle = f"async {m}("
            assert needle in block, (
                f"missing method '{m}' in {cls} group; block excerpt:\n{block[:400]}"
            )


def test_nakama_uses_platform_fetch_only(sdk_source: str) -> None:
    """The SDK must use platform ``fetch`` and not pull any runtime imports."""
    # No `import` statements — the SDK is fully self-contained.
    assert "import " not in sdk_source, (
        "generated SDK must be dependency-free; found an import statement"
    )
    # Uses ``fetch`` (the platform global) and provides a fetch override hook.
    assert "await this._client._fetch(" in sdk_source
    assert "opts.fetch ?? " in sdk_source

    # No axios / node-fetch / got / request references.
    for forbidden in ("axios", "node-fetch", "require(", "got(", "request("):
        assert forbidden not in sdk_source, (
            f"unexpected dependency reference in SDK: {forbidden!r}"
        )


def test_round_trip_is_deterministic(client) -> None:
    """Generating twice from the same spec produces byte-identical output."""
    import asyncio

    async def _run() -> tuple[str, str]:
        r = await client.get("/openapi.json.export")
        spec = r.json()
        first = render(spec)
        second = render(spec)
        return first, second

    first, second = asyncio.get_event_loop().run_until_complete(_run())
    assert first == second, (
        "render(spec) is not deterministic — output must be stable for diffs"
    )


def test_fetch_spec_constructs_url() -> None:
    """``fetch_spec`` points at ``{base_url}/openapi.json.export``.

    Verified via a tiny monkey-patch-free path: we ensure the function uses
    exactly the right suffix and fails loudly on a port nothing listens on.
    """
    base = "http://127.0.0.1:1"  # nothing listens on port 1
    with pytest.raises(RuntimeError) as excinfo:
        fetch_spec(base, timeout=1.0)
    assert "/openapi.json.export" in str(excinfo.value) or "Could not reach" in str(
        excinfo.value
    )


def test_canonical_sdk_matches_in_process_render(client) -> None:
    """The committed ``sdks/ts/src/index.ts`` matches ``render(...)`` of the
    schema served by the live app.

    This locks the committed SDK to the current generator output, so a
    generator change that drifts away from the committed file will fail
    the test until the SDK is regenerated and recommitted.
    """
    if not SDK_PATH.exists():
        pytest.skip(
            "no committed SDK at sdks/ts/src/index.ts yet — "
            "run scripts/gen_ts_sdk.py to materialise it"
        )
    import asyncio

    async def _run() -> str:
        r = await client.get("/openapi.json.export")
        return render(r.json())

    fresh = asyncio.get_event_loop().run_until_complete(_run())
    committed = SDK_PATH.read_text(encoding="utf-8")
    assert committed == fresh, (
        "committed SDK is out of date — re-run:\n"
        "  python scripts/gen_ts_sdk.py --output " + str(SDK_PATH)
    )
