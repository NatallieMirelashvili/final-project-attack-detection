"""LLM client abstraction for autonomous agent workflows."""

from agent_redteam.llm.factory import create_llm_client
from agent_redteam.llm.mock_client import MockLLMClient
from agent_redteam.llm.ollama_client import OllamaLLMClient
from agent_redteam.llm.types import LLMResponse, Message, ToolCall, ToolSpec

__all__ = [
    "MockLLMClient",
    "OllamaLLMClient",
    "create_llm_client",
    "LLMResponse",
    "Message",
    "ToolCall",
    "ToolSpec",
]
