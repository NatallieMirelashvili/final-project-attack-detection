"""Tests for LLM abstraction layer."""

from __future__ import annotations

import pytest

from agent_redteam.llm.factory import create_llm_client
from agent_redteam.llm.mock_client import MockLLMClient
from agent_redteam.llm.types import Message, ToolSpec


def test_mock_llm_deterministic():
    client = MockLLMClient()
    messages = [Message(role="user", content="hello")]
    r1 = client.complete(messages, seed=42, agent_role="planner", task_id="t1")
    r2 = client.complete(messages, seed=42, agent_role="planner", task_id="t1")
    assert r1.text == r2.text
    assert r1.token_count == r2.token_count


def test_mock_llm_role_dependent():
    client = MockLLMClient()
    messages = [Message(role="user", content="task")]
    planner = client.complete(messages, seed=1, agent_role="planner", task_id="t1")
    retriever = client.complete(messages, seed=1, agent_role="retriever", task_id="t1", tools=[
        ToolSpec(name="retrieve_domain_context", description="search", parameters={}),
    ])
    assert "Plan" in planner.text
    assert retriever.tool_calls or "Retrieval" in retriever.text


def test_mock_llm_usage_counters():
    client = MockLLMClient()
    response = client.complete(
        [Message(role="user", content="x")],
        seed=7,
        agent_role="memory",
        task_id="t2",
    )
    assert response.token_count > 0
    assert response.estimated_cost > 0
    assert response.latency_ms > 0


def test_factory_creates_mock_without_api_key():
    client = create_llm_client({"llm_mode": "mock"})
    assert isinstance(client, MockLLMClient)


def test_live_openai_requires_api_key():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        create_llm_client({"llm_mode": "live", "llm_provider": "openai"})


def test_live_unsupported_provider():
    with pytest.raises(ValueError, match="Unsupported llm_provider"):
        create_llm_client({"llm_mode": "live", "llm_provider": "unknown"})


def test_recorded_mode_not_implemented():
    with pytest.raises(NotImplementedError):
        create_llm_client({"llm_mode": "recorded"})


def test_mock_finalizer_not_answer_template():
    client = MockLLMClient()
    response = client.complete(
        [Message(role="user", content="context")],
        seed=99,
        agent_role="finalizer",
        task_id="t3",
        metadata={"expected_answer": "Paris", "attack_goal": "", "instruction": "capital?"},
    )
    assert "Answer:" not in response.text or "Final response:" in response.text
    assert "Paris" in response.text
