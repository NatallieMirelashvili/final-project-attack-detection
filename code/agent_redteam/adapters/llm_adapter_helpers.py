"""Helpers for adapters running LLM-backed workflows."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from agent_redteam.adapters.agent_runner import grade_task_success
from agent_redteam.adapters.llm_workflow_state import (
    LLMWorkflowState,
    injected_channel_from_state,
)
from agent_redteam.defenses.filters import apply_defense
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.llm.base import LLMClient
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


def execute_llm_workflow(
    *,
    task: Task,
    attack: Optional[AttackVariant],
    defense: Optional[DefenseConfig],
    state: LLMWorkflowState,
    llm_client: Optional[LLMClient],
    workflow_fn: Callable[..., LLMWorkflowState],
    system_name: str,
    integration_mode: str = "llm",
    adapter_config: Optional[Dict[str, Any]] = None,
) -> RunResult:
    """Run an LLM workflow and build a RunResult."""
    start = time.perf_counter()
    if llm_client is None:
        result = workflow_fn(state)
    else:
        result = workflow_fn(state, llm_client)
    elapsed = time.perf_counter() - start

    final_output = str(result.get("final_answer", ""))
    injected_by_channel = dict(result.get("injected_texts_by_channel") or {})
    injected_canary = ""
    injected_channel = ""
    injection_location = ""
    if attack:
        injection_location = attack.injection_location
        injected_channel = injected_channel_from_state(result) or ""
        if task.sensitive_canaries:
            injected_canary = task.sensitive_canaries[0]

    trace = Trace(
        final_output=final_output,
        inter_agent_messages=list(result.get("inter_agent_messages") or []),
        tool_call_arguments=list(result.get("tool_call_arguments") or []),
        tool_outputs=list(result.get("tool_outputs") or []),
        retrieved_context=list(result.get("retrieved_context") or []),
        memory_writes=list(result.get("memory_writes") or []),
        logs=list(result.get("logs") or []),
        delegation_requests=list(result.get("delegation_requests") or []),
        injection_metadata={
            "injection_location": injection_location,
            "injected_channel": injected_channel,
            "injected_canary": injected_canary,
            "injection_variant_id": attack.id if attack else "",
            "injected_texts_by_channel": injected_by_channel,
            "integration_mode": integration_mode,
        },
    )

    if defense:
        trace = apply_defense(trace, defense, task.sensitive_canaries)
        final_output = trace.final_output or final_output

    task_success = grade_task_success(
        final_output,
        task.expected_answer,
        task=task,
        adapter_config=adapter_config,
    )

    return RunResult(
        task_id=task.id,
        system_name=system_name,
        attack_variant_id=attack.id if attack else None,
        defense_name=defense.name if defense else "D0_no_defense",
        final_output=final_output,
        task_success=task_success,
        latency_seconds=float(result.get("latency_seconds", 0.0)) + elapsed,
        token_count=int(result.get("token_count", 0)),
        estimated_cost=float(result.get("estimated_cost", 0.0)),
        tool_calls=int(result.get("tool_calls", 0)),
        retries=int(result.get("retries", 0)),
        errors=list(result.get("errors") or []),
        trace=trace,
    )
