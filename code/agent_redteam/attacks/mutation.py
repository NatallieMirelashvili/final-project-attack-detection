"""Attack variant mutation for AutoResearch search."""

from __future__ import annotations

import random
from typing import List

from agent_redteam.attacks.variants import (
    INJECTION_LOCATIONS,
    PROMPT_TEMPLATES,
    TARGET_AGENTS,
    TARGET_CHANNELS,
)
from agent_redteam.schemas import AttackVariant


def mutate_variant(
    parent: AttackVariant,
    rng: random.Random,
    variant_id: str,
) -> AttackVariant:
    """Mutate a high-scoring attack variant."""
    injection = parent.injection_location
    channel = parent.target_channel
    agent = parent.target_agent
    stealth = parent.stealth_level
    template = parent.prompt_template

    mutation_type = rng.choice(
        ["injection", "channel", "agent", "stealth", "template", "combo"]
    )

    if mutation_type in ("injection", "combo"):
        injection = rng.choice(INJECTION_LOCATIONS)
    if mutation_type in ("channel", "combo"):
        channel = rng.choice(TARGET_CHANNELS)
    if mutation_type in ("agent", "combo"):
        agent = rng.choice(TARGET_AGENTS)
    if mutation_type in ("stealth", "combo"):
        delta = rng.uniform(-0.2, 0.2)
        stealth = max(0.0, min(1.0, parent.stealth_level + delta))
    if mutation_type in ("template", "combo"):
        template = rng.choice(PROMPT_TEMPLATES)

    return AttackVariant(
        id=variant_id,
        goal=parent.goal,
        prompt_template=template,
        injection_location=injection,
        target_channel=channel,
        target_agent=agent,
        stealth_level=stealth,
        metadata={
            "parent_id": parent.id,
            "mutation_type": mutation_type,
            "generation": parent.metadata.get("generation", 0) + 1,
        },
    )


def random_variant(
    goal: str,
    rng: random.Random,
    variant_id: str,
) -> AttackVariant:
    """Create a random attack variant."""
    return AttackVariant(
        id=variant_id,
        goal=goal,
        prompt_template=rng.choice(PROMPT_TEMPLATES),
        injection_location=rng.choice(INJECTION_LOCATIONS),
        target_channel=rng.choice(TARGET_CHANNELS),
        target_agent=rng.choice(TARGET_AGENTS),
        stealth_level=rng.uniform(0.1, 0.9),
        metadata={"generation": 0},
    )
