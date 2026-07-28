"""Offline validation tests for Ollama live LLM configs."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_redteam.experiments.experiment_metadata import build_experiment_metadata
from agent_redteam.experiments.runner import load_config
from agent_redteam.llm.factory import create_llm_client
from agent_redteam.llm.ollama_client import OllamaLLMClient
from agent_redteam.llm.ollama_preflight import run_preflight
from agent_redteam.llm.types import Message

OLLAMA_SMOKE_CONFIGS = [
    "langgraph_real_llm_ollama_leakage_smoke.yaml",
    "langgraph_real_llm_ollama_external_leakage_smoke.yaml",
    "langgraph_real_llm_ollama_degradation_smoke.yaml",
    "agentdojo_real_llm_ollama_leakage_smoke.yaml",
    "agentdojo_real_llm_ollama_external_leakage_smoke.yaml",
    "agentdojo_real_llm_ollama_degradation_smoke.yaml",
]

OLLAMA_MEDIUM_CONFIGS = [
    "langgraph_real_llm_ollama_leakage_medium.yaml",
    "langgraph_real_llm_ollama_external_leakage_medium.yaml",
    "langgraph_real_llm_ollama_degradation_medium.yaml",
    "agentdojo_real_llm_ollama_leakage_medium.yaml",
    "agentdojo_real_llm_ollama_external_leakage_medium.yaml",
    "agentdojo_real_llm_ollama_degradation_medium.yaml",
]

REQUIRED_ADAPTER_FIELDS = {
    "integration_mode": "llm",
    "llm_mode": "live",
    "llm_provider": "ollama",
    "llm_model": "llama3.2:3b",
    "ollama_base_url": "http://localhost:11434",
}


def _configs_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "configs"


def _assert_ollama_adapter_config(cfg, *, num_tasks: int, num_iterations: int) -> None:
    assert cfg.num_tasks == num_tasks
    assert cfg.num_iterations == num_iterations
    assert cfg.attack_generator == "auto_research"
    assert cfg.attack_generator_version == "v2"
    assert cfg.random_seed == 42

    adapter = cfg.adapter_config or {}
    for key, expected in REQUIRED_ADAPTER_FIELDS.items():
        assert adapter.get(key) == expected, f"{cfg.experiment_name}: {key}={adapter.get(key)!r}"

    assert float(adapter.get("temperature", -1)) == 0.0

    weights = cfg.scoring_weights or {}
    assert "latency_increase" not in weights


@pytest.mark.parametrize("name", OLLAMA_SMOKE_CONFIGS)
def test_ollama_smoke_configs_are_valid(name: str):
    cfg = load_config(_configs_dir() / name)
    _assert_ollama_adapter_config(cfg, num_tasks=2, num_iterations=2)
    meta = build_experiment_metadata(cfg)
    assert meta["integration_mode"] == "llm"
    assert meta["llm_mode"] == "live"
    assert meta["llm_provider"] == "ollama"
    assert meta["llm_model"] == "llama3.2:3b"


@pytest.mark.parametrize("name", OLLAMA_MEDIUM_CONFIGS)
def test_ollama_medium_configs_are_valid(name: str):
    cfg = load_config(_configs_dir() / name)
    _assert_ollama_adapter_config(cfg, num_tasks=8, num_iterations=12)
    meta = build_experiment_metadata(cfg)
    assert meta["integration_mode"] == "llm"
    assert meta["llm_mode"] == "live"
    assert meta["llm_provider"] == "ollama"
    assert meta["llm_model"] == "llama3.2:3b"


def test_factory_live_defaults_to_ollama_client():
    client = create_llm_client({"llm_mode": "live"})
    assert isinstance(client, OllamaLLMClient)
    assert client.model == "llama3.2:3b"


def test_preflight_returns_nonzero_when_unreachable():
    exit_code, lines = run_preflight(
        base_url="http://127.0.0.1:59999",
        model="llama3.2:3b",
    )
    assert exit_code == 1
    text = "\n".join(lines)
    assert "not reachable" in text.lower() or "fail" in text.lower()
    assert "ollama pull llama3.2:3b" in text


@pytest.mark.skipif(
    __import__("agent_redteam.llm.ollama_client", fromlist=["is_ollama_running"]).is_ollama_running(),
    reason="Ollama is running; unreachable error test requires Ollama to be down",
)
def test_ollama_complete_error_when_unreachable():
    client = OllamaLLMClient(
        {
            "ollama_base_url": "http://127.0.0.1:59999",
            "llm_model": "llama3.2:3b",
        }
    )
    with pytest.raises(RuntimeError, match="Cannot connect to Ollama"):
        client.complete([Message(role="user", content="ping")])


def test_ollama_complete_error_mentions_pull_when_unreachable():
    client = OllamaLLMClient(
        {
            "ollama_base_url": "http://127.0.0.1:59999",
            "llm_model": "llama3.2:3b",
        }
    )
    with pytest.raises(RuntimeError) as exc_info:
        client.complete([Message(role="user", content="ping")])
    assert "ollama pull llama3.2:3b" in str(exc_info.value).lower() or "ollama serve" in str(
        exc_info.value
    ).lower()
