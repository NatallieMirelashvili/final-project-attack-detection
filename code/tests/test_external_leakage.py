"""Tests for external leakage objective, finalizer modes, and AutoResearch v2."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from agent_redteam.adapters.calibration import load_calibration
from agent_redteam.adapters.finalizer_exposure import apply_finalizer_exposure
from agent_redteam.adapters.mock_adapter import MockAdapter
from agent_redteam.attacks.families import ATTACK_FAMILIES, variant_from_family
from agent_redteam.attacks.generators import AutoResearchAttackGenerator, get_attack_generator
from agent_redteam.attacks.auto_research_v2 import AutoResearchV2AttackGenerator
from agent_redteam.data.synthetic_tasks import generate_synthetic_tasks
from agent_redteam.defenses.defense_config import D0_NO_DEFENSE
from agent_redteam.evaluation.leakage_metrics import final_output_leakage_rate
from agent_redteam.evaluation.scorer import score_external_leakage_variant, score_leakage_variant
from agent_redteam.experiments.runner import ExperimentRunner, load_config
from agent_redteam.summarize_results import summarize
from agent_redteam.table_aggregation import infer_experiment_group

EXTERNAL_CONFIGS = [
    "mock_external_leakage_medium.yaml",
    "langgraph_external_leakage_medium.yaml",
]

ALL_EXTERNAL_CONFIGS = [
    "mock_external_leakage_medium.yaml",
    "mock_external_leakage_hard.yaml",
    "langgraph_external_leakage_medium.yaml",
    "langgraph_external_leakage_hard.yaml",
    "autogen_external_leakage_medium.yaml",
    "crewai_external_leakage_medium.yaml",
]


def _configs_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "configs"


def test_external_leakage_configs_load():
    for name in ALL_EXTERNAL_CONFIGS:
        cfg = load_config(_configs_dir() / name)
        assert cfg.goal == "external_leakage"
        assert cfg.attack_generator_version == "v2"
        assert cfg.adapter_config.get("finalizer_exposure_mode")


def test_finalizer_mode_in_metrics_summary(tmp_path):
    cfg_path = tmp_path / "ext.yaml"
    output = str(tmp_path / "results")
    cfg_path.write_text(
        f"""
experiment_name: mock_external_test
system_name: mock
goal: external_leakage
num_iterations: 2
num_tasks: 3
attack_generator: random
defense: no_defense
calibration_profile: medium
reward_profile: external_leakage
finalizer_exposure_mode: tool_and_memory_summary
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
  finalizer_exposure_mode: tool_and_memory_summary
""",
        encoding="utf-8",
    )
    metrics = ExperimentRunner(load_config(cfg_path)).run()
    assert metrics["finalizer_exposure_mode"] == "tool_and_memory_summary"
    assert metrics["goal"] == "external_leakage"
    assert "external_leakage" in metrics


def test_external_reward_prioritizes_final_output():
    tasks = generate_synthetic_tasks(4, 42)
    tasks_map = {t.id: t for t in tasks}
    adapter = MockAdapter()
    adapter.setup(
        {
            "random_seed": 42,
            "calibration_profile": "medium",
            "finalizer_exposure_mode": "tool_and_memory_summary",
        }
    )
    attack = variant_from_family(
        "final_output_exfiltration", "external_leakage", "ext_atk"
    )
    runs = []
    clean = []
    for task in tasks:
        clean.append(adapter.run_clean(task))
        runs.append(adapter.run_attacked(task, attack, D0_NO_DEFENSE))
    adapter.teardown()

    ext_score = score_external_leakage_variant(runs, clean, tasks_map, variant=attack)
    leak_score = score_leakage_variant(runs, clean, tasks_map, variant=attack)
    final_rate = final_output_leakage_rate(runs, tasks_map)
    if final_rate > 0:
        assert ext_score >= leak_score * 0.5


def test_safe_finalizer_lower_external_than_tool_summary():
    tasks = generate_synthetic_tasks(10, 99)
    attack = variant_from_family(
        "summary_contamination", "external_leakage", "safe_cmp"
    )
    rates = {}
    for mode in ("safe_finalizer", "tool_and_memory_summary"):
        adapter = MockAdapter()
        adapter.setup(
            {
                "random_seed": 99,
                "calibration_profile": "medium",
                "finalizer_exposure_mode": mode,
            }
        )
        runs = [adapter.run_attacked(t, attack, D0_NO_DEFENSE) for t in tasks]
        adapter.teardown()
        tasks_map = {t.id: t for t in tasks}
        rates[mode] = final_output_leakage_rate(runs, tasks_map)
    assert rates["safe_finalizer"] <= rates["tool_and_memory_summary"]


def test_autoresearch_v2_selectable(tmp_path):
    gen = get_attack_generator(
        "auto_research",
        "external_leakage",
        42,
        version="v2",
        output_path=tmp_path,
        system_name="mock",
    )
    assert isinstance(gen, AutoResearchV2AttackGenerator)
    v = gen.generate(0)
    assert v.metadata.get("attack_family") or v.metadata.get("generator_version") == "v2"


def test_autoresearch_v1_backward_compatible():
    gen = get_attack_generator("auto_research", "leakage", 42, version="v1")
    assert isinstance(gen, AutoResearchAttackGenerator)
    v = gen.generate(0)
    assert v.goal == "leakage"


def test_autoresearch_v2_writes_diagnostics(tmp_path):
    output = tmp_path / "exp_out"
    gen = AutoResearchV2AttackGenerator(
        goal="external_leakage",
        random_seed=42,
        output_path=output,
        system_name="mock",
    )
    variant = gen.generate(0)
    gen.record_score(variant, 0.5)
    gen.write_diagnostics()
    assert (output / "family_success_rates.json").exists()
    assert (output / "generator_diagnostics.json").exists()
    assert (output / "search_history.jsonl").exists()


def test_external_clean_tables_created(tmp_path):
    output = str(tmp_path / "results")
    cfg = tmp_path / "ext.yaml"
    cfg.write_text(
        f"""
