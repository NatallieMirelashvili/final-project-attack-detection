"""Bridge project MockLLMClient / Ollama to official AutoGen ChatCompletionClient."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Literal, Mapping, Optional, Sequence, Union

from agent_redteam.llm.factory import create_llm_client
from agent_redteam.llm.mock_client import MockLLMClient
from agent_redteam.llm.types import Message

AUTOGEN_MODEL_INFO = {
    "vision": False,
    "function_calling": True,
    "json_output": False,
    "family": "unknown",
    "structured_output": False,
}


def build_autogen_model_client(adapter_config: Dict[str, Any], *, agent_role: str):
    """Return an official AutoGen ChatCompletionClient for one agent role."""
    from autogen_core.models import ModelFamily

    mode = str(adapter_config.get("llm_mode", "mock")).lower()
    if mode == "mock":
        return MockAutoGenChatClient(adapter_config, agent_role=agent_role)

    from autogen_ext.models.openai import OpenAIChatCompletionClient

    model = str(adapter_config.get("llm_model", "llama3.2:3b"))
    base_url = str(adapter_config.get("ollama_base_url", "http://localhost:11434")).rstrip("/") + "/v1"
    temperature = float(adapter_config.get("temperature", 0.0))
    return OpenAIChatCompletionClient(
        model=model,
        base_url=base_url,
        api_key=str(adapter_config.get("api_key", "ollama")),
        temperature=temperature,
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        },
    )


def _messages_to_project(messages: Sequence[Any]) -> List[Message]:
    out: List[Message] = []
    for msg in messages:
        role = getattr(msg, "type", "") or msg.__class__.__name__.replace("Message", "").lower()
        if role == "system":
            role_name = "system"
        elif role == "user":
            role_name = "user"
        elif role == "assistant":
            role_name = "assistant"
        else:
            role_name = "user"
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            content = str(content)
        source = getattr(msg, "source", "") or ""
        out.append(Message(role=role_name, content=content, name=source))
    return out


class MockAutoGenChatClient:
    """Official AutoGen ChatCompletionClient backed by project MockLLMClient."""

    component_type = "model"

    def __init__(self, adapter_config: Dict[str, Any], *, agent_role: str) -> None:
        from autogen_core.models import ModelFamily, ModelInfo, RequestUsage, validate_model_info

        self._agent_role = agent_role
        self._task_context: Dict[str, Any] = dict(adapter_config.get("task_context") or {})
        self._mock = MockLLMClient(adapter_config)
        self._model_info: ModelInfo = {
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False,
        }
        validate_model_info(self._model_info)
        self._cur_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    def set_task_context(self, context: Dict[str, Any]) -> None:
        self._task_context = dict(context)

    async def create(
        self,
        messages: Sequence[Any],
        *,
        tools: Sequence[Any] = (),
        tool_choice: Any = "auto",
        json_output: Optional[Any] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[Any] = None,
    ):
        from autogen_core import FunctionCall
        from autogen_core.models import CreateResult, RequestUsage

        del tool_choice, json_output, extra_create_args, cancellation_token
        proj_messages = _messages_to_project(messages)
        metadata = {
            "attack_goal": self._task_context.get("attack_goal", ""),
            "expected_answer": self._task_context.get("expected_answer", ""),
            "canaries": list(self._task_context.get("canaries") or []),
            "instruction": self._task_context.get("instruction", ""),
            "domain": self._task_context.get("domain", "general"),
        }
        seed = int(self._task_context.get("rng_seed", 0))
        response = self._mock.complete(
            [Message(role="system", content=m.content) if m.role == "system" else m for m in proj_messages],
            tools=None,
            seed=seed,
            agent_role=self._agent_role,
            task_id=self._task_context.get("task_id"),
            metadata=metadata,
        )
        prompt_tokens = max(10, sum(len(m.content.split()) for m in proj_messages) * 2)
        completion_tokens = response.token_count
        self._cur_usage = RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        self._total_usage = RequestUsage(
            prompt_tokens=self._total_usage.prompt_tokens + prompt_tokens,
            completion_tokens=self._total_usage.completion_tokens + completion_tokens,
        )
        if response.tool_calls:
            content: Union[str, List[FunctionCall]] = [
                FunctionCall(id=tc.id, name=tc.name, arguments=tc.arguments) for tc in response.tool_calls
            ]
            finish = "function_calls"
        else:
            content = response.text
            finish = "stop"
        return CreateResult(
            finish_reason=finish,
            content=content,
            usage=self._cur_usage,
            cached=False,
        )

    def create_stream(
        self,
        messages: Sequence[Any],
        *,
        tools: Sequence[Any] = (),
        tool_choice: Any = "auto",
        json_output: Optional[Any] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[Any] = None,
    ) -> AsyncGenerator[Union[str, Any], None]:
        async def _gen():
            result = await self.create(
                messages,
                tools=tools,
                tool_choice=tool_choice,
                json_output=json_output,
                extra_create_args=extra_create_args,
                cancellation_token=cancellation_token,
            )
            if isinstance(result.content, str):
                yield result.content
            yield result

        return _gen()

    async def close(self) -> None:
        return None

    def actual_usage(self):
        return self._cur_usage

    def total_usage(self):
        return self._total_usage

    def count_tokens(self, messages: Sequence[Any], *, tools: Sequence[Any] = ()) -> int:
        del tools
        return max(1, sum(len(getattr(m, "content", "").split()) for m in messages) * 2)

    def remaining_tokens(self, messages: Sequence[Any], *, tools: Sequence[Any] = ()) -> int:
        return max(0, 8192 - self.count_tokens(messages, tools=tools))

    @property
    def capabilities(self):
        return {
            "vision": False,
            "function_calling": True,
            "json_output": False,
        }

    @property
    def model_info(self):
        return self._model_info

    @property
    def agent_role(self) -> str:
        return self._agent_role
