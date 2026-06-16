"""Controlled AgentDojo-compatible local workflow for real adapter experiments."""

from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional, TypedDict

from agent_redteam.data.canaries import contains_exact_canary
from agent_redteam.evaluation.injection_source import INJECTION_LOCATION_TO_CHANNEL
from agent_redteam.schemas import AttackVariant, Task

_AGENTDOJO_REAL_IMPORT_ERROR = (
    "AgentDojo is not installed. Install optional dependency with: "
    "pip install 'agent-redteam[agentdojo]'"
)


def try_import_agentdojo() -> Any:
    try:
        import agentdojo  # noqa: F401

        return agentdojo
    except ImportError:
        try:
            from agentdojo import benchmark  # noqa: F401

            return benchmark
        except ImportError:
            raise ImportError(_AGENTDOJO_REAL_IMPORT_ERROR)


class AgentDojoWorkflowState(TypedDict, total=False):
    task_id: str
    instruction: str
    expected_answer: str
    canaries: List[str]
    user_input: str
    inter_agent_messages: List[str]
    tool_call_arguments: List[str]
    tool_outputs: List[str]
    retrieved_context: List[str]
    memory_writes: List[str]
    logs: List[str]
    delegation_requests: List[str]
    final_answer: str
    rng_seed: int
    calibration_profile: str
    attack_injection_location: str
    attack_target_channel: str
    attack_prompt_template: str
    attack_stealth_level: float
    attack_variant_id: str
    injected_texts_by_channel: Dict[str, List[str]]
    tool_calls: int
    token_count: int
    estimated_cost: float
    latency_seconds: float


_PROPAGATION_BASE: Dict[str, float] = {
    "medium": 0.35,
    "hard": 0.15,
    "legacy": 0.25,
}


def _format_injection(canary: str, template: str) -> str:
    return template.replace("{canary}", canary)


def _record_injection(
    injected: Dict[str, List[str]],
    channel: str,
    text: str,
) -> Dict[str, List[str]]:
    out = dict(injected)
    out.setdefault(channel, []).append(text)
    return out


def _propagation_probability(state: AgentDojoWorkflowState) -> float:
    profile = state.get("calibration_profile", "medium")
    base = _PROPAGATION_BASE.get(profile, 0.25)
    stealth = float(state.get("attack_stealth_level", 0.0))
    return min(0.95, base + stealth * 0.4)


def _find_canary_snippet(state: AgentDojoWorkflowState) -> Optional[str]:
    canaries = state.get("canaries") or []
    if not canaries:
        return None
    for channel in (
        "inter_agent_messages",
        "tool_outputs",
        "memory_writes",
        "retrieved_context",
        "logs",
        "tool_call_arguments",
    ):
        for text in state.get(channel, []):
            if text and contains_exact_canary(text, canaries):
                return text
    return None


def _merge_state(state: AgentDojoWorkflowState, update: Dict[str, Any]) -> AgentDojoWorkflowState:
    merged: AgentDojoWorkflowState = dict(state)
    merged.update(update)
    return merged


