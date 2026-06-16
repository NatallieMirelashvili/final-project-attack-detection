"""Tests for attack generators."""

from agent_redteam.attacks.generators import (
    AutoResearchAttackGenerator,
    ManualBaselineAttackGenerator,
    RandomAttackGenerator,
    get_attack_generator,
)
from agent_redteam.attacks.mutation import mutate_variant, random_variant
from agent_redteam.schemas import AttackVariant


def test_random_attack_generator():
    gen = RandomAttackGenerator("leakage", random_seed=42)
    v1 = gen.generate(0)
    v2 = gen.generate(1)
    assert v1.goal == "leakage"
    assert v1.id != v2.id


def test_manual_baseline_generator():
    gen = ManualBaselineAttackGenerator("leakage", random_seed=42)
    v = gen.generate(0)
    assert "baseline" in v.metadata or v.id.startswith("baseline")


def test_auto_research_mutates_high_scorers():
    gen = AutoResearchAttackGenerator("leakage", random_seed=42)
    variants = [gen.generate(i) for i in range(5)]
    for v, score in zip(variants, [0.1, 0.5, 0.9, 0.3, 0.7]):
        gen.record_score(v, score)
    accepted = gen.get_accepted_variants()
    assert len(accepted) >= 1
    next_v = gen.generate(10)
    assert next_v.goal == "leakage"


def test_mutate_variant():
    parent = random_variant("degradation", __import__("random").Random(42), "parent")
    child = mutate_variant(parent, __import__("random").Random(43), "child")
    assert child.id == "child"
    assert child.metadata.get("parent_id") == "parent"


def test_get_attack_generator_factory():
    gen = get_attack_generator("auto_research", "leakage", 42)
    assert isinstance(gen, AutoResearchAttackGenerator)
