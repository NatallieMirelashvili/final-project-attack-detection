"""Tests for summary table aggregation and internal clean analysis tables."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from agent_redteam.experiments.runner import ExperimentRunner, load_config
from agent_redteam.experiments.transfer_runner import TransferRunner
from agent_redteam.summarize_results import summarize
from agent_redteam.table_aggregation import CONFIG_ALIAS_MAP, infer_experiment_group

MAIN_TABLES = [
    "table_leakage_by_system.csv",
    "table_attack_comparison.csv",
    "table_difficulty_comparison.csv",
    "table_defense_comparison.csv",
    "table_internal_vs_final_leakage.csv",
    "table_degradation_by_system.csv",
]

INTERNAL_CLEAN_TABLES = [
    "internal_clean_leakage_results.csv",
    "internal_clean_attack_comparison.csv",
    "internal_clean_defense_comparison.csv",
    "internal_clean_difficulty_comparison.csv",
    "internal_clean_transferability_matrix.csv",
    "internal_clean_degradation_results.csv",
    "internal_clean_transfer_summary.csv",
    "internal_clean_degradation_summary.csv",
]

DEGRADATION_CONFIGS = [
    "mock_degradation_medium.yaml",
    "mock_degradation_hard.yaml",
    "langgraph_synthetic_degradation_medium.yaml",
    "langgraph_synthetic_degradation_hard.yaml",
    "autogen_synthetic_degradation_medium.yaml",
    "crewai_synthetic_degradation_medium.yaml",
]


def _write_leakage_config(
    tmp_path: Path,
    name: str,
    system: str,
    adapter_type: str,
    calibration: str | None = None,
    defense: str = "no_defense",
    attack: str = "auto_research",
) -> Path:
    output_dir = str(tmp_path / "results")
    cal_line = f"calibration_profile: {calibration}\n" if calibration else ""
    adapter_block = (
        f"adapter_config:\n  calibration_profile: {calibration}\n"
        if calibration
        else "adapter_config: {}\n"
    )
    path = tmp_path / f"{name}.yaml"
    path.write_text(
        f"""
experiment_name: {name}
system_name: {system}
goal: leakage
num_iterations: 2
num_tasks: 3
attack_generator: {attack}
defense: {defense}
{cal_line}output_dir: {output_dir}
random_seed: 42
adapter_type: {adapter_type}
{adapter_block}""",
        encoding="utf-8",
    )
    return path


def _read_csv_headers(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as f:
        return next(csv.reader(f))


def test_main_tables_include_experiment_name_and_group(tmp_path):
    _write_leakage_config(
        tmp_path,
        "langgraph_synthetic_leakage_medium",
        "langgraph_synthetic",
        "langgraph_synthetic",
        calibration="medium",
    )
    summary_path = summarize(str(tmp_path / "results"))

    for table_name in MAIN_TABLES:
        table_path = summary_path / table_name
        if not table_path.exists():
            continue
        headers = _read_csv_headers(table_path)
        assert "experiment_name" in headers, table_name
        assert "experiment_group" in headers, table_name


def test_degradation_table_includes_integration_mode_and_calibration(tmp_path):
    output = str(tmp_path / "results")
    cfg = tmp_path / "deg.yaml"
    cfg.write_text(
        f"""
experiment_name: autogen_synthetic_degradation
system_name: autogen_synthetic
goal: degradation
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
defense: no_defense
calibration_profile: medium
output_dir: {output}
random_seed: 42
adapter_type: autogen_synthetic
adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(cfg)).run()
    summary_path = summarize(output)
    headers = _read_csv_headers(summary_path / "table_degradation_by_system.csv")
    assert "integration_mode" in headers
    assert "calibration_profile" in headers


