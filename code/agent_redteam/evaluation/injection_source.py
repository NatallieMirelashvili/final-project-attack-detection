"""Map attack injection locations to trace channels for source-exclusion metrics."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_redteam.schemas import RunResult

INJECTION_LOCATION_TO_CHANNEL: Dict[str, Optional[str]] = {
    "user_input": None,
    "retrieved_context": "retrieved_context",
    "tool_output": "tool_outputs",
    "memory": "memory_writes",
    "inter_agent_message": "inter_agent_messages",
    "system_prompt": "logs",
}


def injected_channel_for_location(injection_location: str) -> Optional[str]:
    return INJECTION_LOCATION_TO_CHANNEL.get(injection_location)


def channel_texts_excluding_injection_source(
    run: RunResult,
    channel: str,
    texts: List[str],
) -> List[str]:
    """Return channel texts with original injection snippets removed from the source channel."""
    meta = run.trace.injection_metadata if run.trace else {}
    injected_by_channel: Dict[str, List[str]] = meta.get("injected_texts_by_channel", {})
    skip = set(injected_by_channel.get(channel, []))
    if not skip:
        return texts
    return [t for t in texts if t not in skip]
