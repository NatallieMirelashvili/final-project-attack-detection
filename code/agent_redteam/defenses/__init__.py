"""Defense modules."""

from agent_redteam.defenses.defense_config import (
    DefenseConfig,
    D0_NO_DEFENSE,
    D1_PROMPT_DEFENSE,
    D2_GUARD_AGENT,
    D3_MEMORY_REDACTION,
    D4_TOOL_OUTPUT_FILTERING,
    DEFENSE_PRESETS,
    get_defense,
)
from agent_redteam.defenses.filters import apply_defense

__all__ = [
    "DefenseConfig",
    "D0_NO_DEFENSE",
    "D1_PROMPT_DEFENSE",
    "D2_GUARD_AGENT",
    "D3_MEMORY_REDACTION",
    "D4_TOOL_OUTPUT_FILTERING",
    "DEFENSE_PRESETS",
    "get_defense",
    "apply_defense",
]
