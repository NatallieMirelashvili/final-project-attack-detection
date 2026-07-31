"""Tests for sequential experiment suite runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_redteam.experiments.runner import load_config
from agent_redteam.experiments.suite_runner import SuiteRunner, load_suite
from agent_redteam.run_suite import main as run_suite_main


def _write_config(path: Path, *, experiment_name: str, output_dir: Path) -> None:
    path.write_text(
        f"""
experiment_name: {experiment_name}
system_name: mock
goal: degradation
num_iterations: 1
num_tasks: 1
attack_generator: auto_research
attack_generator_version: v2
defense: no_defense
output_dir: {output_dir.as_posix()}
random_seed: 42
adapter_type: mock
adapter_config:
  integration_mode: controlled
""",
        encoding="utf-8",
    )


def _write_suite(path: Path, configs: list[str], **overrides) -> None:
    lines = [
        "suite_name: test_suite",
        "description: test suite",
        "fresh: false",
        "continue_on_error: true",
        "summarize_at_end: false",
        "configs:",
    ]
    for cfg in configs:
        lines.append(f"  - {cfg}")
    for key, value in overrides.items():
        if key == "configs":
            continue
        lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_suite_reads_yaml(tmp_path: Path):
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, ["cfg_a.yaml", "cfg_b.yaml"], suite_name="overnight")
    suite = load_suite(suite_path)
    assert suite.suite_name == "overnight"
    assert suite.configs == ["cfg_a.yaml", "cfg_b.yaml"]
    assert suite.continue_on_error is True


def test_dry_run_lists_configs_without_running(tmp_path: Path, capsys):
    cfg = tmp_path / "ok.yaml"
    _write_config(cfg, experiment_name="ok_exp", output_dir=tmp_path / "results")
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, [str(cfg)])

    runner = SuiteRunner(
        load_suite(suite_path),
        suite_file=suite_path,
        dry_run=True,
        results_root=tmp_path / "results",
    )
    result = runner.run()
    assert result.dry_run is True
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out
    assert "ok.yaml" in captured.out


def test_dry_run_missing_config_raises(tmp_path: Path):
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, ["missing.yaml"])
    runner = SuiteRunner(
        load_suite(suite_path),
        suite_file=suite_path,
        dry_run=True,
        results_root=tmp_path / "results",
    )
    with pytest.raises(FileNotFoundError, match="missing config"):
        runner.run()


def test_suite_writes_status_files(tmp_path: Path):
    results = tmp_path / "results"
    cfg = tmp_path / "good.yaml"
    _write_config(cfg, experiment_name="good_exp", output_dir=results)
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, [str(cfg)])

    def fake_run(config_path: Path, *, fresh: bool):
        config = load_config(config_path)
        out_dir = Path(config.output_dir) / config.experiment_name
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "runs.jsonl").write_text("{}\n", encoding="utf-8")
        (out_dir / "variants.jsonl").write_text("{}\n", encoding="utf-8")
        (out_dir / "metrics_summary.json").write_text("{}", encoding="utf-8")
        return {
            "experiment_name": config.experiment_name,
            "result_dir": str(out_dir),
            "metrics": {},
        }

    runner = SuiteRunner(
        load_suite(suite_path),
        suite_file=suite_path,
        results_root=results,
        run_experiment=fake_run,
    )
    result = runner.run()
    suite_dir = Path(result.suite_dir)
    assert (suite_dir / "suite_status.json").is_file()
    assert (suite_dir / "suite_status.csv").is_file()
    assert (suite_dir / "completed_configs.txt").read_text(encoding="utf-8").strip()
    assert result.records[0].success is True


def test_continue_on_error_records_failure_and_continues(tmp_path: Path):
    results = tmp_path / "results"
    bad = tmp_path / "bad.yaml"
    good = tmp_path / "good.yaml"
    _write_config(bad, experiment_name="bad_exp", output_dir=results)
    _write_config(good, experiment_name="good_exp", output_dir=results)
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, [str(bad), str(good)], continue_on_error="true")

    calls: list[str] = []

    def fake_run(config_path: Path, *, fresh: bool):
        calls.append(str(config_path))
        if config_path.name == "bad.yaml":
            raise RuntimeError("boom")
        config = load_config(config_path)
        out_dir = Path(config.output_dir) / config.experiment_name
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "runs.jsonl").write_text("{}\n", encoding="utf-8")
        (out_dir / "variants.jsonl").write_text("{}\n", encoding="utf-8")
        (out_dir / "metrics_summary.json").write_text("{}", encoding="utf-8")
        return {
            "experiment_name": config.experiment_name,
            "result_dir": str(out_dir),
            "metrics": {},
        }

    runner = SuiteRunner(
        load_suite(suite_path),
        suite_file=suite_path,
        continue_on_error=True,
        results_root=results,
        run_experiment=fake_run,
    )
    result = runner.run()
    assert len(calls) == 2
    assert result.records[0].success is False
    assert "boom" in result.records[0].error
    assert result.records[1].success is True
    failed = (Path(result.suite_dir) / "failed_configs.txt").read_text(encoding="utf-8")
    completed = (Path(result.suite_dir) / "completed_configs.txt").read_text(encoding="utf-8")
    assert str(bad) in failed
    assert str(good) in completed


def test_stop_on_error_stops_after_first_failure(tmp_path: Path):
    results = tmp_path / "results"
    bad = tmp_path / "bad.yaml"
    good = tmp_path / "good.yaml"
    _write_config(bad, experiment_name="bad_exp", output_dir=results)
    _write_config(good, experiment_name="good_exp", output_dir=results)
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, [str(bad), str(good)], continue_on_error="false")

    calls: list[str] = []

    def fake_run(config_path: Path, *, fresh: bool):
        calls.append(str(config_path))
        raise RuntimeError("boom")

    runner = SuiteRunner(
        load_suite(suite_path),
        suite_file=suite_path,
        continue_on_error=False,
        results_root=results,
        run_experiment=fake_run,
    )
    result = runner.run()
    assert len(calls) == 1
    assert len(result.records) == 1


def test_lockfile_prevents_duplicate_suite_runs(tmp_path: Path):
    results = tmp_path / "results"
    cfg = tmp_path / "good.yaml"
    _write_config(cfg, experiment_name="good_exp", output_dir=results)
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, [str(cfg)])

    lock_path = results / "suites" / "test_suite.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"pid": 99999}', encoding="utf-8")

    runner = SuiteRunner(
        load_suite(suite_path),
        suite_file=suite_path,
        results_root=results,
        run_experiment=lambda *_a, **_k: {"experiment_name": "x", "result_dir": ""},
    )
    with pytest.raises(RuntimeError, match="Suite lock already exists"):
        runner.run()


def test_cli_dry_run(tmp_path: Path, capsys):
    cfg = tmp_path / "ok.yaml"
    _write_config(cfg, experiment_name="ok_exp", output_dir=tmp_path / "results")
    suite_path = tmp_path / "suite.yaml"
    _write_suite(suite_path, [str(cfg)])

    code = run_suite_main(["--suite", str(suite_path), "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Dry run OK" in out


def test_core_suite_file_references_existing_configs():
    suite_path = Path("configs/suites/live_ollama_medium_core.yaml")
    suite = load_suite(suite_path)
    missing = []
    for cfg in suite.configs:
        resolved = (suite_path.parent / cfg).resolve()
        if not resolved.exists():
            missing.append(str(cfg))
    assert not missing, f"Missing configs: {missing}"
    assert len(suite.configs) == 4
