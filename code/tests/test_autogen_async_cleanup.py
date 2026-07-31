"""Regression tests for async client cleanup around asyncio.run()."""

from __future__ import annotations

import asyncio
import warnings

import pytest

from agent_redteam.llm.async_cleanup import close_async_clients
from agent_redteam.llm.autogen_model_client import OllamaAutoGenChatClient, build_autogen_model_client


class _AsyncCloseClient:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def test_close_async_clients_awaits_client_close():
    client = _AsyncCloseClient()

    async def _run() -> None:
        await close_async_clients([client])

    asyncio.run(_run())
    assert client.closed is True


def test_repeated_asyncio_run_with_async_client_close_has_no_event_loop_closed():
    """Simulate per-task asyncio.run() and ensure clients close before loop exit."""

    async def _run_once() -> None:
        client = _AsyncCloseClient()
        try:
            await asyncio.sleep(0)
        finally:
            await close_async_clients([client])
        assert client.closed is True

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(3):
            asyncio.run(_run_once())

    event_loop_errors = [
        str(item.message)
        for item in caught
        if "Event loop is closed" in str(item.message)
    ]
    assert not event_loop_errors


def test_live_ollama_autogen_client_uses_sync_backed_wrapper():
    client = build_autogen_model_client(
        {
            "llm_mode": "live",
            "llm_provider": "ollama",
            "llm_model": "llama3.2:3b",
        },
        agent_role="planner",
    )
    assert isinstance(client, OllamaAutoGenChatClient)


def test_httpx_async_client_cleanup_before_loop_exit():
    httpx = pytest.importorskip("httpx")

    async def _run_with_client() -> None:
        client = httpx.AsyncClient()
        try:
            await client.aclose()
        finally:
            await close_async_clients([client])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(2):
            asyncio.run(_run_with_client())

    event_loop_errors = [
        str(item.message)
        for item in caught
        if "Event loop is closed" in str(item.message)
    ]
    assert not event_loop_errors
