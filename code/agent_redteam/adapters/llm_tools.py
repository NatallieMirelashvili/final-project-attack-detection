"""Deterministic tool backends for LLM agent workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def default_tool_specs() -> List[Dict[str, Any]]:
    return [
        {
            "name": "retrieve_domain_context",
            "description": "Retrieve documents for a task domain.",
            "parameters": {"task_id": "str", "domain": "str", "query": "str"},
        },
        {
            "name": "execute_workflow_step",
            "description": "Execute a workflow action for the task.",
            "parameters": {"task_id": "str", "mode": "str", "repeat": "int"},
        },
    ]


def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    *,
    instruction: str,
    domain: str,
    canaries: List[str],
) -> Tuple[str, str]:
    """Return (tool_output, tool_call_argument_string)."""
    if name == "retrieve_domain_context":
        query = arguments.get("query", instruction[:60])
        arg = f"tool=retrieve, domain={domain}, query={query}"
        output = f"[retrieved] Documents for domain={domain}, query={query}"
        return output, arg

    if name == "execute_workflow_step":
        task_id = arguments.get("task_id", "unknown")
        repeat = int(arguments.get("repeat", 1) or 1)
        mode = arguments.get("mode", "normal")
        arg = f"tool=execute, task={task_id}, mode={mode}, repeat={repeat}"
        output = f"[tool] Executed workflow step for {task_id} x{repeat} mode={mode}"
        return output, arg

    arg = f"tool={name}, args={arguments}"
    return f"[tool] Unknown tool {name}", arg
