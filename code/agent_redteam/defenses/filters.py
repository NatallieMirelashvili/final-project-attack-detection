"""Defense filter implementations."""

from __future__ import annotations

from typing import List

from agent_redteam.data.canaries import redact_canaries
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.schemas import Trace


def _redact_list(items: List[str], canaries: List[str]) -> List[str]:
    return [redact_canaries(item, canaries) for item in items]


def apply_defense(
    trace: Trace,
    defense: DefenseConfig,
    canaries: List[str],
) -> Trace:
    """Apply defense filters to a trace, preserving pre-defense snapshots."""
    pre = Trace(
        final_output=trace.final_output,
        inter_agent_messages=list(trace.inter_agent_messages),
        tool_call_arguments=list(trace.tool_call_arguments),
        tool_outputs=list(trace.tool_outputs),
        retrieved_context=list(trace.retrieved_context),
        memory_writes=list(trace.memory_writes),
        logs=list(trace.logs),
        delegation_requests=list(trace.delegation_requests),
    )

    post = Trace(
        final_output=trace.final_output,
        inter_agent_messages=list(trace.inter_agent_messages),
        tool_call_arguments=list(trace.tool_call_arguments),
        tool_outputs=list(trace.tool_outputs),
        retrieved_context=list(trace.retrieved_context),
        memory_writes=list(trace.memory_writes),
        logs=list(trace.logs),
        delegation_requests=list(trace.delegation_requests),
        pre_defense_final_output=pre.final_output,
        pre_defense_inter_agent_messages=list(pre.inter_agent_messages),
        pre_defense_tool_outputs=list(pre.tool_outputs),
        pre_defense_memory_writes=list(pre.memory_writes),
    )

    if defense.defense_type == "no_defense":
        return post

    if defense.defense_type == "guard_agent":
        post.final_output = redact_canaries(post.final_output, canaries)

    if defense.defense_type == "memory_or_inter_agent_redaction":
        post.inter_agent_messages = _redact_list(post.inter_agent_messages, canaries)
        post.memory_writes = _redact_list(post.memory_writes, canaries)
        post.delegation_requests = _redact_list(post.delegation_requests, canaries)

    if defense.defense_type == "tool_output_filtering":
        post.tool_outputs = _redact_list(post.tool_outputs, canaries)
        post.retrieved_context = _redact_list(post.retrieved_context, canaries)

    # prompt_defense lowers leakage probability in adapter; no post-hoc redaction here

    return post
