"""Optional integration tests for Ollama live LLM client."""

from __future__ import annotations

import pytest

from agent_redteam.llm.factory import create_llm_client
from agent_redteam.llm.ollama_client import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    OllamaLLMClient,
    is_ollama_model_available,
    is_ollama_running,
)
from agent_redteam.llm.types import Message


pytestmark = pytest.mark.skipif(
    not is_ollama_running(),
    reason="Ollama is not running at http://localhost:11434",
)


@pytest.fixture(scope="module")
def ollama_model() -> str:
    model = DEFAULT_OLLAMA_MODEL
    if not is_ollama_model_available(model):
        pytest.skip(
            f"Ollama model {model!r} is not pulled locally. Run: ollama pull {model}"
        )
    return model


def test_ollama_is_reachable():
    assert is_ollama_running(DEFAULT_OLLAMA_BASE_URL)


def test_ollama_model_available(ollama_model: str):
    assert is_ollama_model_available(ollama_model)


def test_ollama_simple_completion(ollama_model: str):
    client = OllamaLLMClient({"llm_model": ollama_model, "temperature": 0.0})
    response = client.complete(
        [Message(role="user", content="Reply with exactly the word: pong")],
        agent_role="test",
    )
    assert response.text.strip()
    assert response.estimated_cost == 0.0
    assert response.metadata.get("provider") == "ollama"
    assert response.metadata.get("model") == ollama_model


def test_factory_creates_ollama_client(ollama_model: str):
    client = create_llm_client(
        {
            "llm_mode": "live",
            "llm_provider": "ollama",
            "llm_model": ollama_model,
            "temperature": 0.0,
        }
    )
    assert isinstance(client, OllamaLLMClient)


def test_live_mode_defaults_to_ollama(ollama_model: str):
    client = create_llm_client({"llm_mode": "live", "llm_model": ollama_model})
    assert isinstance(client, OllamaLLMClient)
