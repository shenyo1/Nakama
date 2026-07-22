"""Generate the TypeScript SDK for NakamaApi from /openapi.json.export.

The generator fetches the OpenAPI 3 schema from a running NakamaApi instance
and emits a single hand-rolled, dependency-free TypeScript client. Each
endpoint group is exposed as a named class (``Anime``, ``Comic``, …) so
callers can write::

    import { NakamaApi } from "./sdks/ts/src";
    const api = new NakamaApi({ baseUrl: "https://example.com" });
    const res = await api.anime.home("otakudesu");

Design goals
------------
1. **Zero runtime deps.** The SDK uses the platform ``fetch`` API directly.
   No axios, no node-fetch, no openapi-typescript-codegen output.
2. **End-to-end typing.** Every endpoint method signature carries its
   parameter shape and a return type that resolves all response ``$ref``s
   against the generated model interfaces.
3. **Grouped surface.** Endpoints are bucketed by OpenAPI tag (with a
   sensible default for untagged meta endpoints), so the SDK mirrors the
   FastAPI router layout (anime, comic, novel, search, image, history, ws,
   stats).
4. **CLI friendly.** ``--url`` overrides the running instance, ``--output``
   overrides the destination path. Both default to ``http://localhost:8000``
   and ``./sdks/ts/src/index.ts``.

Usage
-----
::

    # from project root, while the FastAPI app is running:
    python scripts/gen_ts_sdk.py
    python scripts/gen_ts_sdk.py --url http://localhost:8000
    python scripts/gen_ts_sdk.py --url https://staging.example.com \
        --output ./sdks/ts/src/index.ts
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Tag → SDK group mapping.
#
# The SDK exposes one class per logical group. We let the OpenAPI ``tags``
# array drive placement, but we also normalize a couple of names that don't
# match the desired public API (proxy → image). Untagged operations are
# funneled into ``stats`` because the only two unauthenticated meta endpoints
# (/health, /stats) belong there conceptually.
# ---------------------------------------------------------------------------
TAG_GROUP = {
    "anime": "anime",
    "comic": "comic",
    "novel": "novel",
    "search": "search",
    "proxy": "image",
    "history": "history",
    "ws": "ws",
    "stats": "stats",
    "health": "stats",
    "preferences": "preferences",
}

DEFAULT_GROUP = "stats"

# Iteration order used both in the class declarations and the index module.
GROUP_ORDER = ["anime", "comic", "novel", "search", "image", "history", "ws", "stats", "preferences"]


# ---------------------------------------------------------------------------
# Type conversion: OpenAPI schema → TypeScript expression.
# ---------------------------------------------------------------------------
def _ts_safe_name(name: str) -> str:
    """Return a TypeScript-safe identifier for ``name``."""
    out: List[str] = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        elif ch in {"-", ".", " ", "/"}:
            out.append("_")
        # everything else ($, brackets, etc.) dropped
    cleaned = "".join(out).strip("_")
    if not cleaned:
        cleaned = "Anon"
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned


def _resolve_ref(ref: str, components: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Return (type_name, schema_dict) for a ``$ref`` pointer."""
    assert ref.startswith("#/components/schemas/"), ref
    name = ref.rsplit("/", 1)[-1]
    return name, components[name]