experiment_name: mock_external_leakage_medium
system_name: mock
goal: external_leakage
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
attack_generator_version: v2
defense: no_defense
calibration_profile: medium
reward_profile: external_leakage
finalizer_exposure_mode: tool_and_memory_summary
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
  finalizer_exposure_mode: tool_and_memory_summary
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(cfg)).run()
    summary = summarize(output)
    tables = [
        "internal_clean_external_leakage_results.csv",
        "internal_clean_external_attack_comparison.csv",
        "internal_clean_external_defense_comparison.csv",
        "internal_clean_external_leakage_summary.csv",
        "internal_clean_autoresearch_v2_diagnostics.csv",
    ]
    for t in tables:
        assert (summary / t).exists(), t


def test_external_clean_tables_exclude_legacy(tmp_path):
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
    medium = tmp_path / "medium.yaml"
    medium.write_text(
        f"""
experiment_name: mock_external_leakage_medium
system_name: mock
goal: external_leakage
num_iterations: 2
num_tasks: 3
attack_generator: random
defense: no_defense
calibration_profile: medium
finalizer_exposure_mode: tool_and_memory_summary
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
  finalizer_exposure_mode: tool_and_memory_summary
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(legacy)).run()
    ExperimentRunner(load_config(medium)).run()
    summary = summarize(output)
    with (summary / "internal_clean_external_leakage_results.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert all(r["goal"] == "external_leakage" for r in rows)
    assert all(r["experiment_name"] != "mock_leakage_legacy" for r in rows)


def test_attack_families_defined():
    assert len(ATTACK_FAMILIES) >= 8


def test_external_attack_compare_v1_v2_distinguishable(tmp_path):
    output = str(tmp_path / "results")
    for name in (
        "langgraph_external_attack_compare_auto_v1",
        "langgraph_external_attack_compare_auto_v2",
    ):
        cfg = load_config(_configs_dir() / f"{name}.yaml")
        cfg = cfg.__class__(
            **{
                **cfg.__dict__,
                "output_dir": output,
                "num_iterations": 3,
                "num_tasks": 3,
            }
        )
        ExperimentRunner(cfg).run()
    summary = summarize(output)
    with (summary / "internal_clean_external_attack_comparison.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    versions = {r["attack_generator_version"] for r in rows}
    names = {r["experiment_name"] for r in rows}
    assert "v1" in versions
    assert "v2" in versions
    assert "langgraph_external_attack_compare_auto_v1" in names
    assert "langgraph_external_attack_compare_auto_v2" in names
    md = (summary / "paper_tables.md").read_text(encoding="utf-8")
    assert "External Attack Comparison" in md


def test_paper_tables_external_sections(tmp_path):
    output = str(tmp_path / "results")
    cfg = tmp_path / "ext.yaml"
    cfg.write_text(
        f"""
experiment_name: mock_external_leakage_medium
system_name: mock
goal: external_leakage
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
attack_generator_version: v2
defense: no_defense
calibration_profile: medium
reward_profile: external_leakage
finalizer_exposure_mode: tool_and_memory_summary
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
  finalizer_exposure_mode: tool_and_memory_summary
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(cfg)).run()
    summary = summarize(output)
    md = (summary / "paper_tables.md").read_text(encoding="utf-8")
    assert "External Leakage Results" in md
    assert "External Leakage Summary" in md
    assert "AutoResearch v2 Diagnostics" in md


def test_degradation_experiment_group():
    assert infer_experiment_group(
        "mock_degradation_medium", "mock_degradation_medium", "degradation", "medium"
    ) == "degradation"
