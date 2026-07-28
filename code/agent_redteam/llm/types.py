"""LLM request/response types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    role: str
    content: str
    name: str = ""


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    id: str = ""


@dataclass
class LLMRequest:
    messages: List[Message]
    tools: Optional[List[ToolSpec]] = None
    seed: Optional[int] = None
    agent_role: str = ""
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    token_count: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)
