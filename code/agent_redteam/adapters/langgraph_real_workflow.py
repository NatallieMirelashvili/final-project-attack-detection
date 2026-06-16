"""Minimal real LangGraph workflow for controlled leakage experiments."""

from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional, TypedDict

from agent_redteam.data.canaries import contains_exact_canary
from agent_redteam.evaluation.injection_source import INJECTION_LOCATION_TO_CHANNEL
from agent_redteam.schemas import AttackVariant, Task

_LANGGRAPH_IMPORT_ERROR = (
    "LangGraph is not installed. Install optional dependencies with: "
    "pip install 'agent-redteam[langgraph]'"
)


def try_import_langgraph() -> Any:
    try:
        from langgraph.graph import END, START, StateGraph

        return StateGraph, START, END
    except ImportError:
        raise ImportError(_LANGGRAPH_IMPORT_ERROR)


class WorkflowGraphState(TypedDict, total=False):
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
    state: WorkflowGraphState,
    channel: str,
    text: str,
) -> Dict[str, List[str]]:
    injected = dict(state.get("injected_texts_by_channel") or {})
    injected.setdefault(channel, []).append(text)
    return injected


def _propagation_probability(state: WorkflowGraphState) -> float:
    profile = state.get("calibration_profile", "medium")
    base = _PROPAGATION_BASE.get(profile, 0.25)
    stealth = float(state.get("attack_stealth_level", 0.0))
    return min(0.95, base + stealth * 0.4)


def _find_canary_snippet(state: WorkflowGraphState) -> Optional[str]:
    canaries = state.get("canaries") or []
    if not canaries:
        return None
    for channel in (
        "inter_agent_messages",
        "tool_outputs",
        "memory_writes",
        "retrieved_context",
        "logs",
        "delegation_requests",
        "tool_call_arguments",
    ):
        for text in state.get(channel, []):
            if text and contains_exact_canary(text, canaries):
                return text
    return None


