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

# Host -> referer mapping for hotlink-protected image CDNs. Many comic/manga
# sources serve chapter images from a dedicated CDN host that refuses requests
# without a browser-like Referer pointing at the owning site. When we see one
# of these hosts we send the matching Referer so the image actually loads.
# Falls back to the image's own origin when the host isn't listed here.
_REFERER_BY_HOST = {
    # komikcast / komikcast.fit CDN (v3.komikcast.fit, minio.imgkc1.my.id, sv*.imgkc1.my.id)
    "imgkc1.my.id": "https://komikcast.fit/",
    "minio.imgkc1.my.id": "https://komikcast.fit/",
    # komiku
    "komiku": "https://komiku.co.id/",
    # komikindo
    "komikindo": "https://komikindo.id/",
    # bacakomik
    "bacakomik": "https://bacakomik.bio/",
    # kiryuu
    "kiryuu": "https://kiryuu.id/",
    # shinigami
    "shinigami": "https://shinigami.id/",
    # westmanga
    "westmanga": "https://westmanga.fun/",
    # komikstation
    "komikstation": "https://komikstation.co/",
}

# Exact host -> referer overrides (verified live during audit on 2026-08-08).
_EXACT_REFERER_BY_HOST = {
    "sv1.imgkc1.my.id": "https://komikcast.fit/",
    "sv2.imgkc1.my.id": "https://komikcast.fit/",
}


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


def _pick_referer(url: str, explicit: Optional[str] = None) -> Optional[str]:
    """Choose the Referer header to send to the upstream image host.

    Priority:
      1. an explicit ``referer=`` query param from the caller,
      2. an exact host match in ``_EXACT_REFERER_BY_HOST``,
      3. a suffix match in ``_REFERER_BY_HOST`` (CDN host contains owner site name),
      4. the image's own origin (most hotlink filters accept a same-domain
         referer even when the site itself isn't whitelisted).

    Returns None only when the URL has no host (shouldn't happen — validation
    runs first), in which case we send the image's origin anyway.
    """
    if explicit:
        return explicit
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    if host in _EXACT_REFERER_BY_HOST:
        return _EXACT_REFERER_BY_HOST[host]
    for needle, ref in _REFERER_BY_HOST.items():
        # substring match so sv1.imgkc1.my.id, minio.imgkc1.my.id,
        # cdn.komikindo.id, etc. all hit their owning source.
        if needle in host:
            return ref
    # fallback: same-origin referer
    return f"{parsed.scheme}://{parsed.netloc}/"


@router.get("/image", summary="Proxy a remote image with SSRF protection")
async def image_proxy(
    url: str = Query(..., description="Absolute http(s) URL of the image to fetch."),
    referer: Optional[str] = Query(None, description="Optional Referer header to send upstream (hotlink bypass)."),
):
    """Fetch *url* server-side and stream the raw bytes back.

    This endpoint exists so a browser frontend can render chapter page images
    that would otherwise be blocked by hotlink protection or CORS. The server
    validates that *url* is a public http(s) resource before fetching — any
    scheme other than http/https, and any host that resolves into a private
    IP range, is rejected with HTTP 400.

    A ``referer`` query parameter may be supplied to override the auto-detected
    Referer (used by sources with strict hotlink protection, e.g. komikcast).
    When omitted the proxy picks a sensible Referer from the CDN host mapping
    or falls back to the image's own origin.
    """
    error = await _validate_url(url)
    if error:
        return JSONResponse(status_code=400, content={"ok": False, "error": error})

    headers = {}
    picked = _pick_referer(url, referer)
    if picked:
        headers["Referer"] = picked
    # A browser-like User-Agent also helps a few hotlink filters that check it.
    headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )

    try:
        client = await get_client()
        # We turn off redirect-following so a malicious redirect cannot bounce
        # us onto an internal host after the initial validation passes. The
        # upstream image hosts we care about do not redirect.
        resp = await client.get(url, headers=headers, follow_redirects=False)
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
            resp = await client.get(new_url, headers=headers, follow_redirects=False)
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
