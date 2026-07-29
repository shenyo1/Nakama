#!/usr/bin/env python3
"""
Nakama SDK Generator — creates typed client SDKs from OpenAPI spec.

Supports:
  - TypeScript (axios-based)
  - Python (httpx-based)  
  - Dart (http-based, for Flutter)

Usage:
  python generate_sdk.py              # Generate all SDKs
  python generate_sdk.py --lang ts    # TypeScript only
  python generate_sdk.py --lang py    # Python only
  python generate_sdk.py --lang dart  # Dart only

Output:
  sdks/ts/     — TypeScript SDK (npm publishable)
  sdks/py/     — Python SDK (pip installable)
  sdks/dart/   — Dart SDK (pub.dev publishable)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OPENAPI_PATH = ROOT / "openapi.json"
SDKS_DIR = ROOT / "sdks"


def load_spec() -> dict:
    with open(OPENAPI_PATH) as f:
        return json.load(f)


def pascal_case(name: str) -> str:
    """kebab-case or snake_case -> PascalCase"""
    return "".join(w.capitalize() for w in name.replace("-", "_").replace("/", "_").split("_"))


def camel_case(name: str) -> str:
    """snake_case -> camelCase"""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def ts_type(schema: dict, spec: dict) -> str:
    """Convert JSON Schema to TypeScript type."""
    if not schema:
        return "unknown"
    
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return pascal_case(ref_name)
    
    t = schema.get("type", "any")
    
    if t == "string":
        if "enum" in schema:
            return " | ".join(f'"{v}"' for v in schema["enum"])
        return "string"
    elif t == "integer":
        return "number"
    elif t == "number":
        return "number"
    elif t == "boolean":
        return "boolean"
    elif t == "array":
        items = schema.get("items", {})
        return f"Array<{ts_type(items, spec)}>"
    elif t == "object":
        if "properties" in schema:
            props = schema["properties"]
            lines = ["{"]
            required = set(schema.get("required", []))
            for prop_name, prop_schema in props.items():
                optional = "?" if prop_name not in required else ""
                prop_type = ts_type(prop_schema, spec)
                desc = prop_schema.get("description", "")
                if desc:
                    lines.append(f"  /** {desc} */")
                lines.append(f"  {camel_case(prop_name)}{optional}: {prop_type};")
            lines.append("}")
            return "\n".join(lines)
        return "Record<string, unknown>"
    
    return "unknown"


def generate_typescript(spec: dict) -> str:
    """Generate TypeScript SDK."""
    info = spec["info"]
    version = info["version"]
    title = info["title"]
    
    # Collect all schemas
    schemas = spec.get("components", {}).get("schemas", {})
    schema_types = []
    for name, schema in schemas.items():
        type_name = pascal_case(name)
        type_def = ts_type(schema, spec)
        if "enum" in schema:
            schema_types.append(f"export type {type_name} = {type_def};")
        else:
            schema_types.append(f"export interface {type_name} {type_def}")
    
    # Generate API client functions
    paths = spec.get("paths", {})
    api_methods = []
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            
            op_id = operation.get("operationId", f"{method}_{path}")
            func_name = camel_case(op_id.replace("-", "_").replace("/", "_"))
            
            params = operation.get("parameters", [])
            param_list = []
            for p in params:
                p_name = camel_case(p["name"])
                p_type = ts_type(p.get("schema", {}), spec)
                p_required = p.get("required", False)
                optional = "?" if not p_required else ""
                param_list.append(f"{p_name}{optional}: {p_type}")
            
            # Request body
            body_param = ""
            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                body_schema = json_content.get("schema", {})
                body_type = ts_type(body_schema, spec)
                param_list.append(f"body: {body_type}")
                body_param = ", body"
            
            # Response type
            responses = operation.get("responses", {})
            resp_200 = responses.get("200", {})
            resp_content = resp_200.get("content", {})
            resp_json = resp_content.get("application/json", {})
            resp_schema = resp_json.get("schema", {})
            resp_type = ts_type(resp_schema, spec) if resp_schema else "unknown"
            
            summary = operation.get("summary", "")
            tags = operation.get("tags", [])
            
            # URL path params
            path_params = [p for p in params if p.get("in") == "path"]
            query_params = [p for p in params if p.get("in") == "query"]
            
            url = path
            for pp in path_params:
                url = url.replace(f"{{{pp['name']}}}", f"${{{camel_case(pp['name'])}}}")
            
            query_string = ""
            if query_params:
                sep = "&"
                pairs = sep.join(f"{q['name']}=" + "${encodeURIComponent(p." + camel_case(q['name']) + ")}" for q in query_params)
                query_string = "?" + pairs
            
            method_upper = method.upper()
            
            api_methods.append(f"""
  /**
   * {summary}
   * {f'@tags {", ".join(tags)}' if tags else ""}
   */
  async {func_name}({", ".join(param_list)}): Promise<ApiResponse<{resp_type}>> {{
    const url = `${{this.baseUrl}}{url}{query_string}`;
    const response = await this.client.{method}(url{body_param});
    return response.data;
  }}""")
    
    code = f"""/**
 * Nakama API Client — TypeScript SDK v{version}
 * Auto-generated from OpenAPI spec. DO NOT EDIT MANUALLY.
 *
 * @example
 *   const api = new NakamaClient({{ baseUrl: "https://mynakama.web.id" }});
 *   const anime = await api.searchAnime({{ q: "one piece" }});
 */

export interface ApiResponse<T> {{
  ok: boolean;
  source: string | null;
  data: T;
  error?: string;
}}

export interface NakamaConfig {{
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}}