def test_transfer_matrix_preserves_medium_and_hard_calibration(tmp_path):
    output_dir = str(tmp_path / "results")
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path, "langgraph_synthetic_leakage_medium", "langgraph_synthetic",
        "langgraph_synthetic", calibration="medium", attack="manual_baseline",
    ))).run()
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path, "mock_leakage_medium", "mock", "mock",
        calibration="medium", attack="manual_baseline",
    ))).run()

    medium_matrix = tmp_path / "medium_matrix.yaml"
    medium_matrix.write_text(
        f"""
mode: matrix
target_experiment: cross_framework_medium_matrix
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
sources:
  - experiment: langgraph_synthetic_leakage_medium
    system_name: langgraph_synthetic
targets:
  - system_name: autogen_synthetic
    adapter_suffix: matrix_medium_autogen
    adapter_config:
      calibration_profile: medium
""",
        encoding="utf-8",
    )
    medium_metrics = TransferRunner(medium_matrix).run()
    assert medium_metrics["calibration_profile"] == "medium"
    medium_profiles = {
        r["target_calibration_profile"] for r in medium_metrics["transfer_matrix"]
    }
    assert medium_profiles == {"medium"}

    hard_matrix = tmp_path / "hard_matrix.yaml"
    hard_matrix.write_text(
        f"""
mode: matrix
target_experiment: cross_framework_hard_matrix
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
sources:
  - experiment: langgraph_synthetic_leakage_medium
    system_name: langgraph_synthetic
targets:
  - system_name: crewai_synthetic
    adapter_suffix: matrix_hard_crewai
    adapter_config:
      calibration_profile: hard
      transfer_difficulty_penalty: 0.12
""",
        encoding="utf-8",
    )
    hard_metrics = TransferRunner(hard_matrix).run()
    assert hard_metrics["calibration_profile"] == "hard"
    hard_profiles = {
        r["target_calibration_profile"] for r in hard_metrics["transfer_matrix"]
    }
    assert hard_profiles == {"hard"}


