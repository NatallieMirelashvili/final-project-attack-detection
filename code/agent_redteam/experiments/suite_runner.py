"""Sequential experiment suite runner for overnight medium-scale runs."""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from agent_redteam.experiments.runner import ExperimentRunner, load_config


@dataclass
class SuiteConfig:
    suite_name: str
    description: str
    configs: List[str]
    fresh: bool = False
    continue_on_error: bool = True
    summarize_at_end: bool = True
    output_log_path: str = ""


@dataclass
class SuiteRunRecord:
    config_path: str
    experiment_name: str
    result_dir: str
    exit_code: int
    elapsed_seconds: float
    runs_jsonl: bool
    variants_jsonl: bool
    metrics_summary: bool
    success: bool
    error: str = ""
    started_at: str = ""
    finished_at: str = ""


@dataclass
class SuiteRunResult:
    suite_name: str
    suite_dir: str
    records: List[SuiteRunRecord] = field(default_factory=list)
    summarize_completed: bool = False
    summarize_error: str = ""
    dry_run: bool = False


def load_suite(path: str | Path) -> SuiteConfig:
    suite_path = Path(path)
    if not suite_path.exists():
        raise FileNotFoundError(f"Suite file not found: {suite_path}")
    with suite_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    configs = [str(c) for c in raw.get("configs") or []]
    if not configs:
        raise ValueError(f"Suite '{suite_path}' has no configs listed")
    suite_name = str(raw.get("suite_name") or suite_path.stem)
    return SuiteConfig(
        suite_name=suite_name,
        description=str(raw.get("description") or ""),
        configs=configs,
        fresh=bool(raw.get("fresh", False)),
        continue_on_error=bool(raw.get("continue_on_error", True)),
        summarize_at_end=bool(raw.get("summarize_at_end", True)),
        output_log_path=str(raw.get("output_log_path") or ""),
    )


def _default_lock_path(suite_name: str, results_root: Path) -> Path:
    return results_root / "suites" / f"{suite_name}.lock"


def _resolve_config_path(config_ref: str, suite_file: Path) -> Path:
    path = Path(config_ref)
    if not path.is_absolute():
        path = (suite_file.parent / path).resolve()
        if not path.exists():
            path = (Path.cwd() / config_ref).resolve()
    return path


def _validate_artifacts(result_dir: Path) -> Dict[str, bool]:
    return {
        "runs_jsonl": (result_dir / "runs.jsonl").is_file(),
        "variants_jsonl": (result_dir / "variants.jsonl").is_file(),
        "metrics_summary": (result_dir / "metrics_summary.json").is_file(),
    }


def _write_status_files(suite_dir: Path, records: List[SuiteRunRecord]) -> None:
    status_json = suite_dir / "suite_status.json"
    with status_json.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2)

    csv_path = suite_dir / "suite_status.csv"
    fieldnames = list(asdict(records[0]).keys()) if records else [
        "config_path",
        "experiment_name",
        "result_dir",
        "exit_code",
        "elapsed_seconds",
        "runs_jsonl",
        "variants_jsonl",
        "metrics_summary",
        "success",
        "error",
        "started_at",
        "finished_at",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))

    completed = [r.config_path for r in records if r.success]
    failed = [r.config_path for r in records if not r.success]
    (suite_dir / "completed_configs.txt").write_text("\n".join(completed) + ("\n" if completed else ""), encoding="utf-8")
    (suite_dir / "failed_configs.txt").write_text("\n".join(failed) + ("\n" if failed else ""), encoding="utf-8")


def _acquire_lock(lock_path: Path, *, force: bool) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists() and not force:
        detail = lock_path.read_text(encoding="utf-8").strip()
        raise RuntimeError(
            f"Suite lock already exists at {lock_path}. "
            f"Another suite may be running. Details: {detail or '(empty)'}"
        )
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    lock_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _release_lock(lock_path: Path) -> None:
    if lock_path.exists():
        lock_path.unlink()


