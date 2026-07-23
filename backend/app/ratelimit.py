"""Rate limiter instance (slowapi).

Kept in its own module to avoid a circular import between ``app.main`` and
``app.routers.*`` — both need the limiter, but main imports the routers.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP limiter. Default limit (60/minute) is read from Settings.rate_limit at
# each decorated endpoint; this object only provides the key function.
limiter = Limiter(key_func=get_remote_address)
