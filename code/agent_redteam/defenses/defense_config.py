"""Defense configuration presets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DefenseConfig:
    name: str
    defense_type: str
    strength: float = 0.5
    metadata: Dict = field(default_factory=dict)


D0_NO_DEFENSE = DefenseConfig(name="D0_no_defense", defense_type="no_defense", strength=0.0)
D1_PROMPT_DEFENSE = DefenseConfig(
    name="D1_prompt_defense", defense_type="prompt_defense", strength=0.6
)
D2_GUARD_AGENT = DefenseConfig(name="D2_guard_agent", defense_type="guard_agent", strength=0.7)
D3_MEMORY_REDACTION = DefenseConfig(
    name="D3_memory_or_inter_agent_redaction",
    defense_type="memory_or_inter_agent_redaction",
    strength=0.65,
)
D4_TOOL_OUTPUT_FILTERING = DefenseConfig(
    name="D4_tool_output_filtering", defense_type="tool_output_filtering", strength=0.7
)

DEFENSE_PRESETS: Dict[str, DefenseConfig] = {
    "no_defense": D0_NO_DEFENSE,
    "D0": D0_NO_DEFENSE,
    "prompt_defense": D1_PROMPT_DEFENSE,
    "D1": D1_PROMPT_DEFENSE,
    "guard_agent": D2_GUARD_AGENT,
    "D2": D2_GUARD_AGENT,
    "memory_or_inter_agent_redaction": D3_MEMORY_REDACTION,
    "D3": D3_MEMORY_REDACTION,
    "tool_output_filtering": D4_TOOL_OUTPUT_FILTERING,
    "D4": D4_TOOL_OUTPUT_FILTERING,
}


def get_defense(name: str) -> DefenseConfig:
    """Resolve defense name to DefenseConfig."""
    key = name.strip()
    if key in DEFENSE_PRESETS:
        return DEFENSE_PRESETS[key]
    return DefenseConfig(name=key, defense_type="no_defense", strength=0.0)
