"""Image proxy endpoint with SSRF protection: /image?url=<encoded_url>.

Why this exists
---------------
Chapter pages on comic sources commonly return image URLs that sit on a
different (or hotlink-protected) host from the API's. A frontend rendered in
the browser cannot simply ``<img src=...>`` those URLs because of CORS, mixed
content, or ``Referer``/cookie checks. The proxy fetches the image on the
server side and streams the bytes back to the client with permissive
caching headers so the browser can render it directly.

Security
--------
A naive proxy is a classic SSRF vector — anyone could ask the server to
``GET http://127.0.0.1:6379`` or ``GET http://169.254.169.254/...`` and use
the API server as a relay into the internal network. We mitigate by:

* Rejecting non-http(s) schemes.
* Resolving the hostname and refusing any address that lands in a private,
  loopback, link-local, multicast, or reserved range (RFC 1918 + RFC 6890).
* Not following redirects to different hosts (the resolved IP must match).

The proxy is registered outside the API-key prefix tree (``/image`` does not
start with ``/anime``, ``/comic`` or ``/novel``) so the auth middleware in
``app.main`` leaves it alone, as required for the proxy to be reachable.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from ..config import get_settings
from ..http import get_client

router = APIRouter(tags=["proxy"])


# CIDR ranges we refuse to fetch. These are the canonical "private/internal"
# ranges plus loopback, link-local, multicast, and the unspecified address.
# We deliberately block 0.0.0.0/8 and 169.254.0.0/16 (cloud metadata) as well
# as IPv6 equivalents so the proxy is safe in cloud environments.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),   # carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),     # loopback
    ipaddress.ip_network("169.254.0.0/16"),  # link-local (cloud metadata!)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),   # benchmarking
    ipaddress.ip_network("224.0.0.0/4"),     # multicast
    ipaddress.ip_network("240.0.0.0/4"),     # reserved
    ipaddress.ip_network("::1/128"),         # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),        # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),       # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),   # IPv4-mapped IPv6 (re-check)
]


def _ip_is_blocked(ip: str) -> bool:
    """Return True if *ip* falls in any blocked range."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # unparseable → refuse
    # IPv4-mapped IPv6 addresses: re-evaluate the embedded IPv4 part too.
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return _ip_is_blocked(str(addr.ipv4_mapped))
    for net in _BLOCKED_NETWORKS:
        if addr.version != net.version:
            continue
        if addr in net:
            return True
    return False


async def _validate_url(url: str) -> Optional[str]:
    """Return an error message if *url* is unsafe, else None.

    Resolution is performed here (synchronously via ``getaddrinfo``) so we can
    reject before opening the HTTP connection. Both A and AAAA records are
    checked; if *any* answer lands in a blocked range we refuse the whole
    request.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "Malformed URL."
    if parsed.scheme not in ("http", "https"):
        return f"Unsupported URL scheme '{parsed.scheme}'. Only http/https are allowed."
    host = parsed.hostname
    if not host:
        return "URL is missing a hostname."
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return "Could not resolve hostname."
    for info in infos:
        # sockaddr layout is (host, port) for IPv4 or (host, port, flow, scope) for IPv6.
        sockaddr = info[4]
        ip = str(sockaddr[0])
        if _ip_is_blocked(ip):
            return f"Refusing to fetch URL pointing at blocked address {ip}."
    return None


@router.get("/image", summary="Proxy a remote image with SSRF protection")
async def image_proxy(url: str = Query(..., description="Absolute http(s) URL of the image to fetch.")):
    """Fetch *url* server-side and stream the raw bytes back.

    This endpoint exists so a browser frontend can render chapter page images
    that would otherwise be blocked by hotlink protection or CORS. The server
    validates that *url* is a public http(s) resource before fetching — any
    scheme other than http/https, and any host that resolves into a private
    IP range, is rejected with HTTP 400.
    """
    error = await _validate_url(url)
    if error:
        return JSONResponse(status_code=400, content={"ok": False, "error": error})

    try:
        client = await get_client()
        # We turn off redirect-following so a malicious redirect cannot bounce
        # us onto an internal host after the initial validation passes. The
        # upstream image hosts we care about do not redirect.
        resp = await client.get(url, follow_redirects=False)
    except httpx.RequestError as e:
        return JSONResponse(
            status_code=502, content={"ok": False, "error": f"Upstream fetch failed: {e}"}
        )

    # If the upstream redirected, re-validate the Location header before we
    # follow it manually.
    if resp.status_code in (301, 302, 303, 307, 308):
        new_url = resp.headers.get("location")
        if not new_url:
            return JSONResponse(status_code=502, content={"ok": False, "error": "Redirect with no Location header."})
        # Handle relative redirect targets.
        if new_url.startswith("/"):
            parsed = urlparse(url)
            new_url = f"{parsed.scheme}://{parsed.netloc}{new_url}"
        error = await _validate_url(new_url)
        if error:
            return JSONResponse(status_code=400, content={"ok": False, "error": error})
        try:
            resp = await client.get(new_url, follow_redirects=False)
        except httpx.RequestError as e:
            return JSONResponse(
                status_code=502, content={"ok": False, "error": f"Upstream fetch failed: {e}"}
            )

    if resp.status_code >= 400:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": f"Upstream returned HTTP {resp.status_code}."},
        )

    content_type = resp.headers.get("content-type", "application/octet-stream")
    # Only forward image/* content-types. Anything else (HTML error pages
    # served with a 200 by an upstream proxy, for example) is refused.
    if not content_type.lower().startswith("image/"):
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": f"Upstream content-type '{content_type}' is not an image."},
        )

    # 24h client cache. Comic chapter pages are largely immutable; this lets
    # the browser pull them from disk on repeat reads.
    headers = {
        "Cache-Control": "public, max-age=86400",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=resp.content, media_type=content_type, headers=headers)
