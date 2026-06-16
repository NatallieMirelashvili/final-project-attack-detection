"""Tests for cross-framework transfer matrix."""

from pathlib import Path

from agent_redteam.experiments.runner import ExperimentRunner, load_config
from agent_redteam.experiments.transfer_runner import TransferRunner


def _mini_leakage_config(tmp_path: Path, name: str, system: str, adapter_type: str) -> Path:
    output_dir = str(tmp_path / "results")
    path = tmp_path / f"{name}.yaml"
    path.write_text(
        f"""
experiment_name: {name}
system_name: {system}
goal: leakage
num_iterations: 2
num_tasks: 3
attack_generator: manual_baseline
defense: no_defense
output_dir: {output_dir}
random_seed: 42
adapter_type: {adapter_type}
adapter_config: {{}}
""",
        encoding="utf-8",
    )
    return path


def test_cross_framework_transfer_matrix(tmp_path):
    ad_path = _mini_leakage_config(tmp_path, "agentdojo_leakage", "agentdojo", "agentdojo")
    ad_config = load_config(ad_path)
    ad_config.adapter_config = {"agentdojo_mock_mode": True}
    ExperimentRunner(ad_config).run()

    lg_path = _mini_leakage_config(
        tmp_path, "langgraph_synthetic_leakage", "langgraph_synthetic", "langgraph_synthetic"
    )
    ExperimentRunner(load_config(lg_path)).run()

    output_dir = str(tmp_path / "results")
    matrix_config = tmp_path / "matrix.yaml"
    matrix_config.write_text(
        f"""
mode: matrix
target_experiment: transfer_cross_framework_matrix
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
sources:
  - experiment: agentdojo_leakage
    system_name: agentdojo
  - experiment: langgraph_synthetic_leakage
    system_name: langgraph_synthetic
targets:
  - system_name: autogen_synthetic
    adapter_suffix: matrix_autogen
  - system_name: crewai_synthetic
    adapter_suffix: matrix_crewai
""",
        encoding="utf-8",
    )

    metrics = TransferRunner(matrix_config).run()
    target_dir = tmp_path / "results" / "transfer_cross_framework_matrix"

    assert (target_dir / "transfer_matrix.csv").exists()
    assert (target_dir / "transfer_results.csv").exists()
    assert (target_dir / "transfer_runs.jsonl").exists()
    assert (target_dir / "metrics_summary.json").exists()
    assert len(metrics.get("transfer_matrix", [])) >= 4