def test_transfer_target_system_from_config(tmp_path):
    output_dir = str(tmp_path / "results")
    source_cfg = _write_leakage_config(
        tmp_path,
        "source_leakage_medium",
        "langgraph_synthetic",
        "langgraph_synthetic",
        calibration="medium",
        attack="manual_baseline",
    )
    ExperimentRunner(load_config(source_cfg)).run()

    transfer_cfg = tmp_path / "transfer.yaml"
    transfer_cfg.write_text(
        f"""
source_experiment: source_leakage_medium
target_experiment: transfer_to_autogen
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
target_system_name: autogen_synthetic
target_adapter_suffix: transfer_autogen
target_adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    metrics = TransferRunner(transfer_cfg).run()
    assert metrics["target_system"] == "autogen_synthetic"
    assert metrics["transfer_matrix"][0]["target_system"] == "autogen_synthetic"


def test_alias_defense_not_duplicated_in_clean_defense_table(tmp_path):
    output = str(tmp_path / "results")
    for name in (
        "langgraph_defense_memory_redaction",
        "langgraph_defense_memory_or_inter_agent_redaction",
    ):
        cfg = tmp_path / f"{name}.yaml"
        cfg.write_text(
            f"""
experiment_name: {name}
system_name: langgraph_synthetic
goal: leakage
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
defense: memory_or_inter_agent_redaction
calibration_profile: medium
output_dir: {output}
random_seed: 202
adapter_type: langgraph_synthetic
adapter_config:
  calibration_profile: medium
""",
            encoding="utf-8",
        )
        ExperimentRunner(load_config(cfg)).run()

    summary_path = summarize(output)
    clean_path = summary_path / "internal_clean_defense_comparison.csv"
    assert clean_path.exists()
    with clean_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    exp_names = {r["experiment_name"] for r in rows}
    assert "langgraph_defense_memory_redaction" in exp_names
    assert "langgraph_defense_memory_or_inter_agent_redaction" not in exp_names
    assert CONFIG_ALIAS_MAP[
        "langgraph_defense_memory_or_inter_agent_redaction"
    ] == "langgraph_defense_memory_redaction"


def test_internal_clean_tables_created_and_exclude_legacy(tmp_path):
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path, "legacy_leakage", "mock", "mock"
    ))).run()
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path,
        "langgraph_synthetic_leakage_medium",
        "langgraph_synthetic",
        "langgraph_synthetic",
        calibration="medium",
    ))).run()

    summary_path = summarize(str(tmp_path / "results"))

    for table_name in INTERNAL_CLEAN_TABLES:
        assert (summary_path / table_name).exists(), table_name

    with (summary_path / "internal_clean_leakage_results.csv").open(encoding="utf-8") as f:
        clean_rows = list(csv.DictReader(f))
    assert clean_rows
    assert all(r["calibration_profile"] != "legacy" for r in clean_rows)
    assert all(r["experiment_name"] != "legacy_leakage" for r in clean_rows)


def test_paper_tables_includes_internal_clean_section(tmp_path):
    _write_leakage_config(
        tmp_path,
        "langgraph_attack_compare_random",
        "langgraph_synthetic",
        "langgraph_synthetic",
        calibration="medium",
        attack="random",
    )
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path,
        "langgraph_attack_compare_random",
        "langgraph_synthetic",
        "langgraph_synthetic",
        calibration="medium",
        attack="random",
    ))).run()
    summary_path = summarize(str(tmp_path / "results"))
    md = (summary_path / "paper_tables.md").read_text(encoding="utf-8")
    assert "Internal Clean Analysis Tables" in md


def test_infer_experiment_group_attack_and_defense():
    assert infer_experiment_group(
        "agentdojo_attack_compare_random", "agentdojo_attack_compare_random",
        "leakage", "medium",
    ) == "attack_comparison"
    assert infer_experiment_group(
        "langgraph_defense_guard_agent", "langgraph_defense_guard_agent",
        "leakage", "medium",
    ) == "defense_comparison"
    assert infer_experiment_group(
        "mock_degradation_medium", "mock_degradation_medium",
        "degradation", "medium",
    ) == "degradation"


def test_internal_clean_transfer_includes_all_variant_rows(tmp_path):
    output_dir = str(tmp_path / "results")
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path, "langgraph_synthetic_leakage_medium", "langgraph_synthetic",
        "langgraph_synthetic", calibration="medium", attack="auto_research",
    ))).run()
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path, "mock_leakage_medium", "mock", "mock",
        calibration="medium", attack="auto_research",
    ))).run()

    matrix_cfg = tmp_path / "medium_matrix.yaml"
    matrix_cfg.write_text(
        f"""
mode: matrix
target_experiment: cross_framework_medium_matrix
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
sources:
  - experiment: langgraph_synthetic_leakage_medium
    system_name: langgraph_synthetic
  - experiment: mock_leakage_medium
    system_name: mock
targets:
  - system_name: autogen_synthetic
    adapter_suffix: matrix_medium_autogen
    adapter_config:
      calibration_profile: medium
  - system_name: crewai_synthetic
    adapter_suffix: matrix_medium_crewai
    adapter_config:
      calibration_profile: medium
""",
        encoding="utf-8",
    )
    TransferRunner(matrix_cfg).run()

    summary_path = summarize(output_dir)
    with (summary_path / "internal_clean_transferability_matrix.csv").open(encoding="utf-8") as f:
        clean_rows = list(csv.DictReader(f))

    assert len(clean_rows) > 2
    assert all(r.get("goal") == "leakage" for r in clean_rows)
    assert all(r.get("experiment_group") == "transfer" for r in clean_rows)
    variant_ids = {r.get("source_attack_variant_id") for r in clean_rows}
    assert len(variant_ids) > 1


def test_internal_clean_transfer_excludes_legacy_only(tmp_path):
    output_dir = str(tmp_path / "results")
    legacy_source = _write_leakage_config(
        tmp_path, "legacy_source", "mock", "mock", attack="manual_baseline",
    )
    ExperimentRunner(load_config(legacy_source)).run()

    matrix_cfg = tmp_path / "legacy_matrix.yaml"
    matrix_cfg.write_text(
        f"""
mode: matrix
target_experiment: legacy_transfer_matrix
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
sources:
  - experiment: legacy_source
    system_name: mock
targets:
  - system_name: autogen_synthetic
    adapter_suffix: legacy_target
    adapter_config: {{}}
""",
        encoding="utf-8",
    )
    TransferRunner(matrix_cfg).run()
    summary_path = summarize(output_dir)
    with (summary_path / "internal_clean_transferability_matrix.csv").open(encoding="utf-8") as f:
        clean_rows = list(csv.DictReader(f))
    assert len(clean_rows) == 0


def test_internal_clean_transfer_summary_created(tmp_path):
    output_dir = str(tmp_path / "results")
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path, "langgraph_synthetic_leakage_medium", "langgraph_synthetic",
        "langgraph_synthetic", calibration="medium", attack="manual_baseline",
    ))).run()
    matrix_cfg = tmp_path / "matrix.yaml"
    matrix_cfg.write_text(
        f"""
mode: matrix
target_experiment: cross_framework_medium_matrix
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output_dir}
sources:
  - experiment: langgraph_synthetic_leakage_medium
    system_name: langgraph_synthetic
targets:
  - system_name: autogen_synthetic
    adapter_suffix: matrix_medium_autogen
    adapter_config:
      calibration_profile: medium
""",
        encoding="utf-8",
    )
    TransferRunner(matrix_cfg).run()
    summary_path = summarize(output_dir)
    summary_file = summary_path / "internal_clean_transfer_summary.csv"
    assert summary_file.exists()
    with summary_file.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert "mean_transfer_asr" in rows[0]
    assert "num_variants" in rows[0]


def test_calibrated_degradation_configs_load():
    configs_dir = Path(__file__).resolve().parents[1] / "configs"
    for name in DEGRADATION_CONFIGS:
        path = configs_dir / name
        assert path.exists(), name
        config = load_config(path)
        assert config.goal == "degradation"
        assert config.adapter_config.get("calibration_profile") in ("medium", "hard")


def test_calibrated_degradation_experiment_group(tmp_path):
    output = str(tmp_path / "results")
    cfg_path = tmp_path / "mock_degradation_medium.yaml"
    cfg_path.write_text(
        f"""