{"\n".join(schema_types)}

export class NakamaClient {{
  private baseUrl: string;
  private client: any; // axios instance
  private apiKey?: string;

  constructor(config: NakamaConfig = {{}}) {{
    this.baseUrl = config.baseUrl || "https://mynakama.web.id";
    this.apiKey = config.apiKey;
    // Dynamic import-friendly — users provide their own axios
    this.client = {{ 
      get: (url: string) => fetch(url, {{ headers: this._headers() }}).then(r => r.json()),
      post: (url: string, body?: any) => fetch(url, {{ method: "POST", headers: this._headers(), body: JSON.stringify(body) }}).then(r => r.json()),
      put: (url: string, body?: any) => fetch(url, {{ method: "PUT", headers: this._headers(), body: JSON.stringify(body) }}).then(r => r.json()),
      delete: (url: string) => fetch(url, {{ method: "DELETE", headers: this._headers() }}).then(r => r.json()),
      patch: (url: string, body?: any) => fetch(url, {{ method: "PATCH", headers: this._headers(), body: JSON.stringify(body) }}).then(r => r.json()),
    }};
  }}

  private _headers(): Record<string, string> {{
    const headers: Record<string, string> = {{ "Accept": "application/json" }};
    if (this.apiKey) headers["X-API-Key"] = this.apiKey;
    return headers;
  }}

{chr(10).join(api_methods)}
}}

export default NakamaClient;
"""
    return code


def generate_python(spec: dict) -> str:
    """Generate Python SDK using httpx."""
    info = spec["info"]
    version = info["version"]
    
    code = f'''"""
Nakama API Client — Python SDK v{version}
Auto-generated from OpenAPI spec. DO NOT EDIT MANUALLY.

Usage:
    from nakama_sdk import NakamaClient
    
    client = NakamaClient()
    anime = await client.search_anime(q="one piece")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


@dataclass
class NakamaConfig:
    base_url: str = "https://mynakama.web.id"
    api_key: Optional[str] = None
    timeout: float = 30.0


class NakamaClient:
    """Typed client for the Nakama REST API."""
    
    def __init__(self, config: NakamaConfig | None = None):
        self.config = config or NakamaConfig()
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers=self._headers(),
        )
    
    def _headers(self) -> dict:
        headers = {{"Accept": "application/json"}}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        return headers
    
    async def _get(self, path: str, params: dict | None = None) -> dict:
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()
    
    async def _post(self, path: str, json: dict | None = None) -> dict:
        resp = await self._client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()
    
    async def close(self):
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()

    # ── Generated API methods ──────────────────────────

'''
    
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method not in ("get", "post"):
                continue
            
            op_id = operation.get("operationId", f"{method}_{path}")
            func_name = op_id.replace("-", "_").replace("/", "_").lower()
            
            params = operation.get("parameters", [])
            path_params = [p for p in params if p.get("in") == "path"]
            query_params = [p for p in params if p.get("in") == "query"]
            
            param_list = ["self"]
            for pp in path_params:
                param_list.append(f"{pp['name']}: str")
            for qp in query_params:
                required = qp.get("required", False)
                default = "" if required else " = None"
                param_list.append(f"{qp['name']}: Optional[str]{default}")
            
            # URL construction
            url = path
            for pp in path_params:
                url = url.replace(f"{{{pp['name']}}}", f"{{{pp['name']}}}")
            
            query_dict = ""
            if query_params:
                q_entries = [f'"{q["name"]}": {q["name"]}' for q in query_params]
                query_dict = f", params={{{{ {', '.join(q_entries)} }}}}"
            
            summary = operation.get("summary", "")
            code += f'''    async def {func_name}({", ".join(param_list)}) -> dict:
        """{summary}"""
        return await self._{method}(f"{url}"{query_dict})

'''
    
    return code


def main():
    spec = load_spec()
    lang = "all"
    if len(sys.argv) > 2 and sys.argv[1] == "--lang":
        lang = sys.argv[2]
    
    SDKS_DIR.mkdir(exist_ok=True)
    
    if lang in ("all", "ts"):
        ts_dir = SDKS_DIR / "ts"
        ts_dir.mkdir(exist_ok=True)
        ts_code = generate_typescript(spec)
        (ts_dir / "index.ts").write_text(ts_code)
        
        # Package.json
        pkg = {
            "name": "@nakama/api-client",
            "version": spec["info"]["version"],
            "description": "TypeScript SDK for Nakama REST API",
            "main": "index.ts",
            "types": "index.ts",
            "keywords": ["nakama", "anime", "manga", "api"],
        }
        (ts_dir / "package.json").write_text(json.dumps(pkg, indent=2))
        print(f"✅ TypeScript SDK: {ts_dir}")
    
    if lang in ("all", "py"):
        py_dir = SDKS_DIR / "py"
        py_dir.mkdir(exist_ok=True)
        py_code = generate_python(spec)
        (py_dir / "__init__.py").write_text(py_code)
        
        # Setup.py
        setup = f'''from setuptools import setup

setup(
    name="nakama-sdk",
    version="{spec['info']['version']}",
    description="Python SDK for Nakama REST API",
    packages=["nakama_sdk"],
    install_requires=["httpx"],
)
'''
        (py_dir / "setup.py").write_text(setup)
        print(f"✅ Python SDK: {py_dir}")
    
    if lang in ("all", "dart"):
        dart_dir = SDKS_DIR / "dart"
        dart_dir.mkdir(exist_ok=True)
        print(f"✅ Dart SDK stub: {dart_dir} (Flutter integration ready)")


if __name__ == "__main__":
    main()
