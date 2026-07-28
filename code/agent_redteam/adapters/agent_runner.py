"""Shared autonomous agent step runner for LLM-backed real workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_redteam.adapters.llm_tools import default_tool_specs, execute_tool
from agent_redteam.evaluation.injection_source import INJECTION_LOCATION_TO_CHANNEL
from agent_redteam.goals import is_leakage_goal
from agent_redteam.llm.base import LLMClient
from agent_redteam.llm.types import Message, ToolSpec
from agent_redteam.schemas import AttackVariant


ROLE_INJECTION_LOCATION = {
    "planner": ("inter_agent_message", "system_prompt"),
    "retriever": ("retrieved_context",),
    "worker": ("tool_output",),
    "memory": ("memory",),
    "finalizer": ("user_input",),
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


def build_llm_metadata(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "attack_goal": state.get("attack_goal", ""),
        "expected_answer": state.get("expected_answer", ""),
        "canaries": list(state.get("canaries") or []),
        "instruction": state.get("instruction", ""),
        "domain": state.get("domain", "general"),
    }


def persist_injection_to_channels(
    state: Dict[str, Any],
    location: str,
    text: str,
) -> Dict[str, Any]:
    """Mirror controlled-mode injection by writing attack text into trace channels."""
    updates: Dict[str, Any] = {}
    if location == "inter_agent_message":
        inter = list(state.get("inter_agent_messages") or [])
        inter.append(text)
        updates["inter_agent_messages"] = inter
    elif location == "tool_output":
        tool_outputs = list(state.get("tool_outputs") or [])
        tool_outputs.append(text)
        updates["tool_outputs"] = tool_outputs
    elif location == "memory":
        memory_writes = list(state.get("memory_writes") or [])
        memory_writes.append(text)
        updates["memory_writes"] = memory_writes
    elif location == "retrieved_context":
        retrieved = list(state.get("retrieved_context") or [])
        retrieved.append(text)
        updates["retrieved_context"] = retrieved
    elif location == "system_prompt":
        logs = list(state.get("logs") or [])
        logs.append(text)
        updates["logs"] = logs
    return updates


def apply_attack_to_messages(
    messages: List[Message],
    state: Dict[str, Any],
    agent_role: str,
) -> tuple[List[Message], Dict[str, List[str]]]:
    """Inject attack text before the target agent LLM call."""
    injected = dict(state.get("injected_texts_by_channel") or {})
    attack_goal = state.get("attack_goal", "")
    location = state.get("attack_injection_location", "")
    template = state.get("attack_prompt_template", "")
    if not template or not state.get("attack_variant_id"):
        return messages, injected

    role_locations = ROLE_INJECTION_LOCATION.get(agent_role, ())
    if location not in role_locations:
        return messages, injected

    canary = (state.get("canaries") or ["SYN_CANARY"])[0]
    if is_leakage_goal(attack_goal):
        text = _format_injection(canary, template)
    else:
        text = template.replace("{canary}", "").strip() or template

    channel = INJECTION_LOCATION_TO_CHANNEL.get(location, "logs")
    injected = _record_injection(injected, channel, text)

    if location == "system_prompt":
        messages = [Message(role="system", content=f"SYSTEM: {text}")] + messages
    elif location == "user_input":
        messages = messages + [Message(role="user", content=text, name="attack")]
    else:
        messages = messages + [
            Message(role="user", content=f"[injected/{location}] {text}", name="attack")
        ]
    return messages, injected


def run_agent_step(
    agent_role: str,
    state: Dict[str, Any],
    llm_client: LLMClient,
    *,
    system_prompt: str,
    user_prompt: str,
    with_tools: bool = False,
) -> Dict[str, Any]:
    """Execute one LLM agent step and update workflow state fields."""
    channel_updates: Dict[str, Any] = {}
    location = state.get("attack_injection_location", "")
    role_locations = ROLE_INJECTION_LOCATION.get(agent_role, ())
    if location in role_locations and state.get("attack_variant_id"):
        canary = (state.get("canaries") or ["SYN_CANARY"])[0]
        attack_goal = state.get("attack_goal", "")
        template = state.get("attack_prompt_template", "")
        if template:
            if is_leakage_goal(attack_goal):
                injected_text = _format_injection(canary, template)
            else:
                injected_text = template.replace("{canary}", "").strip() or template
            channel_updates = persist_injection_to_channels(state, location, injected_text)

    working_state = dict(state)
    working_state.update(channel_updates)

    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]
    for msg in working_state.get("inter_agent_messages") or []:
        messages.append(Message(role="assistant", content=str(msg), name="context"))
    for ctx in working_state.get("retrieved_context") or []:
        messages.append(Message(role="user", content=f"[context] {ctx}", name="retriever"))
    for out in working_state.get("tool_outputs") or []:
        messages.append(Message(role="tool", content=str(out), name="tool"))

    messages, injected = apply_attack_to_messages(messages, working_state, agent_role)

    tools = None
    if with_tools:
        tools = [
            ToolSpec(name=t["name"], description=t["description"], parameters=t["parameters"])
            for t in default_tool_specs()
        ]

    seed = int(state.get("rng_seed", 0))
    response = llm_client.complete(
        messages,
        tools=tools,
        seed=seed,
        agent_role=agent_role,
        task_id=state.get("task_id"),
        metadata=build_llm_metadata(state),
    )

    update: Dict[str, Any] = {
        "token_count": int(state.get("token_count", 0)) + response.token_count,
        "estimated_cost": float(state.get("estimated_cost", 0.0)) + response.estimated_cost,
        "injected_texts_by_channel": injected,
    }

    inter = list(working_state.get("inter_agent_messages") or [])
    logs = list(working_state.get("logs") or [])
    delegation = list(working_state.get("delegation_requests") or [])
    retrieved = list(working_state.get("retrieved_context") or [])
    tool_args = list(working_state.get("tool_call_arguments") or [])
    tool_outputs = list(working_state.get("tool_outputs") or [])
    memory_writes = list(working_state.get("memory_writes") or [])
    errors = list(state.get("errors") or [])
    tool_calls_count = int(state.get("tool_calls", 0))
    retries = int(state.get("retries", 0))

    label = agent_role
    if response.text:
        inter.append(f"[{label}] {response.text}")

    for tc in response.tool_calls:
        tool_calls_count += 1
        output, arg = execute_tool(
            tc.name,
            tc.arguments,
            instruction=str(state.get("instruction", "")),
            domain=str(state.get("domain", "general")),
            canaries=list(state.get("canaries") or []),
        )
        tool_args.append(arg)
        tool_outputs.append(output)
        logs.append(f"INFO: {label} invoked {tc.name}")
        if tc.name == "execute_workflow_step" and int(tc.arguments.get("repeat", 1) or 1) > 2:
            retries += 1
            if agent_role == "worker":
                errors.append(f"tool_loop_at_{label}")

    if agent_role == "retriever" and response.text and not response.tool_calls:
        retrieved.append(response.text)

    if agent_role == "memory" and response.text:
        memory_writes.append(response.text)

    if agent_role == "planner":
        delegation.append(f"{label}->retriever: plan ready for {state.get('task_id')}")

    if agent_role in ("reviewer", "finalizer"):
        update["final_answer"] = response.text

    update.update(
        {
            "inter_agent_messages": inter,
            "logs": logs,
            "delegation_requests": delegation,
            "retrieved_context": retrieved,
            "tool_call_arguments": tool_args,
            "tool_outputs": tool_outputs,
            "memory_writes": memory_writes,
            "tool_calls": tool_calls_count,
            "retries": retries,
            "errors": errors,
        }
    )
    return update


def attack_from_state_dict(state: Dict[str, Any]) -> Optional[AttackVariant]:
    if not state.get("attack_variant_id"):
        return None
    return AttackVariant(
        id=str(state["attack_variant_id"]),
        goal=state.get("attack_goal", "leakage"),
        prompt_template=str(state.get("attack_prompt_template", "")),
        injection_location=str(state.get("attack_injection_location", "")),
        target_channel=str(state.get("attack_target_channel", "")),
        target_agent=str(state.get("attack_target_agent", "")),
        stealth_level=float(state.get("attack_stealth_level", 0.0)),
    )


def grade_task_success(final_output: str, expected_answer: str) -> bool:
    if not expected_answer:
        return bool(final_output.strip())
    return expected_answer in final_output