def _ts_type_for(
    schema: Dict[str, Any],
    components: Dict[str, Any],
    *,
    seen: Optional[set] = None,
) -> str:
    """Translate an OpenAPI schema node into a TypeScript type expression."""
    if seen is None:
        seen = set()

    if not isinstance(schema, dict):
        return "unknown"

    # $ref — unwrap once, tracking recursion depth to avoid infinite loops.
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen:
            return "unknown"
        name, target = _resolve_ref(ref, components)
        seen.add(ref)
        return _ts_type_for(target, components, seen=seen)

    # anyOf / oneOf — widen to the union of members.
    if "anyOf" in schema or "oneOf" in schema:
        members: List[Dict[str, Any]] = list(
            schema.get("anyOf") or schema.get("oneOf") or []
        )
        rendered = [_ts_type_for(m, components, seen=seen) for m in members]
        # de-dup while preserving order
        seen_types = set()
        unique_rendered = []
        for t in rendered:
            if t not in seen_types:
                seen_types.add(t)
                unique_rendered.append(t)
        rendered = unique_rendered
        # filter null out of nullable unions.
        rendered = [t for t in rendered if t != "null"]
        if not rendered:
            return "unknown"
        if len(rendered) == 1:
            return rendered[0]
        return " | ".join(rendered)

    # allOf — intersection.
    if "allOf" in schema:
        return " & ".join(
            _ts_type_for(m, components, seen=seen) for m in schema["allOf"]
        )

    # enum → string-literal union (or mixed literal union).
    if "enum" in schema:
        vals = schema["enum"]
        if all(isinstance(v, str) for v in vals):
            return " | ".join(json.dumps(v) for v in vals)
        return " | ".join(json.dumps(v) for v in vals)

    t = schema.get("type")

    if t == "string":
        return "string"
    if t == "integer" or t == "number":
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "null":
        return "null"
    if t == "array":
        items = schema.get("items", {})
        inner = _ts_type_for(items, components, seen=seen)
        return f"Array<{inner}>"

    if t == "object" or "properties" in schema or "additionalProperties" in schema:
        return _inline_object_type(schema, components, seen=seen)

    # No recognizable type — fall back to ``unknown`` rather than ``any``
    # so callers are nudged to validate manually.
    return "unknown"


def _inline_object_type(
    schema: Dict[str, Any],
    components: Dict[str, Any],
    *,
    seen: Optional[set] = None,
) -> str:
    """Emit an inline structural object type for an anonymous schema."""
    seen = seen or set()
    props = schema.get("properties", {})
    required = set(schema.get("required") or [])
    parts: List[str] = []
    for key, sub in props.items():
        ts_type = _ts_type_for(sub, components, seen=seen)
        q = "" if key in required else "?"
        # Quote the key so any character is legal in TS object type.
        parts.append(f'"{key}"{q}: {ts_type}')
    if not parts:
        return "Record<string, unknown>"
    extras = schema.get("additionalProperties")
    if isinstance(extras, dict):
        parts.append(
            f"[key: string]: {_ts_type_for(extras, components, seen=seen)}"
        )
    return "{ " + "; ".join(parts) + " }"


# ---------------------------------------------------------------------------
# Model emission.
# ---------------------------------------------------------------------------
def _emit_model(name: str, schema: Dict[str, Any], components: Dict[str, Any]) -> str:
    name = _ts_safe_name(name)
    body = _inline_object_type(schema, components)
    return f"export interface {name} {body}"


# ---------------------------------------------------------------------------
# Operation parsing.
# ---------------------------------------------------------------------------
def _op_path_params(path: str) -> List[Tuple[str, str]]:
    """Return [(name, type)] for path params.

    FastAPI's OpenAPI surface declares these as bare ``{name}`` placeholders
    without an explicit schema, so we treat every one as ``string``.
    """
    out: List[Tuple[str, str]] = []
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == "{":
            j = path.index("}", i)
            out.append((path[i + 1:j], "string"))
            i = j + 1
        else:
            i += 1
    return out


def _op_query_params(
    op: Dict[str, Any], components: Dict[str, Any]
) -> List[Tuple[str, str, bool]]:
    """Return [(name, ts_type, required)] for query parameters."""
    out: List[Tuple[str, str, bool]] = []
    for p in op.get("parameters", []) or []:
        if p.get("in") != "query":
            continue
        name = _ts_safe_name(str(p["name"]))
        required = bool(p.get("required", False))
        schema = p.get("schema", {})
        ts_type = _ts_type_for(schema, components)
        out.append((name, ts_type, required))
    return out


def _op_body_param(
    op: Dict[str, Any], components: Dict[str, Any]
) -> Optional[Tuple[str, str]]:
    """Return (param_name, ts_type) for the JSON body, or None."""
    rb = op.get("requestBody")
    if not rb:
        return None
    content = rb.get("content", {})
    json_body = content.get("application/json")
    if not json_body:
        return None
    schema = json_body.get("schema", {})
    return ("body", _ts_type_for(schema, components))


def _op_return_type(
    op: Dict[str, Any], components: Dict[str, Any]
) -> Tuple[str, str]:
    """Return (return_type, status_label) for the operation's primary success."""
    responses = op.get("responses") or {}
    if "200" in responses:
        r = responses["200"]
        label = "200"
    else:
        for code, r in responses.items():
            if str(code).startswith("2"):
                label = str(code)
                break
        else:
            return ("unknown", "any")
    content = r.get("content", {})
    json_resp = content.get("application/json") or content.get(
        "application/json; charset=utf-8"
    )
    if not json_resp:
        return ("unknown", label)
    schema = json_resp.get("schema", {})
    return (_ts_type_for(schema, components), label)


