"""
Tiny in-process TTL cache.

Used to avoid re-spending Hub tokens / re-hitting rate limits on read-style
calls that users poll repeatedly (e.g. usage, analytics). Process-local and
best-effort — fine for a single-service deployment; swap for Redis if the app
is ever scaled horizontally.
"""

from __future__ import annotations

import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}


def get(key: str) -> Any | None:
    item = _store.get(key)
    if item is None:
        return None
    expires_at, value = item
    if time.monotonic() >= expires_at:
        _store.pop(key, None)
        return None
    return value


def set(key: str, value: Any, ttl_seconds: float) -> None:
    _store[key] = (time.monotonic() + ttl_seconds, value)


def clear() -> None:
    _store.clear()
