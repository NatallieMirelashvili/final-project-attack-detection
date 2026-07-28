"""Shared workflow state for style-compatible LLM multi-agent pipelines."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from agent_redteam.evaluation.injection_source import INJECTION_LOCATION_TO_CHANNEL
from agent_redteam.schemas import AttackVariant, Task


class LLMWorkflowState(TypedDict, total=False):
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
    domain: str
    attack_goal: str
    attack_target_agent: str
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
    task_success: bool
    retries: int
    errors: List[str]


def format_injection(canary: str, template: str) -> str:
    return template.replace("{canary}", canary)


def record_injection(
    injected: Dict[str, List[str]],
    channel: str,
    text: str,
) -> Dict[str, List[str]]:
    out = dict(injected)
    out.setdefault(channel, []).append(text)
    return out


def merge_state(state: LLMWorkflowState, update: Dict[str, Any]) -> LLMWorkflowState:
    merged: LLMWorkflowState = dict(state)
    merged.update(update)
    return merged


def initial_state_llm(
    task: Task,
    attack: Optional[AttackVariant],
    rng_seed: int,
    calibration_profile: str,
) -> LLMWorkflowState:
    state: LLMWorkflowState = {
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
        "domain": task.domain,
        "injected_texts_by_channel": {},
        "tool_calls": 0,
        "token_count": 0,
        "estimated_cost": 0.0,
        "latency_seconds": 0.0,
        "task_success": True,
        "retries": 0,
        "errors": [],
    }
    if attack:
        state.update(
            {
                "attack_goal": attack.goal,
                "attack_target_agent": attack.target_agent,
                "attack_injection_location": attack.injection_location,
                "attack_target_channel": attack.target_channel,
                "attack_prompt_template": attack.prompt_template,
                "attack_stealth_level": attack.stealth_level,
                "attack_variant_id": attack.id,
            }
        )
    return state


def injected_channel_from_state(state: LLMWorkflowState) -> Optional[str]:
    location = state.get("attack_injection_location", "")
    return INJECTION_LOCATION_TO_CHANNEL.get(location)
