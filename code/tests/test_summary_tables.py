"""Tests for paper-ready summary tables."""

import csv
from pathlib import Path

from agent_redteam.experiments.runner import ExperimentRunner, load_config
from agent_redteam.summarize_results import summarize


def _write_mini_config(tmp_path: Path, name: str, goal: str) -> None:
    output_dir = str(tmp_path / "results")
    config_path = tmp_path / f"{name}.yaml"
    config_path.write_text(
        f"""
experiment_name: {name}
system_name: autogen_synthetic
goal: {goal}
num_iterations: 2
num_tasks: 3
attack_generator: manual_baseline
defense: no_defense
output_dir: {output_dir}
random_seed: 42
adapter_type: autogen_synthetic
adapter_config: {{}}
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(config_path)).run()


def test_paper_summary_tables_created(tmp_path):
    _write_mini_config(tmp_path, "autogen_synthetic_leakage", "leakage")
    _write_mini_config(tmp_path, "autogen_synthetic_degradation", "degradation")

    summary_path = summarize(str(tmp_path / "results"))

    assert (summary_path / "table_leakage_by_system.csv").exists()
    assert (summary_path / "table_internal_vs_final_leakage.csv").exists()
    assert (summary_path / "table_degradation_by_system.csv").exists()
    assert (summary_path / "table_defense_tradeoff.csv").exists()
    assert (summary_path / "table_transferability_matrix.csv").exists()
    assert (summary_path / "table_best_variants.csv").exists()
    assert (summary_path / "paper_tables.md").exists()
    assert (summary_path / "table_attack_comparison.csv").exists()
    assert (summary_path / "table_difficulty_comparison.csv").exists()
    assert (summary_path / "table_defense_comparison.csv").exists()

    md = (summary_path / "paper_tables.md").read_text(encoding="utf-8")
    assert "# Paper Tables" in md
    assert "Leakage by System" in md
    assert "integration_mode" in md
    assert "calibration_profile" in md

    with (summary_path / "table_leakage_by_system.csv").open(encoding="utf-8") as f:
        headers = next(csv.reader(f))
    assert "integration_mode" in headers
    assert "calibration_profile" in headers
