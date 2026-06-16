"""End-to-end tests for experiment runner."""

import json
from pathlib import Path

import pytest

from agent_redteam.experiments.runner import ExperimentRunner, load_config
from agent_redteam.experiments.transfer_runner import TransferRunner
from agent_redteam.summarize_results import summarize


@pytest.fixture
def tmp_results(tmp_path):
    return tmp_path / "results"


def _write_config(tmp_path: Path, name: str, goal: str, output_dir: str) -> Path:
    config_path = tmp_path / f"{name}.yaml"
    config_path.write_text(
        f"""
experiment_name: {name}
system_name: mock
goal: {goal}
num_iterations: 3
num_tasks: 3
attack_generator: auto_research
defense: no_defense
output_dir: {output_dir}
random_seed: 42
adapter_type: mock
""",
        encoding="utf-8",
    )
    return config_path


def test_leakage_experiment_end_to_end(tmp_path):
    output_dir = str(tmp_path / "results")
    config_path = _write_config(tmp_path, "test_leakage", "leakage", output_dir)
    config = load_config(config_path)
    runner = ExperimentRunner(config)
    metrics = runner.run()

    exp_dir = Path(output_dir) / "test_leakage"
    assert (exp_dir / "runs.jsonl").exists()
    assert (exp_dir / "variants.jsonl").exists()
    assert (exp_dir / "metrics_summary.json").exists()
    assert (exp_dir / "trace_samples.jsonl").exists()
    assert (exp_dir / "best_variants.jsonl").exists()
    assert (exp_dir / "leakage_results.csv").exists()
    assert "leakage" in metrics


def test_degradation_experiment_end_to_end(tmp_path):
    output_dir = str(tmp_path / "results")
    config_path = _write_config(tmp_path, "test_degradation", "degradation", output_dir)
    config = load_config(config_path)
    runner = ExperimentRunner(config)
    metrics = runner.run()

    exp_dir = Path(output_dir) / "test_degradation"
    assert (exp_dir / "degradation_results.csv").exists()
    assert "performance" in metrics


def test_transfer_and_summarize_end_to_end(tmp_path):
    output_dir = str(tmp_path / "results")
    leak_config = _write_config(tmp_path, "mock_leakage", "leakage", output_dir)
    config = load_config(leak_config)
    ExperimentRunner(config).run()

    transfer_config = tmp_path / "transfer.yaml"
    transfer_config.write_text(
        f"""
source_experiment: mock_leakage
target_experiment: transfer_mock_target
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
target_adapter_suffix: target
""",
        encoding="utf-8",
    )
    TransferRunner(transfer_config).run()

    target_dir = Path(output_dir) / "transfer_mock_target"
    assert (target_dir / "transfer_results.csv").exists()
    assert (target_dir / "metrics_summary.json").exists()

    summary_path = summarize(output_dir)
    assert summary_path.exists()
    assert (summary_path / "leakage_results.csv").exists()
    assert (summary_path / "transfer_results.csv").exists()
