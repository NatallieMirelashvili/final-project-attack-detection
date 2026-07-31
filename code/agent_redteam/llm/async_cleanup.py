"""Helpers for closing async HTTP clients before an event loop shuts down."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable


async def close_async_clients(clients: Iterable[Any]) -> None:
    """Await ``close()`` on model clients that expose an async cleanup hook."""
    for client in clients:
        close = getattr(client, "close", None)
        if not callable(close):
            continue
        result = close()
        if asyncio.iscoroutine(result):
            await result
