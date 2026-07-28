"""Local Ollama HTTP client for live LLM-backed agent workflows."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from agent_redteam.llm.types import LLMResponse, Message, ToolCall, ToolSpec

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_TEMPERATURE = 0.0


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def is_ollama_running(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout: float = 2.0) -> bool:
    """Return True if Ollama responds at the given base URL."""
    url = f"{_normalize_base_url(base_url)}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def list_ollama_models(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout: float = 5.0) -> List[str]:
    """Return model names reported by Ollama, or empty list if unreachable."""
    url = f"{_normalize_base_url(base_url)}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    models = payload.get("models") or []
    names: List[str] = []
    for entry in models:
        name = entry.get("name") or entry.get("model") or ""
        if name:
            names.append(str(name))
    return names


def is_ollama_model_available(
    model: str,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: float = 5.0,
) -> bool:
    """Return True if the model name (or base name without tag) is pulled locally."""
    models = list_ollama_models(base_url, timeout=timeout)
    if not models:
        return False
    model_base = model.split(":")[0]
    for name in models:
        if name == model or name.split(":")[0] == model_base:
            return True
    return False


def _map_messages(messages: List[Message]) -> List[Dict[str, str]]:
    mapped: List[Dict[str, str]] = []
    for msg in messages:
        role = msg.role
        if role == "tool":
            role = "user"
            content = f"[tool result] {msg.content}"
        else:
            content = msg.content
        if msg.name and role == "assistant":
            content = f"[{msg.name}] {content}"
        mapped.append({"role": role, "content": content})
    return mapped


def _map_tools(tools: Optional[List[ToolSpec]]) -> Optional[List[Dict[str, Any]]]:
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


def _parse_tool_calls(message: Dict[str, Any]) -> List[ToolCall]:
    raw_calls = message.get("tool_calls") or []
    parsed: List[ToolCall] = []
    for idx, call in enumerate(raw_calls):
        fn = call.get("function") or {}
        name = str(fn.get("name") or "")
        if not name:
            continue
        args_raw = fn.get("arguments") or "{}"
        if isinstance(args_raw, str):
            try:
                arguments = json.loads(args_raw) if args_raw.strip() else {}
            except json.JSONDecodeError:
                arguments = {"raw": args_raw}
        elif isinstance(args_raw, dict):
            arguments = args_raw
        else:
            arguments = {}
        parsed.append(
            ToolCall(
                id=str(call.get("id") or f"ollama_tc_{idx}"),
                name=name,
                arguments=arguments,
            )
        )
    return parsed


class OllamaLLMClient:
    """LLM client backed by a local Ollama server (free, no API key)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = dict(config or {})
        self._base_url = _normalize_base_url(
            str(cfg.get("ollama_base_url") or DEFAULT_OLLAMA_BASE_URL)
        )
        self._model = str(cfg.get("llm_model") or DEFAULT_OLLAMA_MODEL)
        self._temperature = float(cfg.get("temperature", DEFAULT_TEMPERATURE))
        self._timeout = float(cfg.get("ollama_timeout", 120.0))
        self._provider = "ollama"

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

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
        del metadata  # reserved for future prompt shaping
        body: Dict[str, Any] = {
            "model": self._model,
            "messages": _map_messages(messages),
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        if seed is not None:
            body["options"]["seed"] = int(seed)
        mapped_tools = _map_tools(tools)
        if mapped_tools:
            body["tools"] = mapped_tools

        url = f"{self._base_url}/api/chat"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            if exc.code == 404 and "model" in detail.lower():
                raise RuntimeError(
                    f"Ollama model '{self._model}' is not available locally. "
                    f"Pull it with: ollama pull {self._model}"
                ) from exc
            raise RuntimeError(
                f"Ollama chat request failed (HTTP {exc.code}): {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise RuntimeError(
                "Cannot connect to Ollama at "
                f"{self._base_url}. Start the Ollama app or run `ollama serve`, "
                f"then pull the model with `ollama pull {self._model}`."
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError(
                f"Ollama request timed out after {self._timeout}s "
                f"(model={self._model}). Try a smaller model such as llama3.2:1b."
            ) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        message = payload.get("message") or {}
        text = str(message.get("content") or "").strip()
        tool_calls = _parse_tool_calls(message)

        prompt_tokens = int(payload.get("prompt_eval_count") or 0)
        eval_tokens = int(payload.get("eval_count") or 0)
        token_count = prompt_tokens + eval_tokens
        if token_count <= 0 and text:
            token_count = max(1, len(text.split()))

        total_duration_ns = payload.get("total_duration")
        latency_ms = elapsed_ms
        if total_duration_ns:
            try:
                latency_ms = float(total_duration_ns) / 1_000_000.0
            except (TypeError, ValueError):
                pass

        error_field = payload.get("error")
        if error_field:
            err_text = str(error_field)
            if "not found" in err_text.lower() or "pull" in err_text.lower():
                raise RuntimeError(
                    f"Ollama model '{self._model}' is not available locally. "
                    f"Pull it with: ollama pull {self._model}"
                )
            raise RuntimeError(f"Ollama error: {err_text}")

        finish = "tool_calls" if tool_calls else "stop"
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            token_count=token_count,
            estimated_cost=0.0,
            latency_ms=latency_ms,
            finish_reason=finish,
            metadata={
                "provider": self._provider,
                "model": self._model,
                "base_url": self._base_url,
                "agent_role": agent_role,
                "task_id": task_id,
                "prompt_eval_count": prompt_tokens,
                "eval_count": eval_tokens,
                "ollama": True,
            },
        )