# ---------------------------------------------------------------------------
# Short operation-name derivation.
# ---------------------------------------------------------------------------
def _short_op_name(op_id: str, path: str, method: str) -> str:
    """Derive a short function name from the operationId / path."""
    if op_id:
        head = op_id.split("_", 1)[0]
        if head and head.isidentifier():
            return head
    # Fallback: the last non-empty path segment, slugified.
    for seg in reversed(path.split("/")):
        if seg and not seg.startswith("{"):
            return seg.replace("-", "_")
    return method.lower()


# ---------------------------------------------------------------------------
# Renderer.
# ---------------------------------------------------------------------------
HEADER = """// ============================================================================
//  NakamaApi TypeScript SDK — AUTO-GENERATED FILE. DO NOT EDIT.
//
//  Regenerate with: python scripts/gen_ts_sdk.py [--url URL] [--output PATH]
//
//  Source of truth: GET /openapi.json.export on a running NakamaApi instance.
//  Runtime deps    : none — uses the platform fetch API directly.
// ============================================================================

export interface NakamaApiOptions {
  /** Base URL of the NakamaApi deployment. No trailing slash. */
  baseUrl: string;
  /** Default headers sent with every request (e.g. { "X-API-Key": "..." }). */
  headers?: Record<string, string>;
  /** Optional fetch override — useful for Node 18 < environments. */
  fetch?: typeof fetch;
}

/** Internal handle shared across groups — never instantiated by callers. */
export interface NakamaApiClient {
  baseUrl: string;
  headers: Record<string, string>;
  _fetch: typeof fetch;
}

/**
 * Thrown by every endpoint when the response status is not 2xx.
 *
 * The original body is kept on ``.body`` (string) so callers can do their
 * own structured parsing. ``status`` is the numeric HTTP status code.
 */
export class NakamaApiError extends Error {
  readonly status: number;
  readonly body: string;
  constructor(status: number, body: string) {
    super(`NakamaApi request failed: ${status} ${body}`);
    this.status = status;
    this.body = body;
    this.name = "NakamaApiError";
  }
}

/**
 * Generic request options accepted by every generated endpoint method.
 * Groups accept their own typed subset of ``params`` for typed query/body
 * input but this base is exposed for advanced use cases.
 */
export interface NakamaApiRequestInit {
  headers?: Record<string, string>;
  fetch?: typeof fetch;
}

"""


