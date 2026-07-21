"""Source adapters package."""
from __future__ import annotations

import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, List, Optional, TypeVar

from .base import AnimeSource, ComicSource, NovelSource, SourceError
from .registry import (
    anime_source,
    comic_source,
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
    novel_source,
)

__all__ = [
    "AnimeSource",
    "ComicSource",
    "NovelSource",
    "SourceError",
    "anime_source",
    "comic_source",
    "novel_source",
    "list_anime_sources",
    "list_comic_sources",
    "list_novel_sources",
    "with_fallback",
]


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _resolve(kind: str, name: str):
    if kind == "anime":
        return anime_source(name)
    if kind == "comic":
        return comic_source(name)
    return novel_source(name)


def _list(kind: str) -> List[str]:
    if kind == "anime":
        return list_anime_sources()
    if kind == "comic":
        return list_comic_sources()
    return list_novel_sources()


def _is_empty(result: Any) -> bool:
    """A result is "empty" in the user-facing sense.

    * ``None`` → empty
    * ``[]`` / ``{}`` / ``""`` → empty
    * anything truthy → not empty
    """
    if result is None:
        return True
    if isinstance(result, (list, dict, str, tuple, set)) and len(result) == 0:
        return True
    return False


def with_fallback(
    kind: str,
    timeout: float = 10.0,
) -> Callable[[F], F]:
    """Decorator factory: wrap a source method to fall back across the registry.

    Usage::

        @with_fallback("comic")
        async def search_comic(primary: str, query: str):
            src = comic_source(primary)
            if src is None:
                raise SourceError(f"unknown comic source {primary!r}")
            return await src.search(query)

    The decorated function must accept a source name as the FIRST positional
    argument (e.g. ``"kiryuu"``) and any further args/kwargs to forward.

    Behavior:
      * Try the primary source first by calling the decorated function.
      * If it raises ``SourceError`` or returns an empty result, try the next
        source of the same ``kind`` from the registry.
      * All sources are tried concurrently via ``asyncio.gather`` with a
        per-source ``asyncio.wait_for`` timeout. The first non-empty result
        wins; the rest are cancelled.
      * If every source returns empty/None/errors, raise ``SourceError``
        with a descriptive message so the router can surface a 502 instead
        of silently returning ``[]``.

    The decorator is generic: it works on any async function whose first
    argument is the source name to try first.
    """
    if kind not in ("anime", "comic", "novel"):
        raise ValueError(
            f"with_fallback: invalid kind {kind!r}; expected one of anime/comic/novel"
        )

    def decorator(fn: F) -> F:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError(
                f"with_fallback: '{fn.__name__}' must be an async function"
            )

        @functools.wraps(fn)
        async def wrapper(primary: str, *args: Any, **kwargs: Any) -> Any:
            order: List[str] = []
            seen = set()
            if primary:
                order.append(primary)
                seen.add(primary)
            for name in _list(kind):
                if name not in seen:
                    order.append(name)
                    seen.add(name)

            if not order:
                raise SourceError(
                    f"No {kind} sources registered for fallback"
                )

            async def _attempt(name: str) -> tuple[str, Any]:
                """Run the wrapped fn with a timeout and classify the outcome.

                Returns ``(name, _Empty())`` on empty/timeout/error so the
                outer loop can keep trying the next source.
                """
                try:
                    result = await asyncio.wait_for(
                        fn(name, *args, **kwargs),
                        timeout=timeout,
                    )
                    if _is_empty(result):
                        return name, _Empty("empty")
                    return name, result
                except asyncio.TimeoutError:
                    return name, _Empty("timeout")
                except SourceError as e:
                    return name, _Empty(str(e))
                except Exception as e:  # noqa: BLE001 — defensive
                    return name, _Empty(f"{type(e).__name__}: {e}")

            # Start one task per source. We cancel any still-running tasks as
            # soon as a non-empty result is in hand so we don't burn cycles.
            tasks = {
                asyncio.ensure_future(_attempt(name)): name for name in order
            }

            pending = set(tasks.keys())
            winner: Optional[Any] = None
            winner_name: Optional[str] = None
            failures: list[tuple[str, str]] = []

            try:
                while pending:
                    done, pending = await asyncio.wait(
                        pending, return_when=asyncio.FIRST_COMPLETED
                    )
                    for t in done:
                        try:
                            name, result = t.result()
                        except Exception as e:  # noqa: BLE001
                            failures.append(("?", f"{type(e).__name__}: {e}"))
                            continue
                        if isinstance(result, _Empty):
                            failures.append((name, result.reason))
                            continue
                        winner = result
                        winner_name = name
                        break
                    if winner is not None:
                        # Cancel anything still in flight.
                        for t in pending:
                            t.cancel()
                        # Drain cancellations quietly.
                        if pending:
                            await asyncio.gather(*pending, return_exceptions=True)
                        break
            finally:
                # Best-effort cleanup.
                for t in list(tasks.keys()):
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*tasks.keys(), return_exceptions=True)

            if winner is not None:
                return winner

            if failures:
                last_name, last_err = failures[-1]
                raise SourceError(
                    f"All {kind} sources returned empty/failed for "
                    f"{fn.__name__}(); last failure from '{last_name}': {last_err}"
                )
            return []

        setattr(wrapper, "__fallback_kind__", kind)
        setattr(wrapper, "__fallback_timeout__", timeout)
        setattr(wrapper, "__fallback_wrapped__", True)
        return wrapper  # type: ignore[return-value]

    return decorator


class _Empty:
    """Sentinel returned by the per-source attempt when the result is unusable."""

    __slots__ = ("reason",)

    def __init__(self, reason: str) -> None:
        self.reason = reason