class SuiteRunner:
    """Run a list of experiment configs sequentially with suite-level logging."""

    def __init__(
        self,
        suite: SuiteConfig,
        *,
        suite_file: Path,
        fresh: bool = False,
        continue_on_error: Optional[bool] = None,
        dry_run: bool = False,
        force: bool = False,
        results_root: Path | None = None,
        run_experiment: Optional[Callable[..., Dict[str, Any]]] = None,
        summarize_fn: Optional[Callable[[Path], Path]] = None,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.suite = suite
        self.suite_file = suite_file.resolve()
        self.fresh = fresh or suite.fresh
        self.continue_on_error = (
            suite.continue_on_error if continue_on_error is None else continue_on_error
        )
        self.dry_run = dry_run
        self.force = force
        self.results_root = results_root or Path("results")
        self._run_experiment = run_experiment or self._default_run_experiment
        self._summarize_fn = summarize_fn or self._default_summarize
        self._log = log_fn or (lambda msg: None)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.suite_dir = self.results_root / "suites" / suite.suite_name / timestamp
        self.lock_path = _default_lock_path(suite.suite_name, self.results_root)
        log_ref = suite.output_log_path.strip()
        self.log_path = Path(log_ref) if log_ref else self.suite_dir / "suite.log"

    def _default_run_experiment(self, config_path: Path, *, fresh: bool) -> Dict[str, Any]:
        config = load_config(config_path)
        runner = ExperimentRunner(config, fresh=fresh)
        metrics = runner.run()
        return {
            "metrics": metrics,
            "experiment_name": config.experiment_name,
            "result_dir": str(runner.output_path),
        }

    @staticmethod
    def _default_summarize(results_root: Path) -> Path:
        from agent_redteam.summarize_results import summarize

        return summarize(results_root)

    def _log_line(self, msg: str, log_handle) -> None:
        line = msg.rstrip()
        print(line)
        log_handle.write(line + "\n")
        log_handle.flush()
        self._log(line)

    def run(self) -> SuiteRunResult:
        result = SuiteRunResult(suite_name=self.suite.suite_name, suite_dir=str(self.suite_dir))

        if self.dry_run:
            self.suite_dir.mkdir(parents=True, exist_ok=True)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("w", encoding="utf-8") as log_handle:
                self._log_line(f"DRY RUN: suite '{self.suite.suite_name}'", log_handle)
                if self.suite.description:
                    self._log_line(self.suite.description, log_handle)
                for config_ref in self.suite.configs:
                    config_path = _resolve_config_path(config_ref, self.suite_file)
                    exists = "OK" if config_path.exists() else "MISSING"
                    self._log_line(f"  [{exists}] {config_ref} -> {config_path}", log_handle)
            result.dry_run = True
            missing = [
                c
                for c in self.suite.configs
                if not _resolve_config_path(c, self.suite_file).exists()
            ]
            if missing:
                raise FileNotFoundError(f"Dry run found missing config(s): {', '.join(missing)}")
            return result

        _acquire_lock(self.lock_path, force=self.force)
        self.suite_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        records: List[SuiteRunRecord] = []
        try:
            with self.log_path.open("w", encoding="utf-8") as log_handle:
                self._log_line(f"Starting suite '{self.suite.suite_name}'", log_handle)
                if self.suite.description:
                    self._log_line(self.suite.description, log_handle)
                self._log_line(f"Suite directory: {self.suite_dir}", log_handle)
                self._log_line(f"Fresh mode: {self.fresh}", log_handle)
                self._log_line(f"Continue on error: {self.continue_on_error}", log_handle)

                for config_ref in self.suite.configs:
                    config_path = _resolve_config_path(config_ref, self.suite_file)
                    started_at = datetime.now(timezone.utc).isoformat()
                    self._log_line(f"\n=== Config: {config_ref} ===", log_handle)
                    self._log_line(f"Resolved path: {config_path}", log_handle)

                    if not config_path.exists():
                        record = SuiteRunRecord(
                            config_path=config_ref,
                            experiment_name="",
                            result_dir="",
                            exit_code=1,
                            elapsed_seconds=0.0,
                            runs_jsonl=False,
                            variants_jsonl=False,
                            metrics_summary=False,
                            success=False,
                            error=f"Config file not found: {config_path}",
                            started_at=started_at,
                            finished_at=datetime.now(timezone.utc).isoformat(),
                        )
                        records.append(record)
                        _write_status_files(self.suite_dir, records)
                        self._log_line(record.error, log_handle)
                        if not self.continue_on_error:
                            break
                        continue

                    start = time.perf_counter()
                    exit_code = 0
                    error_text = ""
                    experiment_name = ""
                    result_dir = ""
                    try:
                        if self.fresh:
                            preview = load_config(config_path)
                            preview_dir = Path(preview.output_dir) / preview.experiment_name
                            if preview_dir.exists():
                                shutil.rmtree(preview_dir)
                                self._log_line(f"Cleared result directory: {preview_dir}", log_handle)

                        run_info = self._run_experiment(config_path, fresh=self.fresh)
                        experiment_name = str(run_info.get("experiment_name", ""))
                        result_dir = str(run_info.get("result_dir", ""))
                    except Exception as exc:
                        exit_code = 1
                        error_text = "".join(
                            traceback.format_exception(type(exc), exc, exc.__traceback__)
                        )
                        self._log_line(error_text, log_handle)

                    elapsed = time.perf_counter() - start
                    artifact_flags = {"runs_jsonl": False, "variants_jsonl": False, "metrics_summary": False}
                    if result_dir:
                        artifact_flags = _validate_artifacts(Path(result_dir))

                    success = (
                        exit_code == 0
                        and artifact_flags["runs_jsonl"]
                        and artifact_flags["variants_jsonl"]
                        and artifact_flags["metrics_summary"]
                    )
                    record = SuiteRunRecord(
                        config_path=config_ref,
                        experiment_name=experiment_name,
                        result_dir=result_dir,
                        exit_code=exit_code,
                        elapsed_seconds=elapsed,
                        runs_jsonl=artifact_flags["runs_jsonl"],
                        variants_jsonl=artifact_flags["variants_jsonl"],
                        metrics_summary=artifact_flags["metrics_summary"],
                        success=success,
                        error=error_text.strip(),
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc).isoformat(),
                    )
                    records.append(record)
                    _write_status_files(self.suite_dir, records)

                    self._log_line(
                        f"Finished {config_ref}: exit={exit_code}, elapsed={elapsed:.1f}s, success={success}",
                        log_handle,
                    )
                    if result_dir:
                        self._log_line(f"Result directory: {result_dir}", log_handle)

                    if not success and not self.continue_on_error:
                        self._log_line("Stopping suite due to failure (--stop-on-error).", log_handle)
                        break

                if self.suite.summarize_at_end and records and any(r.success for r in records):
                    self._log_line("\nRunning summarize_results...", log_handle)
                    try:
                        summary_path = self._summarize_fn(self.results_root)
                        result.summarize_completed = True
                        self._log_line(f"Summary written to {summary_path}", log_handle)
                    except Exception as exc:
                        result.summarize_error = "".join(
                            traceback.format_exception(type(exc), exc, exc.__traceback__)
                        )
                        self._log_line(result.summarize_error, log_handle)

                self._log_line("\nSuite complete.", log_handle)
        finally:
            _release_lock(self.lock_path)

        result.records = records
        return result