def _emit_method(
    method: str,
    path: str,
    op: Dict[str, Any],
    components: Dict[str, Any],
    func_name: str,
) -> str:
    """Emit a single TS method body, returning the literal source string.

    The method is generated as part of a class and therefore references
    ``this._client.baseUrl``, ``this._client.headers`` and ``this._client._fetch``.
    """
    summary = (op.get("summary") or "").strip()
    jsdoc_lines: List[str] = []
    if summary:
        jsdoc_lines.append(f" * {summary}")
    jsdoc_lines.append(f" * @see {method} {path}")
    if op.get("description"):
        for line in str(op["description"]).splitlines():
            jsdoc_lines.append(f" * {line.strip()}")

    path_params = _op_path_params(path)
    query_params = _op_query_params(op, components)
    body = _op_body_param(op, components)

    args: List[str] = []
    for name, _ in path_params:
        args.append(f"{name}: string")

    extra_fields: List[str] = []
    for qname, qtype, qreq in query_params:
        optional = "" if qreq else "?"
        extra_fields.append(f'"{qname}"{optional}: {qtype}')
    if body:
        extra_fields.append(f"body: {body[1]}")

    if extra_fields:
        args.append(
            "params?: { " + "; ".join(extra_fields) + " }"
        )

    return_type, _ = _op_return_type(op, components)

    # ---- Build inner lines ----------------------------------------------
    inner_lines: List[str] = []

    if query_params or body:
        # The function-level ``params`` is optional; coerce to a concrete
        # record so we can index it without strict-mode complaints.
        inner_lines.append("    const p: any = (params as any) ?? {};")

    if query_params:
        inner_lines.append("    const search = new URLSearchParams();")
        for qname, _, _ in query_params:
            inner_lines.append(
                f"    if (p.{qname} !== undefined) "
                f'search.set("{qname}", String(p.{qname}));'
            )
        inner_lines.append("    const qs = search.toString();")
        inner_lines.append("    const suffix = qs ? `?${qs}` : \"\";")
    else:
        inner_lines.append('    const suffix = "";')

    path_expr = path
    for name, _ in path_params:
        path_expr = path_expr.replace("{" + name + "}", "${" + name + "}")
    # Escape any literal backticks in the path expression so TS template
    # literals don't break (paths don't normally contain `` but be defensive).
    path_expr = path_expr.replace("`", "\\`")

    inner_lines.append(
        f"    const url = `${{this._client.baseUrl}}{path_expr}${{suffix}}`;"
    )
    inner_lines.append(
        "    const hdrs: Record<string, string> = {"
        ' ...this._client.headers, "Accept": "application/json"'
        + (', "Content-Type": "application/json"' if body else "")
        + " };"
    )
    inner_lines.append("    const init: RequestInit = {")
    inner_lines.append(f'      method: "{method}",')
    inner_lines.append("      headers: hdrs,")
    if body:
        inner_lines.append(
            "      body: JSON.stringify(p.body),"
        )
    inner_lines.append("    };")
    inner_lines.append(
        "    const res = await this._client._fetch(url, init);"
    )
    inner_lines.append("    if (!res.ok) {")
    inner_lines.append(
        "      const text = await res.text().catch(() => \"\");"
    )
    inner_lines.append(
        "      throw new NakamaApiError("
        "res.status, text || res.statusText);"
    )
    inner_lines.append("    }")
    inner_lines.append(
        f"    return (await res.json()) as {return_type};"
    )

    method_body = "\n".join(inner_lines)

    jsdoc = "/**\n" + "\n".join(jsdoc_lines) + "\n */"
    indented_jsdoc = "\n".join("  " + ln for ln in jsdoc.splitlines())
    signature = (
        f"async {func_name}({', '.join(args)}): Promise<{return_type}>"
    )
    return f"{indented_jsdoc}\n  {signature} {{\n{method_body}\n  }}"


def _render_group_class(group: str, ops: List[Tuple[str, str, str, Dict[str, Any]]]) -> str:
    """Render one group as a TS class.

    ``ops`` is a list of (func_name, method, path, op_dict).
    """
    class_name = group.capitalize()
    lines: List[str] = []
    lines.append(f"export class {class_name} {{")
    lines.append("  private readonly _client: NakamaApiClient;")
    lines.append(f"  constructor(client: NakamaApiClient) {{")
    lines.append("    this._client = client;")
    lines.append("  }")
    lines.append("")
    # Sort by path then method for deterministic output.
    ops_sorted = sorted(ops, key=lambda t: (t[2], t[1]))
    for func_name, method, path, op in ops_sorted:
        lines.append(_emit_method(method, path, op, _components_singleton, func_name))
        lines.append("")
    lines.append("}")
    return "\n".join(lines) + "\n"


# We pass the components dict through to each emitted method via a module-level
# cache. This keeps the renderer pure-ish and avoids threading the dict through
# every helper signature.
_components_singleton: Dict[str, Any] = {}


def _wrap_components_for_render() -> Any:
    """Build a wrapper that injects ``components`` into ``_emit_method``.

    The wrapper returns a fresh function bound to the schema dict so the
    renderer can pass it into ``_render_group_class`` without a circular
    import.
    """
    # No-op helper — the actual emission is in ``_emit_method`` which reads
    # from the module-level ``_components_singleton``. Kept for symmetry.
    return _emit_method


