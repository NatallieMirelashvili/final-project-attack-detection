"""Tests for selective finalizer exposure and discriminative external leakage benchmark."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from agent_redteam.adapters.mock_adapter import MockAdapter
from agent_redteam.attacks.auto_research_v2 import AutoResearchV2AttackGenerator
from agent_redteam.attacks.families import ATTACK_FAMILIES, PROPAGATION_META_KEYS, variant_from_family
from agent_redteam.data.synthetic_tasks import generate_synthetic_tasks
from agent_redteam.defenses.defense_config import D0_NO_DEFENSE
from agent_redteam.evaluation.leakage_metrics import final_output_leakage_rate
from agent_redteam.experiments.runner import ExperimentRunner, load_config
from agent_redteam.summarize_results import summarize
from agent_redteam.table_aggregation import (
    filter_internal_clean_external_selective_attack_comparison,
    infer_experiment_group,
)

SELECTIVE_ATTACK_COMPARE_CONFIGS = [
    "langgraph_external_selective_attack_compare_random.yaml",
    "langgraph_external_selective_attack_compare_manual.yaml",
    "langgraph_external_selective_attack_compare_auto_v1.yaml",
    "langgraph_external_selective_attack_compare_auto_v2.yaml",
]

SELECTIVE_LEAKAGE_CONFIGS = [
    "mock_external_leakage_selective_medium.yaml",
    "langgraph_external_leakage_selective_medium.yaml",
    "autogen_external_leakage_selective_medium.yaml",
    "crewai_external_leakage_selective_medium.yaml",
]


def _configs_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "configs"


def test_selective_finalizer_context_mode_loads():
    cfg = load_config(_configs_dir() / "mock_external_leakage_selective_medium.yaml")
    assert cfg.adapter_config.get("finalizer_exposure_mode") == "selective_finalizer_context"


def test_selective_leakage_not_higher_than_tool_summary():
    tasks = generate_synthetic_tasks(12, 77)
    attack = variant_from_family("final_output_exfiltration", "external_leakage", "sel_cmp")
    rates = {}
    for mode in ("selective_finalizer_context", "tool_and_memory_summary"):
        adapter = MockAdapter()
        adapter.setup(
            {
                "random_seed": 77,
                "calibration_profile": "medium",
                "finalizer_exposure_mode": mode,
            }
        )
        runs = [adapter.run_attacked(t, attack, D0_NO_DEFENSE) for t in tasks]
        adapter.teardown()
        tasks_map = {t.id: t for t in tasks}
        rates[mode] = final_output_leakage_rate(runs, tasks_map)
    assert rates["selective_finalizer_context"] <= rates["tool_and_memory_summary"]


def test_selective_leakage_not_lower_than_safe_finalizer_compatible_attack():
    tasks = generate_synthetic_tasks(12, 88)
    attack = variant_from_family("multi_hop_agent_relay", "external_leakage", "sel_safe")
    rates = {}
    for mode in ("safe_finalizer", "selective_finalizer_context"):
        adapter = MockAdapter()
        adapter.setup(
            {
                "random_seed": 88,
                "calibration_profile": "medium",
                "finalizer_exposure_mode": mode,
            }
        )
        runs = [adapter.run_attacked(t, attack, D0_NO_DEFENSE) for t in tasks]
        adapter.teardown()
        tasks_map = {t.id: t for t in tasks}
        rates[mode] = final_output_leakage_rate(runs, tasks_map)
    assert rates["selective_finalizer_context"] >= rates["safe_finalizer"]


def test_propagation_compatibility_metadata_on_families():
    assert len(ATTACK_FAMILIES) >= 8
    for family_id, spec in ATTACK_FAMILIES.items():
        for key in PROPAGATION_META_KEYS:
            assert key in spec, f"{family_id} missing {key}"
    variant = variant_from_family("memory_to_final_propagation", "external_leakage", "meta_chk")
    for key in PROPAGATION_META_KEYS:
        assert key in variant.metadata


def test_autoresearch_v2_external_uses_final_output_family_reward(tmp_path):
    gen = AutoResearchV2AttackGenerator(
        goal="external_leakage",
        random_seed=42,
        output_path=tmp_path,
        system_name="mock",
    )
    variant = gen.generate(0)
    gen.record_score(variant, 0.2, final_output_leakage_rate=0.9)
    gen.write_diagnostics()
    with (tmp_path / "family_success_rates.json").open(encoding="utf-8") as f:
        data = json.load(f)
    assert data["primary_external_signal"] == "final_output_leakage_rate"
    family = str(variant.metadata.get("attack_family", "unknown"))
    assert data["family_mean_final_output_rates"].get(family) == 0.9


def test_selective_attack_compare_configs_load():
    for name in SELECTIVE_ATTACK_COMPARE_CONFIGS:
        cfg = load_config(_configs_dir() / name)
        assert cfg.goal == "external_leakage"
        assert cfg.adapter_config.get("finalizer_exposure_mode") == "selective_finalizer_context"
        assert cfg.adapter_config.get("calibration_profile") == "medium"
        assert "selective" in cfg.experiment_name and "attack_compare" in cfg.experiment_name


def test_selective_clean_tables_created(tmp_path):
    output = str(tmp_path / "results")
    cfg_path = tmp_path / "selective.yaml"
    cfg_path.write_text(
        f"""