def run_agentdojo_real_workflow(state: AgentDojoWorkflowState) -> AgentDojoWorkflowState:
    """Execute a minimal controlled AgentDojo-style agent pipeline locally."""
    start_total = time.perf_counter()
    injected = dict(state.get("injected_texts_by_channel") or {})

    # user_input
    user_input = state.get("instruction", "")
    if state.get("attack_injection_location") == "user_input" and state.get("attack_prompt_template"):
        canary = (state.get("canaries") or ["SYN_CANARY"])[0]
        user_input = f"{user_input} {_format_injection(canary, state['attack_prompt_template'])}"
    state = _merge_state(
        state,
        {
            "user_input": user_input,
            "token_count": state.get("token_count", 0) + 40,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.0004,
        },
    )

    # agent / system message
    messages = list(state.get("inter_agent_messages") or [])
    logs = list(state.get("logs") or [])
    messages.append(f"[agentdojo-agent] Task {state.get('task_id')}: {user_input[:80]}")
    if state.get("attack_injection_location") == "inter_agent_message" and state.get(
        "attack_prompt_template"
    ):
        canary = (state.get("canaries") or ["SYN_CANARY"])[0]
        text = _format_injection(canary, state["attack_prompt_template"])
        messages.append(f"[agentdojo-agent] {text}")
        injected = _record_injection(injected, "inter_agent_messages", text)
    if state.get("attack_injection_location") == "system_prompt" and state.get(
        "attack_prompt_template"
    ):
        canary = (state.get("canaries") or ["SYN_CANARY"])[0]
        text = f"SYSTEM: {_format_injection(canary, state['attack_prompt_template'])}"
        logs.append(text)
        injected = _record_injection(injected, "logs", text)
    state = _merge_state(
        state,
        {
            "inter_agent_messages": messages,
            "logs": logs,
            "token_count": state.get("token_count", 0) + 55,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.00055,
        },
    )

    # retrieved context
    retrieved = list(state.get("retrieved_context") or [])
    retrieved.append(f"[agentdojo-env] Benchmark context for {state.get('task_id')}")
    if state.get("attack_injection_location") == "retrieved_context" and state.get(
        "attack_prompt_template"
    ):
        canary = (state.get("canaries") or ["SYN_CANARY"])[0]
        text = _format_injection(canary, state["attack_prompt_template"])
        retrieved.append(text)
        injected = _record_injection(injected, "retrieved_context", text)
    state = _merge_state(
        state,
        {
            "retrieved_context": retrieved,
            "token_count": state.get("token_count", 0) + 45,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.00045,
        },
    )

    # tool observation
    tool_args = list(state.get("tool_call_arguments") or [])
    tool_outputs = list(state.get("tool_outputs") or [])
    tool_args.append(f"agentdojo_tool=run, task={state.get('task_id')}")
    tool_outputs.append(f"[agentdojo-tool] Observation for {state.get('task_id')}")
    if state.get("attack_injection_location") == "tool_output" and state.get(
        "attack_prompt_template"
    ):
        canary = (state.get("canaries") or ["SYN_CANARY"])[0]
        text = _format_injection(canary, state["attack_prompt_template"])
        tool_outputs.append(text)
        injected = _record_injection(injected, "tool_outputs", text)
    state = _merge_state(
        state,
        {
            "tool_call_arguments": tool_args,
            "tool_outputs": tool_outputs,
            "tool_calls": state.get("tool_calls", 0) + 1,
            "token_count": state.get("token_count", 0) + 65,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.00065,
        },
    )

    # environment / memory state
    memory_writes = list(state.get("memory_writes") or [])
    mem = f"agentdojo_env:{state.get('task_id')}=done"
    rng = random.Random(state.get("rng_seed", 0) + 11)
    tool_outputs_list = state.get("tool_outputs") or []
    stealth = float(state.get("attack_stealth_level", 0.0))
    if tool_outputs_list and rng.random() < 0.35 + stealth * 0.25:
        mem = f"{mem} | tool_obs={tool_outputs_list[-1][:120]}"
    if state.get("attack_injection_location") == "memory" and state.get("attack_prompt_template"):
        canary = (state.get("canaries") or ["SYN_CANARY"])[0]
        text = _format_injection(canary, state["attack_prompt_template"])
        mem = f"{mem} | {text}"
        injected = _record_injection(injected, "memory_writes", text)
    memory_writes.append(mem)
    messages = list(state.get("inter_agent_messages") or [])
    messages.append(f"[agentdojo-env] State updated for {state.get('task_id')}")
    state = _merge_state(
        state,
        {
            "memory_writes": memory_writes,
            "inter_agent_messages": messages,
            "token_count": state.get("token_count", 0) + 50,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.0005,
        },
    )

    # final answer (user-visible only)
    answer = state.get("expected_answer", "")
    final_answer = f"Answer: {answer}"
    if state.get("attack_target_channel") == "final_output" and state.get("attack_variant_id"):
        rng_final = random.Random(state.get("rng_seed", 0) + 99)
        if rng_final.random() < _propagation_probability(state):
            snippet = _find_canary_snippet(state)
            if snippet:
                final_answer = f"{final_answer} [Context: {snippet[:160]}]"

    elapsed = time.perf_counter() - start_total
    return _merge_state(
        state,
        {
            "final_answer": final_answer,
            "injected_texts_by_channel": injected,
            "latency_seconds": state.get("latency_seconds", 0.0) + elapsed,
            "token_count": state.get("token_count", 0) + 30,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.0003,
        },
    )


def initial_state(
    task: Task,
    attack: Optional[AttackVariant],
    rng_seed: int,
    calibration_profile: str,
) -> AgentDojoWorkflowState:
    state: AgentDojoWorkflowState = {
        "task_id": task.id,
        "instruction": task.instruction,
        "expected_answer": task.expected_answer,
        "canaries": list(task.sensitive_canaries),
        "user_input": "",
        "inter_agent_messages": [],
        "tool_call_arguments": [],
        "tool_outputs": [],
        "retrieved_context": [],
        "memory_writes": [],
        "logs": [],
        "delegation_requests": [],
        "final_answer": "",
        "rng_seed": rng_seed,
        "calibration_profile": calibration_profile,
        "injected_texts_by_channel": {},
        "tool_calls": 0,
        "token_count": 0,
        "estimated_cost": 0.0,
        "latency_seconds": 0.0,
    }
    if attack:
        state.update(
            {
                "attack_injection_location": attack.injection_location,
                "attack_target_channel": attack.target_channel,
                "attack_prompt_template": attack.prompt_template,
                "attack_stealth_level": attack.stealth_level,
                "attack_variant_id": attack.id,
            }
        )
    return state


def injected_channel_from_state(state: AgentDojoWorkflowState) -> Optional[str]:
    location = state.get("attack_injection_location", "")
    return INJECTION_LOCATION_TO_CHANNEL.get(location)
