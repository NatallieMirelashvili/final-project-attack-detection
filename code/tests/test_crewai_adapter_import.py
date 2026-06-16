"""Tests for CrewAISyntheticAdapter."""

from agent_redteam.adapters.crewai_adapter import CrewAISyntheticAdapter
from agent_redteam.data.synthetic_tasks import generate_synthetic_tasks
from agent_redteam.schemas import AttackVariant


def test_crewai_import_without_crewai_installed():
    adapter = CrewAISyntheticAdapter()
    adapter.setup({"random_seed": 42})
    assert adapter.system_name == "crewai_synthetic"
    adapter.teardown()


def test_crewai_fallback_clean_and_attacked():
    adapter = CrewAISyntheticAdapter()
    adapter.setup({"random_seed": 42})
    tasks = generate_synthetic_tasks(2, 42)

    clean = adapter.run_clean(tasks[0])
    assert clean.system_name == "crewai_synthetic"
    assert clean.task_success

    attack = AttackVariant(
        id="crewai_atk",
        goal="degradation",
        prompt_template="Fail task.",
        injection_location="system_prompt",
        target_channel="final_output",
        target_agent="worker",
        stealth_level=0.9,
    )
    attacked = adapter.run_attacked(tasks[0], attack, None)
    assert attacked.attack_variant_id == "crewai_atk"
    adapter.teardown()