experiment_name: langgraph_external_selective_attack_compare_random
system_name: langgraph_synthetic
goal: external_leakage
num_iterations: 2
num_tasks: 3
attack_generator: random
defense: no_defense
calibration_profile: medium
reward_profile: external_leakage
finalizer_exposure_mode: selective_finalizer_context
output_dir: {output}
random_seed: 42
adapter_type: langgraph_synthetic
adapter_config:
  calibration_profile: medium
  finalizer_exposure_mode: selective_finalizer_context
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(cfg_path)).run()
    summary = summarize(output)
    assert (summary / "internal_clean_external_selective_attack_comparison.csv").exists()
    assert (summary / "internal_clean_external_selective_summary.csv").exists()


def test_selective_clean_tables_exclude_legacy(tmp_path):
    output = str(tmp_path / "results")
    legacy = tmp_path / "legacy.yaml"
    legacy.write_text(
        f"""
experiment_name: mock_leakage_legacy
system_name: mock
goal: leakage
num_iterations: 2
num_tasks: 3
attack_generator: random
defense: no_defense
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config: {{}}
""",
        encoding="utf-8",
    )
    selective = tmp_path / "selective.yaml"
    selective.write_text(
        f"""
experiment_name: mock_external_leakage_selective_medium
system_name: mock
goal: external_leakage
num_iterations: 2
num_tasks: 3
attack_generator: random
defense: no_defense
calibration_profile: medium
finalizer_exposure_mode: selective_finalizer_context
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
  finalizer_exposure_mode: selective_finalizer_context
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(legacy)).run()
    ExperimentRunner(load_config(selective)).run()
    summary = summarize(output)
    with (summary / "internal_clean_external_selective_attack_comparison.csv").open(encoding="utf-8") as f:
        attack_rows = list(csv.DictReader(f))
    with (summary / "internal_clean_external_selective_summary.csv").open(encoding="utf-8") as f:
        summary_rows = list(csv.DictReader(f))

    all_rows = attack_rows + summary_rows
    if attack_rows:
        filtered = filter_internal_clean_external_selective_attack_comparison(attack_rows)
        assert all(r.get("finalizer_exposure_mode") == "selective_finalizer_context" for r in filtered)
    assert all(r.get("experiment_name") != "mock_leakage_legacy" for r in all_rows if r.get("experiment_name"))


def test_paper_tables_includes_selective_sections(tmp_path):
    output = str(tmp_path / "results")
    cfg_path = tmp_path / "selective.yaml"
    cfg_path.write_text(
        f"""
experiment_name: langgraph_external_selective_attack_compare_auto_v2
system_name: langgraph_synthetic
goal: external_leakage
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
attack_generator_version: v2
defense: no_defense
calibration_profile: medium
reward_profile: external_leakage
finalizer_exposure_mode: selective_finalizer_context
output_dir: {output}
random_seed: 42
adapter_type: langgraph_synthetic
adapter_config:
  calibration_profile: medium
  finalizer_exposure_mode: selective_finalizer_context
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(cfg_path)).run()
    summary = summarize(output)
    paper = (summary / "paper_tables.md").read_text(encoding="utf-8")
    assert "External Selective Attack Comparison" in paper
    assert "External Selective Summary" in paper