def render(spec: Dict[str, Any]) -> str:
    """Render the full TypeScript SDK source for ``spec``."""
    global _components_singleton
    components = spec.get("components", {}).get("schemas", {}) or {}
    paths = spec.get("paths", {}) or {}
    _components_singleton = components

    # ---- Models ---------------------------------------------------------
    model_lines: List[str] = []
    seen_models: set = set()
    for raw_name, schema in components.items():
        if raw_name in seen_models:
            continue
        seen_models.add(raw_name)
        model_lines.append(_emit_model(raw_name, schema, components))

    # ---- Group operations ----------------------------------------------
    grouped_ops: Dict[str, List[Tuple[str, str, str, Dict[str, Any]]]] = {}

    for path, methods in paths.items():
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            tags = op.get("tags") or []
            if tags and tags[0] in TAG_GROUP:
                group = TAG_GROUP[tags[0]]
            elif tags:
                group = DEFAULT_GROUP
            else:
                group = DEFAULT_GROUP

            op_id = op.get("operationId") or ""
            raw_name = _short_op_name(op_id, path, method)
            # Disambiguate using HTTP method when collision occurs. We track
            # per-group counts.
            key = (group, raw_name)
            grouped_ops.setdefault(group, [])
            existing_names = {entry[0] for entry in grouped_ops[group]}
            if raw_name not in existing_names:
                func_name = raw_name
            else:
                func_name = raw_name + "_" + method.lower()
                # Last-ditch dedupe: append path tail.
                while func_name in existing_names:
                    func_name = func_name + "_x"

            grouped_ops[group].append((func_name, method.upper(), path, op))

    # ---- Top-level NakamaApi class ---------------------------------------
    group_classes: List[str] = []
    for group in GROUP_ORDER:
        if group in grouped_ops:
            group_classes.append(
                _render_group_class(group, grouped_ops[group])
            )
        else:
            # Always emit a stub class so consumers can rely on every
            # group existing on the client.
            stub = (
                f"export class {group.capitalize()} {{\n"
                f"  private readonly _client: NakamaApiClient;\n"
                f"  constructor(client: NakamaApiClient) {{\n"
                f"    this._client = client;\n"
                f"  }}\n"
                f"}}\n"
            )
            group_classes.append(stub)

    class_decl_lines: List[str] = []
    class_decl_lines.append("export class NakamaApi {")
    for group in GROUP_ORDER:
        class_decl_lines.append(
            f"  readonly {group}: {group.capitalize()};"
        )
    class_decl_lines.append("")
    class_decl_lines.append("  constructor(opts: NakamaApiOptions) {")
    class_decl_lines.append(
        "    const client: NakamaApiClient = {"
    )
    class_decl_lines.append(
        "      baseUrl: opts.baseUrl.replace(/\\/$/, \"\"),"
    )
    class_decl_lines.append("      headers: opts.headers ?? {},")
    class_decl_lines.append(
        "      _fetch: opts.fetch ?? ((...args: Parameters<typeof fetch>) => fetch(...args)),"
    )
    class_decl_lines.append("    };")
    for group in GROUP_ORDER:
        class_decl_lines.append(f"    this.{group} = new {group.capitalize()}(client);")
    class_decl_lines.append("  }")
    class_decl_lines.append("}")
    class_decl = "\n".join(class_decl_lines)

    # ---- Stitch file ----------------------------------------------------
    parts: List[str] = []
    parts.append(HEADER)
    parts.append("// -- Component schemas (TypeScript interfaces) --------------------\n\n")
    parts.extend(line + "\n" for line in model_lines)
    parts.append("\n// -- Endpoint groups --------------------------------------------------\n\n")
    parts.extend(group_classes)
    parts.append("\n// -- Top-level client -------------------------------------------------\n\n")
    parts.append(class_decl)
    parts.append(
        "\n// -- Default export --------------------------------------------------\n"
        "export default NakamaApi;\n"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Fetching the spec.
# ---------------------------------------------------------------------------
def fetch_spec(base_url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """GET ``{base_url}/openapi.json.export`` and return the parsed JSON.

    Raises ``RuntimeError`` on any HTTP or parse error so a misconfigured URL
    is loud at codegen time.
    """
    base_url = base_url.rstrip("/")
    url = f"{base_url}/openapi.json.export"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"HTTP {e.code} fetching OpenAPI schema from {url}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not reach {url}: {e.reason}"
        ) from e
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"OpenAPI response from {url} is not valid JSON: {e}"
        ) from e


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------
def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the NakamaApi TypeScript SDK from /openapi.json.export. "
            "Run while the FastAPI app is reachable."
        )
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the running NakamaApi instance (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default="./sdks/ts/src/index.ts",
        help="Destination .ts file (default: %(default)s)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    spec = fetch_spec(args.url)
    rendered = render(spec)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")

    paths = spec.get("paths") or {}
    print(
        f"wrote {out} from {args.url}/openapi.json.export "
        f"({len(paths)} paths, "
        f"{len(spec.get('components', {}).get('schemas', {}))} schemas)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
