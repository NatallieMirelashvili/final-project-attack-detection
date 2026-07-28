"""LLM client protocol."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from agent_redteam.llm.types import LLMResponse, Message, ToolSpec


class LLMClient(Protocol):
    def complete(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[ToolSpec]] = None,
        seed: Optional[int] = None,
        agent_role: str = "",
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        ...