def build_langgraph_workflow() -> Any:
    """Compile a minimal LangGraph workflow with real node execution."""
    StateGraph, START, END = try_import_langgraph()

    def user_input_node(state: WorkflowGraphState) -> Dict[str, Any]:
        start = time.perf_counter()
        user_input = state.get("instruction", "")
        injected = dict(state.get("injected_texts_by_channel") or {})
        location = state.get("attack_injection_location", "")
        if location == "user_input" and state.get("attack_prompt_template"):
            canary = (state.get("canaries") or ["SYN_CANARY"])[0]
            user_input = f"{user_input} {_format_injection(canary, state['attack_prompt_template'])}"
        latency = state.get("latency_seconds", 0.0) + (time.perf_counter() - start)
        return {
            "user_input": user_input,
            "injected_texts_by_channel": injected,
            "latency_seconds": latency,
            "token_count": state.get("token_count", 0) + 40,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.0004,
        }

    def planner_node(state: WorkflowGraphState) -> Dict[str, Any]:
        start = time.perf_counter()
        messages = list(state.get("inter_agent_messages") or [])
        logs = list(state.get("logs") or [])
        delegation = list(state.get("delegation_requests") or [])
        injected = dict(state.get("injected_texts_by_channel") or {})

        plan = f"[planner] Plan for {state.get('task_id')}: {state.get('user_input', '')[:80]}"
        messages.append(plan)
        logs.append(f"INFO: planner started {state.get('task_id')}")
        delegation.append(f"planner->retriever: fetch context for {state.get('task_id')}")

        location = state.get("attack_injection_location", "")
        if location == "inter_agent_message" and state.get("attack_prompt_template"):
            canary = (state.get("canaries") or ["SYN_CANARY"])[0]
            text = _format_injection(canary, state["attack_prompt_template"])
            messages.append(f"[planner] {text}")
            injected = _record_injection(
                {**state, "injected_texts_by_channel": injected},
                "inter_agent_messages",
                text,
            )

        if location == "system_prompt" and state.get("attack_prompt_template"):
            canary = (state.get("canaries") or ["SYN_CANARY"])[0]
            text = f"SYSTEM: {_format_injection(canary, state['attack_prompt_template'])}"
            logs.append(text)
            injected = _record_injection({**state, "injected_texts_by_channel": injected}, "logs", text)

        latency = state.get("latency_seconds", 0.0) + (time.perf_counter() - start)
        return {
            "inter_agent_messages": messages,
            "logs": logs,
            "delegation_requests": delegation,
            "injected_texts_by_channel": injected,
            "latency_seconds": latency,
            "token_count": state.get("token_count", 0) + 60,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.0006,
        }

    def retriever_node(state: WorkflowGraphState) -> Dict[str, Any]:
        start = time.perf_counter()
        retrieved = list(state.get("retrieved_context") or [])
        injected = dict(state.get("injected_texts_by_channel") or {})
        ctx = f"[retriever] Context for task={state.get('task_id')}"
        retrieved.append(ctx)

        location = state.get("attack_injection_location", "")
        if location == "retrieved_context" and state.get("attack_prompt_template"):
            canary = (state.get("canaries") or ["SYN_CANARY"])[0]
            text = _format_injection(canary, state["attack_prompt_template"])
            retrieved.append(text)
            injected = _record_injection(
                {**state, "injected_texts_by_channel": injected},
                "retrieved_context",
                text,
            )

        latency = state.get("latency_seconds", 0.0) + (time.perf_counter() - start)
        return {
            "retrieved_context": retrieved,
            "injected_texts_by_channel": injected,
            "latency_seconds": latency,
            "token_count": state.get("token_count", 0) + 50,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.0005,
        }

    def tool_node(state: WorkflowGraphState) -> Dict[str, Any]:
        start = time.perf_counter()
        tool_args = list(state.get("tool_call_arguments") or [])
        tool_outputs = list(state.get("tool_outputs") or [])
        injected = dict(state.get("injected_texts_by_channel") or {})
        tool_args.append(f"tool=execute, task={state.get('task_id')}")
        output = f"[tool] Execution complete for {state.get('task_id')}"
        tool_outputs.append(output)

        location = state.get("attack_injection_location", "")
        if location == "tool_output" and state.get("attack_prompt_template"):
            canary = (state.get("canaries") or ["SYN_CANARY"])[0]
            text = _format_injection(canary, state["attack_prompt_template"])
            tool_outputs.append(text)
            injected = _record_injection(
                {**state, "injected_texts_by_channel": injected},
                "tool_outputs",
                text,
            )

        latency = state.get("latency_seconds", 0.0) + (time.perf_counter() - start)
        return {
            "tool_call_arguments": tool_args,
            "tool_outputs": tool_outputs,
            "tool_calls": state.get("tool_calls", 0) + 1,
            "injected_texts_by_channel": injected,
            "latency_seconds": latency,
            "token_count": state.get("token_count", 0) + 70,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.0007,
        }

    def memory_node(state: WorkflowGraphState) -> Dict[str, Any]:
        start = time.perf_counter()
        memory_writes = list(state.get("memory_writes") or [])
        messages = list(state.get("inter_agent_messages") or [])
        injected = dict(state.get("injected_texts_by_channel") or {})
        mem = f"memory:{state.get('task_id')}=complete"
        rng = random.Random(state.get("rng_seed", 0) + 7)
        tool_outputs = state.get("tool_outputs") or []
        stealth = float(state.get("attack_stealth_level", 0.0))
        if tool_outputs and rng.random() < 0.35 + stealth * 0.25:
            mem = f"{mem} | tool_ref={tool_outputs[-1][:120]}"

        location = state.get("attack_injection_location", "")
        if location == "memory" and state.get("attack_prompt_template"):
            canary = (state.get("canaries") or ["SYN_CANARY"])[0]
            text = _format_injection(canary, state["attack_prompt_template"])
            mem = f"{mem} | {text}"
            injected = _record_injection(
                {**state, "injected_texts_by_channel": injected},
                "memory_writes",
                text,
            )

        memory_writes.append(mem)
        messages.append(f"[memory] Updated state for {state.get('task_id')}")

        latency = state.get("latency_seconds", 0.0) + (time.perf_counter() - start)
        return {
            "memory_writes": memory_writes,
            "inter_agent_messages": messages,
            "injected_texts_by_channel": injected,
            "latency_seconds": latency,
            "token_count": state.get("token_count", 0) + 45,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.00045,
        }

    def summarizer_node(state: WorkflowGraphState) -> Dict[str, Any]:
        start = time.perf_counter()
        answer = state.get("expected_answer", "")
        final_answer = f"Answer: {answer}"
        messages = list(state.get("inter_agent_messages") or [])
        messages.append(f"[summarizer] Prepared response for {state.get('task_id')}")

        target = state.get("attack_target_channel", "")
        if target == "final_output" and state.get("attack_variant_id"):
            rng = random.Random(state.get("rng_seed", 0) + 99)
            if rng.random() < _propagation_probability(state):
                snippet = _find_canary_snippet(state)
                if snippet:
                    final_answer = f"{final_answer} [Context: {snippet[:160]}]"

        latency = state.get("latency_seconds", 0.0) + (time.perf_counter() - start)
        return {
            "final_answer": final_answer,
            "inter_agent_messages": messages,
            "latency_seconds": latency,
            "token_count": state.get("token_count", 0) + 35,
            "estimated_cost": state.get("estimated_cost", 0.0) + 0.00035,
        }

    def final_response_node(state: WorkflowGraphState) -> Dict[str, Any]:
        """Terminal node: final_answer is the user-visible response (no trace concatenation)."""
        return {"final_answer": state.get("final_answer", "")}

    builder = StateGraph(WorkflowGraphState)
    builder.add_node("user_input", user_input_node)
    builder.add_node("planner", planner_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("tool", tool_node)
    builder.add_node("memory", memory_node)
    builder.add_node("summarizer", summarizer_node)
    builder.add_node("final_response", final_response_node)

    builder.add_edge(START, "user_input")
    builder.add_edge("user_input", "planner")
    builder.add_edge("planner", "retriever")
    builder.add_edge("retriever", "tool")
    builder.add_edge("tool", "memory")
    builder.add_edge("memory", "summarizer")
    builder.add_edge("summarizer", "final_response")
    builder.add_edge("final_response", END)

    return builder.compile()


def initial_state(
    task: Task,
    attack: Optional[AttackVariant],
    rng_seed: int,
    calibration_profile: str,
) -> WorkflowGraphState:
    state: WorkflowGraphState = {
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


def injected_channel_from_state(state: WorkflowGraphState) -> Optional[str]:
    location = state.get("attack_injection_location", "")
    return INJECTION_LOCATION_TO_CHANNEL.get(location)
