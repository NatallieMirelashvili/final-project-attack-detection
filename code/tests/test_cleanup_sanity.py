"""Sanity tests for cleanup fixes: metadata, tables, configs, AgentDojo mock calibration."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from agent_redteam.experiments.experiment_metadata import resolve_calibration_profile
from agent_redteam.experiments.runner import ExperimentRunner, load_config
from agent_redteam.experiments.transfer_runner import TransferRunner
from agent_redteam.summarize_results import summarize

REQUIRED_METADATA_KEYS = [
    "experiment_name",
    "system_name",
    "architecture",
    "integration_mode",
    "calibration_profile",
    "attack_generator",
    "defense",
    "goal",
    "random_seed",
    "num_iterations",
    "num_tasks",
]

TABLES_WITH_META = [
    "table_leakage_by_system.csv",
    "table_attack_comparison.csv",
    "table_difficulty_comparison.csv",
    "table_defense_comparison.csv",
    "table_transferability_matrix.csv",
]


def _configs_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "configs"


def test_langgraph_defense_alias_config_loads():
    path = _configs_dir() / "langgraph_defense_memory_or_inter_agent_redaction.yaml"
    assert path.exists()
    config = load_config(path)
    assert config.defense == "memory_or_inter_agent_redaction"
    assert config.adapter_config.get("calibration_profile") == "medium"
    assert config.attack_generator == "auto_research"


def test_metrics_summary_includes_metadata(tmp_path):
    output = str(tmp_path / "results")
    cfg_path = tmp_path / "meta_test.yaml"
    cfg_path.write_text(
        f"""
experiment_name: meta_test_leakage
system_name: langgraph_synthetic
goal: leakage
num_iterations: 2
num_tasks: 3
attack_generator: random
defense: no_defense
calibration_profile: medium
output_dir: {output}
random_seed: 42
adapter_type: langgraph_synthetic
adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    metrics = ExperimentRunner(load_config(cfg_path)).run()
    for key in REQUIRED_METADATA_KEYS:
        assert key in metrics, f"missing {key} in run metrics"

    summary_path = Path(output) / "meta_test_leakage" / "metrics_summary.json"
    with summary_path.open(encoding="utf-8") as f:
        saved = json.load(f)
    for key in REQUIRED_METADATA_KEYS:
        assert key in saved, f"missing {key} in metrics_summary.json"
    assert saved["integration_mode"] == "synthetic_fallback"
    assert saved["calibration_profile"] == "medium"


def test_summarize_tables_include_integration_and_calibration(tmp_path):
    output = str(tmp_path / "results")
    cfg_path = tmp_path / "table_meta.yaml"
    cfg_path.write_text(
        f"""
experiment_name: table_meta_leakage
system_name: autogen_synthetic
goal: leakage
num_iterations: 2
num_tasks: 3
attack_generator: manual_baseline
defense: no_defense
calibration_profile: medium
output_dir: {output}
random_seed: 11
adapter_type: autogen_synthetic
adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(cfg_path)).run()
    summary_path = summarize(output)

    for table_name in TABLES_WITH_META:
        table_path = summary_path / table_name
        assert table_path.exists(), table_name
        with table_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            assert "integration_mode" in headers, table_name
            assert "calibration_profile" in headers, table_name


def test_legacy_experiments_labelled_legacy(tmp_path):
    assert resolve_calibration_profile({}) == "legacy"
    assert resolve_calibration_profile({"calibration_profile": "legacy"}) == "legacy"

    output = str(tmp_path / "results")
    cfg_path = tmp_path / "legacy_test.yaml"
    cfg_path.write_text(
        f"""
experiment_name: legacy_no_profile_leakage
system_name: mock
goal: leakage
num_iterations: 2
num_tasks: 3
attack_generator: random
defense: no_defense
output_dir: {output}
random_seed: 5
adapter_type: mock
adapter_config: {{}}
""",
        encoding="utf-8",
    )
    metrics = ExperimentRunner(load_config(cfg_path)).run()
    assert metrics["calibration_profile"] == "legacy"
    assert metrics["integration_mode"] == "mock"


def test_agentdojo_mock_medium_attack_comparison_not_all_one(tmp_path):
    output = str(tmp_path / "results")
    configs_dir = _configs_dir()
    asrs: list[float] = []

    for name in (
        "agentdojo_attack_compare_random",
        "agentdojo_attack_compare_manual",
        "agentdojo_attack_compare_auto",
    ):
        cfg = load_config(configs_dir / f"{name}.yaml")
        cfg = cfg.__class__(
            **{**cfg.__dict__, "output_dir": output, "num_iterations": 6, "num_tasks": 6}
        )
        metrics = ExperimentRunner(cfg).run()
        assert metrics["calibration_profile"] == "medium"
        assert metrics["integration_mode"] == "mock"
        asrs.append(metrics["leakage"]["leakage_asr"])

    assert not all(a == 1.0 for a in asrs), f"all ASRs saturated at 1.0: {asrs}"
    assert len(set(asrs)) > 1 or not all(a >= 0.99 for a in asrs)