experiment_name: mock_degradation_medium
system_name: mock
goal: degradation
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
defense: no_defense
calibration_profile: medium
scoring_weights:
  utility_drop: 1.0
  cost_amplification: 0.3
  latency_increase: 0.2
  tool_call_increase: 0.2
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    metrics = ExperimentRunner(load_config(cfg_path)).run()
    assert metrics["goal"] == "degradation"
    assert metrics["calibration_profile"] == "medium"
    summary_path = summarize(output)
    with (summary_path / "table_degradation_by_system.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    deg_rows = [r for r in rows if r["experiment_name"] == "mock_degradation_medium"]
    assert deg_rows
    assert deg_rows[0]["experiment_group"] == "degradation"


def test_internal_clean_degradation_excludes_legacy(tmp_path):
    output = str(tmp_path / "results")
    legacy_cfg = tmp_path / "legacy_deg.yaml"
    legacy_cfg.write_text(
        f"""
experiment_name: mock_degradation
system_name: mock
goal: degradation
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
defense: no_defense
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config: {{}}
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(legacy_cfg)).run()

    medium_cfg = tmp_path / "medium_deg.yaml"
    medium_cfg.write_text(
        f"""
experiment_name: mock_degradation_medium
system_name: mock
goal: degradation
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
defense: no_defense
calibration_profile: medium
scoring_weights:
  utility_drop: 1.0
  cost_amplification: 0.3
  latency_increase: 0.2
  tool_call_increase: 0.2
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(medium_cfg)).run()

    summary_path = summarize(output)
    with (summary_path / "internal_clean_degradation_results.csv").open(encoding="utf-8") as f:
        clean_rows = list(csv.DictReader(f))
    assert clean_rows
    assert all(r["experiment_name"] != "mock_degradation" for r in clean_rows)
    assert all(r["calibration_profile"] in ("medium", "hard") for r in clean_rows)


def test_internal_clean_degradation_summary_created(tmp_path):
    output = str(tmp_path / "results")
    cfg = tmp_path / "deg.yaml"
    cfg.write_text(
        f"""
experiment_name: mock_degradation_medium
system_name: mock
goal: degradation
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
defense: no_defense
calibration_profile: medium
scoring_weights:
  utility_drop: 1.0
  cost_amplification: 0.3
  latency_increase: 0.2
  tool_call_increase: 0.2
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(cfg)).run()
    summary_path = summarize(output)
    summary_file = summary_path / "internal_clean_degradation_summary.csv"
    assert summary_file.exists()
    with summary_file.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert "mean_utility_drop" in rows[0]
    assert "num_experiments" in rows[0]


def test_paper_tables_includes_transfer_and_degradation_summary_sections(tmp_path):
    output = str(tmp_path / "results")
    ExperimentRunner(load_config(_write_leakage_config(
        tmp_path, "langgraph_synthetic_leakage_medium", "langgraph_synthetic",
        "langgraph_synthetic", calibration="medium", attack="manual_baseline",
    ))).run()
    matrix_cfg = tmp_path / "matrix.yaml"
    matrix_cfg.write_text(
        f"""
mode: matrix
target_experiment: cross_framework_medium_matrix
goal: leakage
num_tasks: 3
defense: no_defense
random_seed: 42
output_dir: {output}
sources:
  - experiment: langgraph_synthetic_leakage_medium
    system_name: langgraph_synthetic
targets:
  - system_name: autogen_synthetic
    adapter_suffix: matrix_medium_autogen
    adapter_config:
      calibration_profile: medium
""",
        encoding="utf-8",
    )
    TransferRunner(matrix_cfg).run()

    deg_cfg = tmp_path / "deg.yaml"
    deg_cfg.write_text(
        f"""
experiment_name: mock_degradation_medium
system_name: mock
goal: degradation
num_iterations: 2
num_tasks: 3
attack_generator: auto_research
defense: no_defense
calibration_profile: medium
scoring_weights:
  utility_drop: 1.0
  cost_amplification: 0.3
  latency_increase: 0.2
  tool_call_increase: 0.2
output_dir: {output}
random_seed: 42
adapter_type: mock
adapter_config:
  calibration_profile: medium
""",
        encoding="utf-8",
    )
    ExperimentRunner(load_config(deg_cfg)).run()

    summary_path = summarize(output)
    md = (summary_path / "paper_tables.md").read_text(encoding="utf-8")
    assert "Transfer Summary (clean)" in md
    assert "Degradation Summary (clean)" in md
