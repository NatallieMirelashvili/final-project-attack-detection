"""Factory for LLM clients."""

from __future__ import annotations

import os
from typing import Any, Dict

from agent_redteam.llm.base import LLMClient
from agent_redteam.llm.mock_client import MockLLMClient
from agent_redteam.llm.ollama_client import OllamaLLMClient


def create_llm_client(adapter_config: Dict[str, Any] | None = None) -> LLMClient:
    config = dict(adapter_config or {})
    mode = str(config.get("llm_mode", "mock")).lower().strip()

    if mode == "mock":
        return MockLLMClient(config)

    if mode == "recorded":
        raise NotImplementedError(
            "llm_mode=recorded is not implemented. Use llm_mode=mock for offline runs."
        )

    if mode == "live":
        provider = str(config.get("llm_provider") or "ollama").lower().strip()
        if provider == "ollama":
            return OllamaLLMClient(config)
        if provider in ("openai", "openai_compatible"):
            api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "llm_mode=live with llm_provider=openai requires "
                    "OPENAI_API_KEY or adapter_config.api_key"
                )
            try:
                from agent_redteam.llm.openai_compatible_client import OpenAICompatibleClient
            except ImportError as exc:
                raise RuntimeError(
                    "llm_mode=live with llm_provider=openai requires the optional "
                    "openai package. Install openai or use llm_provider=ollama."
                ) from exc
            return OpenAICompatibleClient(config)
        raise ValueError(
            f"Unsupported llm_provider for live mode: {provider!r}. "
            "Supported: ollama (default), openai."
        )

    raise ValueError(f"Unknown llm_mode: {mode}")
