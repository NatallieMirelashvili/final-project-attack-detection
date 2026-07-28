"""Bridge project MockLLMClient / Ollama to official CrewAI LLM interface."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from crewai.llms.base_llm import BaseLLM
from pydantic import Field, PrivateAttr, model_validator

from agent_redteam.llm.mock_client import MockLLMClient
from agent_redteam.llm.types import Message

CREWAI_ROLE_TO_MOCK = {
    "manager": "planner",
    "researcher": "retriever",
    "worker": "worker",
    "memory": "memory",
    "finalizer": "finalizer",
}


def build_crewai_llm(adapter_config: Dict[str, Any], *, agent_role: str):
    """Return an official CrewAI LLM instance for one agent role."""
    mode = str(adapter_config.get("llm_mode", "mock")).lower()
    if mode == "mock":
        return ProjectMockCrewAILLM(
            model="project-mock",
            agent_role=agent_role,
            adapter_config=adapter_config,
            temperature=float(adapter_config.get("temperature", 0.0)),
        )

    from crewai import LLM

    model = str(adapter_config.get("llm_model", "llama3.2:3b"))
    base_url = str(adapter_config.get("ollama_base_url", "http://localhost:11434")).rstrip("/") + "/v1"
    temperature = float(adapter_config.get("temperature", 0.0))
    return LLM(
        model=f"ollama/{model}",
        base_url=base_url,
        api_key="ollama",
        temperature=temperature,
    )


class ProjectMockCrewAILLM(BaseLLM):
    """Official CrewAI-compatible LLM backed by project MockLLMClient."""

    llm_type: str = "project_mock"
    agent_role: str = "manager"
    adapter_config: Dict[str, Any] = Field(default_factory=dict)

    _mock: MockLLMClient = PrivateAttr()
    _task_context: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _token_usage: Dict[str, int] = PrivateAttr(
        default_factory=lambda: {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "successful_requests": 0,
        }
    )

    @model_validator(mode="after")
    def _init_mock_client(self) -> "ProjectMockCrewAILLM":
        self._mock = MockLLMClient(self.adapter_config)
        self._task_context = dict(self.adapter_config.get("task_context") or {})
        return self

    def set_task_context(self, context: Dict[str, Any]) -> None:
        self._task_context = dict(context)

    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: List[dict] | None = None,
        callbacks: List[Any] | None = None,
        available_functions: Dict[str, Any] | None = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> Union[str, Any]:
        del tools, callbacks, available_functions, from_task, from_agent, response_model
        if isinstance(messages, str):
            proj_messages = [Message(role="user", content=messages)]
        else:
            proj_messages = [
                Message(role=str(m.get("role", "user")), content=str(m.get("content", "")))
                for m in messages
            ]
        metadata = {
            "attack_goal": self._task_context.get("attack_goal", ""),
            "expected_answer": self._task_context.get("expected_answer", ""),
            "canaries": list(self._task_context.get("canaries") or []),
            "instruction": self._task_context.get("instruction", ""),
            "domain": self._task_context.get("domain", "general"),
        }
        mock_role = CREWAI_ROLE_TO_MOCK.get(self.agent_role, self.agent_role)
        response = self._mock.complete(
            proj_messages,
            seed=int(self._task_context.get("rng_seed", 0)),
            agent_role=mock_role,
            task_id=self._task_context.get("task_id"),
            metadata=metadata,
        )
        prompt_tokens = max(10, sum(len(m.content.split()) for m in proj_messages) * 2)
        completion_tokens = response.token_count
        self._token_usage["prompt_tokens"] += prompt_tokens
        self._token_usage["completion_tokens"] += completion_tokens
        self._token_usage["total_tokens"] += prompt_tokens + completion_tokens
        self._token_usage["successful_requests"] += 1
        return response.text

    def get_usage_metrics(self):
        from crewai.types.usage_metrics import UsageMetrics

        return UsageMetrics(
            total_tokens=self._token_usage["total_tokens"],
            prompt_tokens=self._token_usage["prompt_tokens"],
            completion_tokens=self._token_usage["completion_tokens"],
            successful_requests=self._token_usage["successful_requests"],
        )
