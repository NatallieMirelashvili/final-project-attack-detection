"""Factory for creating agent system adapters."""

from __future__ import annotations

from typing import Any, Dict

from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.agentdojo_adapter import AgentDojoAdapter
from agent_redteam.adapters.agentdojo_real_adapter import AgentDojoRealAdapter
from agent_redteam.adapters.autogen_adapter import AutoGenSyntheticAdapter
from agent_redteam.adapters.crewai_adapter import CrewAISyntheticAdapter
from agent_redteam.adapters.langgraph_adapter import LangGraphSyntheticAdapter
from agent_redteam.adapters.langgraph_real_adapter import LangGraphRealAdapter
from agent_redteam.adapters.mock_adapter import MockAdapter
from agent_redteam.schemas import ExperimentConfig


def create_adapter(
    system_name: str,
    adapter_type: str | None = None,
    adapter_config: Dict[str, Any] | None = None,
    random_seed: int = 42,
) -> AgentSystemAdapter:
    """Create and configure an adapter by system name or explicit adapter type."""
    config = dict(adapter_config or {})
    config.setdefault("random_seed", random_seed)

    name = (adapter_type or system_name or "mock").lower().strip()

    if name in ("mock",):
        adapter: AgentSystemAdapter = MockAdapter()
    elif name in ("agentdojo_real",):
        adapter = AgentDojoRealAdapter()
    elif name in ("agentdojo",):
        adapter = AgentDojoAdapter()
    elif name in ("langgraph_real",):
        adapter = LangGraphRealAdapter()
    elif name in ("langgraph_synthetic", "langgraph"):
        adapter = LangGraphSyntheticAdapter()
    elif name in ("autogen_synthetic", "autogen"):
        adapter = AutoGenSyntheticAdapter()
    elif name in ("crewai_synthetic", "crewai"):
        adapter = CrewAISyntheticAdapter()
    else:
        adapter = MockAdapter()

    adapter.setup(config)
    return adapter


def create_adapter_from_config(config: ExperimentConfig) -> AgentSystemAdapter:
    """Create adapter from experiment configuration."""
    return create_adapter(
        system_name=config.system_name,
        adapter_type=config.adapter_type,
        adapter_config=config.adapter_config,
        random_seed=config.random_seed,
    )
