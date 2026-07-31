"""Tests for degradation family attack generator."""

from __future__ import annotations

from agent_redteam.attacks.degradation_families import (
    DEGRADATION_FAMILY_ORDER,
    DEGRADATION_FAMILIES,
    variant_from_degradation_family,
)
from agent_redteam.attacks.generators import DegradationFamilyAttackGenerator, get_attack_generator


def test_degradation_family_count_and_order() -> None:
    assert len(DEGRADATION_FAMILY_ORDER) == 6
    assert set(DEGRADATION_FAMILY_ORDER) == set(DEGRADATION_FAMILIES.keys())


def test_degradation_family_generator_cycles_six_families() -> None:
    gen = DegradationFamilyAttackGenerator(goal="degradation", random_seed=42)
    families = []
    for i in range(6):
        variant = gen.generate(i)
        assert variant.goal == "degradation"
        family = variant.metadata["degradation_family"]
        families.append(family)
        assert variant.injection_location == DEGRADATION_FAMILIES[family]["injection_location"]
    assert families == DEGRADATION_FAMILY_ORDER


def test_get_attack_generator_degradation_families() -> None:
    gen = get_attack_generator("degradation_families", goal="degradation", random_seed=42)
    assert isinstance(gen, DegradationFamilyAttackGenerator)
    variant = gen.generate(0)
    assert variant.metadata.get("degradation_family") == DEGRADATION_FAMILY_ORDER[0]


def test_variant_from_degradation_family_metadata() -> None:
    variant = variant_from_degradation_family("verification_loop", "test_001")
    assert variant.metadata["attack_family"] == "verification_loop"
    assert "expected_signals" in variant.metadata
