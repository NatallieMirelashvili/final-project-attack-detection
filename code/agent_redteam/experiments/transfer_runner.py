"""Transfer experiment runner with single-source and matrix modes."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from agent_redteam.adapters.adapter_factory import create_adapter
from agent_redteam.defenses.defense_config import get_defense
from agent_redteam.data.synthetic_tasks import generate_synthetic_tasks
from agent_redteam.evaluation.leakage_metrics import compute_all_leakage_metrics
from agent_redteam.evaluation.performance_metrics import compute_all_performance_metrics
from agent_redteam.evaluation.transfer_metrics import (
    cross_architecture_transfer,
    cross_domain_transfer,
    cross_framework_transfer,
    generalization_gap,
    transfer_asr,
)
from agent_redteam.experiments.experiment_metadata import (
    infer_architecture,
    infer_matrix_calibration_profile,
    resolve_calibration_profile,
    resolve_integration_mode,
    SYSTEM_ARCHITECTURE,
)
from agent_redteam.logging_utils.jsonl import append_jsonl, read_jsonl, write_jsonl
from agent_redteam.schemas import AttackVariant, RunResult, Trace


def _dict_to_variant(d: Dict[str, Any]) -> AttackVariant:
    v = d.get("variant", d)
    return AttackVariant(
        id=v["id"],
        goal=v["goal"],
        prompt_template=v["prompt_template"],
        injection_location=v["injection_location"],
        target_channel=v["target_channel"],
        target_agent=v["target_agent"],
        stealth_level=v["stealth_level"],
        metadata=v.get("metadata", {}),
    )


def _dict_to_trace(d: Dict[str, Any]) -> Trace:
    return Trace(
        **{k: d.get(k, [] if k != "final_output" else "") for k in Trace.__dataclass_fields__}
    )


def _dict_to_run(d: Dict[str, Any]) -> RunResult:
    trace_data = d.get("trace", {})
    return RunResult(
        task_id=d["task_id"],
        system_name=d["system_name"],
        attack_variant_id=d.get("attack_variant_id"),
        defense_name=d["defense_name"],
        final_output=d["final_output"],
        task_success=d["task_success"],
        latency_seconds=d["latency_seconds"],
        token_count=d["token_count"],
        estimated_cost=d["estimated_cost"],
        tool_calls=d["tool_calls"],
        retries=d["retries"],
        errors=d.get("errors", []),
        trace=_dict_to_trace(trace_data),
    )


def _run_to_dict(run: RunResult) -> Dict[str, Any]:
    return asdict(run)


def _architecture_for_system(system_name: str) -> str:
    for key, arch in SYSTEM_ARCHITECTURE.items():
        if system_name == key or system_name.startswith(key):
            return arch
    return "unknown"


def _integration_mode_from_metrics(
    metrics: Dict[str, Any],
    system_name: str,
    adapter_config: Dict[str, Any],
) -> str:
    if metrics.get("integration_mode"):
        return str(metrics["integration_mode"])
    return resolve_integration_mode(system_name, system_name, adapter_config)


def _calibration_from_metrics(metrics: Dict[str, Any], experiment_name: str = "") -> str:
    if metrics.get("calibration_profile"):
        return str(metrics["calibration_profile"])
    adapter_config = metrics.get("adapter_config") or {}
    return resolve_calibration_profile(adapter_config, experiment_name)


class TransferRunner:
    def __init__(self, config_path: str | Path) -> None:
        with Path(config_path).open("r", encoding="utf-8") as f:
            self.raw = yaml.safe_load(f)
        self.output_dir = Path(self.raw.get("output_dir", "results"))
        self.mode = self.raw.get("mode", "single")
        if self.raw.get("sources") and self.mode != "matrix":
            self.mode = "matrix"
        self.random_seed = self.raw.get("random_seed", 42)
        self.num_tasks = self.raw.get("num_tasks", 5)
        self.defense = self.raw.get("defense", "no_defense")
        self.goal = self.raw.get("goal", "leakage")

    def _enrich_matrix_row(
        self,
        row: Dict[str, Any],
        transfer_experiment: str,
        source_experiment: str,
        source_metrics: Dict[str, Any],
        target_system: str,
        target_config_name: str,
        target_adapter_config: Dict[str, Any],
    ) -> None:
        source_system = row.get("source_system", source_metrics.get("system_name", ""))
        row["transfer_experiment_name"] = transfer_experiment
        row["source_experiment_name"] = source_experiment
        row["source_config_name"] = source_metrics.get("config_name", source_experiment)
        row["target_config_name"] = target_config_name
        row["source_integration_mode"] = _integration_mode_from_metrics(
            source_metrics, str(source_system), source_metrics.get("adapter_config") or {}
        )
        row["target_integration_mode"] = resolve_integration_mode(
            target_system, target_system, target_adapter_config
        )
        row["source_calibration_profile"] = _calibration_from_metrics(source_metrics, source_experiment)
        row["target_calibration_profile"] = resolve_calibration_profile(
            target_adapter_config, transfer_experiment
        )

    def _collect_warnings(self, target_system: str) -> List[str]:
        warnings: List[str] = []
        if not target_system or target_system in ("unknown", "multiple"):
            warnings.append("target_system_missing")
        return warnings

    def run(self) -> Dict[str, Any]:
        if self.mode == "matrix":
            return self._run_matrix()
        return self._run_single()

    def _run_single(self) -> Dict[str, Any]:
        source_experiment = self.raw["source_experiment"]
        target_experiment = self.raw.get("target_experiment", "transfer_target")
        target_system = self.raw.get("target_system_name", "mock")
        target_suffix = self.raw.get("target_adapter_suffix", "target")
        target_adapter_config = self.raw.get("target_adapter_config", {})

        source_path = self.output_dir / source_experiment
        target_path = self.output_dir / target_experiment
        target_path.mkdir(parents=True, exist_ok=True)

        source_metrics = self._load_metrics(source_path)
        source_system = source_metrics.get("system_name", self._infer_system(source_experiment))
        source_goal = source_metrics.get("goal", self.goal)

        variants = self._load_variants(source_path)
        tasks = generate_synthetic_tasks(self.num_tasks, self.random_seed)
        tasks_map = {t.id: t for t in tasks}
        defense = get_defense(self.defense)

        target_config = {
            "random_seed": self.random_seed + 1,
            "variant_suffix": target_suffix,
            **target_adapter_config,
        }
        target_adapter = create_adapter(
            system_name=target_system,
            adapter_config=target_config,
            random_seed=self.random_seed + 1,
        )

        matrix_rows: List[Dict[str, Any]] = []
        transfer_rows: List[Dict[str, Any]] = []
        all_runs: List[RunResult] = []

        for variant in variants:
            row, runs = self._evaluate_variant_on_target(
                variant=variant,
                source_metrics=source_metrics,
                source_path=source_path,
                source_system=source_system,
                source_goal=source_goal,
                target_system=target_system,
                target_adapter=target_adapter,
                tasks=tasks,
                tasks_map=tasks_map,
                defense=defense,
            )
            self._enrich_matrix_row(
                row,
                transfer_experiment=target_experiment,
                source_experiment=source_experiment,
                source_metrics=source_metrics,
                target_system=target_system,
                target_config_name=target_suffix,
                target_adapter_config=target_adapter_config,
            )
            matrix_rows.append(row)
            transfer_rows.append({
                "variant_id": variant.id,
                "source_metric": row["source_metric"],
                "target_metric": row["target_leakage_asr"] if source_goal == "leakage"
                else row["target_utility_drop"],
                "transfer_asr": row["transfer_asr"],
                "generalization_gap": row["generalization_gap"],
                "goal": source_goal,
            })
            for run in runs:
                all_runs.append(run)
                append_jsonl(target_path / "transfer_runs.jsonl", _run_to_dict(run))

        metrics_summary = self._build_summary(
            source_experiment=source_experiment,
            target_experiment=target_experiment,
            source_system=source_system,
            target_system=target_system,
            target_adapter_config=target_adapter_config,
            target_config_name=target_suffix,
            goal=source_goal,
            matrix_rows=matrix_rows,
            transfer_rows=transfer_rows,
            all_runs=all_runs,
            tasks_map=tasks_map,
        )

        self._write_outputs(target_path, matrix_rows, transfer_rows, metrics_summary)
        target_adapter.teardown()
        return metrics_summary

    def _run_matrix(self) -> Dict[str, Any]:
        target_experiment = self.raw.get(
            "target_experiment", "transfer_cross_framework_matrix"
        )
        target_path = self.output_dir / target_experiment
        target_path.mkdir(parents=True, exist_ok=True)

        sources = self.raw.get("sources", [])
        targets = self.raw.get("targets", [])
        tasks = generate_synthetic_tasks(self.num_tasks, self.random_seed)
        tasks_map = {t.id: t for t in tasks}
        defense = get_defense(self.defense)

        matrix_rows: List[Dict[str, Any]] = []
        transfer_rows: List[Dict[str, Any]] = []
        all_runs: List[RunResult] = []

        for src in sources:
            source_experiment = src["experiment"]
            source_path = self.output_dir / source_experiment
            source_metrics = self._load_metrics(source_path)
            source_system = src.get(
                "system_name",
                source_metrics.get("system_name", self._infer_system(source_experiment)),
            )
            source_goal = source_metrics.get("goal", self.goal)
            variants = self._load_variants(source_path)

            for tgt in targets:
                target_system = tgt["system_name"]
                target_suffix = tgt.get("adapter_suffix", f"from_{source_system}")
                target_adapter_config = tgt.get("adapter_config", {})
                target_config = {
                    "random_seed": self.random_seed + hash(target_system) % 1000,
                    "variant_suffix": target_suffix,
                    **target_adapter_config,
                }
                target_adapter = create_adapter(
                    system_name=target_system,
                    adapter_config=target_config,
                    random_seed=self.random_seed,
                )

                for variant in variants:
                    row, runs = self._evaluate_variant_on_target(
                        variant=variant,
                        source_metrics=source_metrics,
                        source_path=source_path,
                        source_system=source_system,
                        source_goal=source_goal,
                        target_system=target_system,
                        target_adapter=target_adapter,
                        tasks=tasks,
                        tasks_map=tasks_map,
                        defense=defense,
                    )
                    self._enrich_matrix_row(
                        row,
                        transfer_experiment=target_experiment,
                        source_experiment=source_experiment,
                        source_metrics=source_metrics,
                        target_system=target_system,
                        target_config_name=target_suffix,
                        target_adapter_config=target_adapter_config,
                    )
                    matrix_rows.append(row)
                    transfer_rows.append({
                        "variant_id": variant.id,
                        "source_metric": row["source_metric"],
                        "target_metric": row.get("target_leakage_asr", row.get("target_utility_drop", 0)),
                        "transfer_asr": row["transfer_asr"],
                        "generalization_gap": row["generalization_gap"],
                        "goal": source_goal,
                    })
                    for run in runs:
                        all_runs.append(run)
                        append_jsonl(target_path / "transfer_runs.jsonl", _run_to_dict(run))

                target_adapter.teardown()

        metrics_summary = self._build_summary(
            source_experiment="matrix",
            target_experiment=target_experiment,
            source_system="multiple",
            target_system="multiple",
            target_adapter_config={},
            target_config_name=target_experiment,
            goal=self.goal,
            matrix_rows=matrix_rows,
            transfer_rows=transfer_rows,
            all_runs=all_runs,
            tasks_map=tasks_map,
        )

        self._write_outputs(target_path, matrix_rows, transfer_rows, metrics_summary)
        return metrics_summary

    def _evaluate_variant_on_target(
        self,
        variant: AttackVariant,
        source_metrics: Dict[str, Any],
        source_path: Path,
        source_system: str,
        source_goal: str,
        target_system: str,
        target_adapter: Any,
        tasks: List[Any],
        tasks_map: Dict[str, Any],
        defense: Any,
    ) -> tuple[Dict[str, Any], List[RunResult]]:
        variant_runs: List[RunResult] = []
        for task in tasks:
            result = target_adapter.run_attacked(task, variant, defense)
            variant_runs.append(result)

        metric_key = "leakage_asr" if source_goal == "leakage" else "utility_drop"
        if source_goal == "leakage":
            target_metrics = compute_all_leakage_metrics(variant_runs, tasks_map)
        else:
            clean_runs = [target_adapter.run_clean(task) for task in tasks]
            target_metrics = compute_all_performance_metrics(clean_runs, variant_runs)

        source_val = self._source_metric_for_variant(
            source_path, variant.id, source_goal, tasks_map, source_metrics
        )

        if source_goal == "leakage":
            target_leakage_asr = float(target_metrics.get("leakage_asr", 0.0))
            target_utility_drop = 0.0
        else:
            target_leakage_asr = 0.0
            target_utility_drop = float(target_metrics.get("utility_drop", 0.0))

        target_val = float(target_metrics.get(metric_key, 0.0))
        tgt_goal = source_goal

        row = {
            "source_system": source_system,
            "target_system": target_system,
            "source_architecture": _architecture_for_system(source_system),
            "target_architecture": _architecture_for_system(target_system),
            "source_goal": source_goal,
            "target_goal": tgt_goal,
            "source_attack_variant_id": variant.id,
            "source_metric": source_val,
            "target_leakage_asr": target_leakage_asr,
            "target_utility_drop": target_utility_drop,
            "transfer_asr": transfer_asr({metric_key: source_val}, {metric_key: target_val}, metric_key),
            "generalization_gap": generalization_gap(
                {metric_key: source_val}, {metric_key: target_val}, metric_key
            ),
            "source_domain": "mixed",
            "target_domain": "mixed",
        }
        return row, variant_runs

    def _build_summary(
        self,
        source_experiment: str,
        target_experiment: str,
        source_system: str,
        target_system: str,
        goal: str,
        matrix_rows: List[Dict[str, Any]],
        transfer_rows: List[Dict[str, Any]],
        all_runs: List[RunResult],
        tasks_map: Dict[str, Any],
        target_adapter_config: Optional[Dict[str, Any]] = None,
        target_config_name: str = "",
    ) -> Dict[str, Any]:
        aggregate = cross_framework_transfer(transfer_rows)
        arch = cross_architecture_transfer(matrix_rows)
        domain = cross_domain_transfer(matrix_rows)

        adapter_config = target_adapter_config or self.raw.get("target_adapter_config", {})
        target_system_name = self.raw.get("target_system_name", target_system)
        if target_system == "multiple":
            calibration_profile = infer_matrix_calibration_profile(
                target_experiment, self.raw.get("targets", [])
            )
            integration_mode = "synthetic_fallback"
            architecture = infer_architecture("langgraph_synthetic")
        else:
            calibration_profile = resolve_calibration_profile(adapter_config, target_experiment)
            integration_mode = resolve_integration_mode(
                target_system_name, target_system_name, adapter_config
            )
            architecture = infer_architecture(target_system_name)

        warnings = self._collect_warnings(target_system)
        summary: Dict[str, Any] = {
            "experiment_name": target_experiment,
            "config_name": target_experiment,
            "source_experiment": source_experiment,
            "target_experiment": target_experiment,
            "system_name": target_system_name if target_system != "multiple" else "multiple",
            "source_system": source_system,
            "target_system": target_system,
            "architecture": architecture,
            "integration_mode": integration_mode,
            "calibration_profile": calibration_profile,
            "attack_generator": "transfer",
            "defense": self.defense,
            "goal": goal,
            "random_seed": self.random_seed,
            "num_iterations": len(matrix_rows),
            "num_tasks": self.num_tasks,
            "transfer_results": transfer_rows,
            "transfer_matrix": matrix_rows,
            "aggregate": aggregate,
            "cross_architecture": arch,
            "cross_domain": domain,
        }
        if target_config_name:
            summary["target_config_name"] = target_config_name
        if warnings:
            summary["warnings"] = warnings

        if goal == "leakage" and all_runs:
            summary["target_leakage"] = compute_all_leakage_metrics(all_runs, tasks_map)

        return summary

    def _write_outputs(
        self,
        target_path: Path,
        matrix_rows: List[Dict[str, Any]],
        transfer_rows: List[Dict[str, Any]],
        metrics_summary: Dict[str, Any],
    ) -> None:
        with (target_path / "metrics_summary.json").open("w", encoding="utf-8") as f:
            json.dump(metrics_summary, f, indent=2, default=str)

        with (target_path / "transfer_results.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "variant_id",
                    "source_metric",
                    "target_metric",
                    "transfer_asr",
                    "generalization_gap",
                    "goal",
                ],
            )
            writer.writeheader()
            writer.writerows(transfer_rows)

        matrix_fields = [
            "transfer_experiment_name",
            "source_experiment_name",
            "source_config_name",
            "target_config_name",
            "source_system",
            "target_system",
            "source_integration_mode",
            "target_integration_mode",
            "source_calibration_profile",
            "target_calibration_profile",
            "source_goal",
            "target_goal",
            "source_attack_variant_id",
            "source_metric",
            "target_leakage_asr",
            "target_utility_drop",
            "transfer_asr",
            "generalization_gap",
        ]
        with (target_path / "transfer_matrix.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=matrix_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(matrix_rows)

    def _load_metrics(self, source_path: Path) -> Dict[str, Any]:
        path = source_path / "metrics_summary.json"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _source_metric_for_variant(
        self,
        source_path: Path,
        variant_id: str,
        source_goal: str,
        tasks_map: Dict[str, Any],
        fallback_metrics: Dict[str, Any],
    ) -> float:
        """Compute per-variant source metric from source runs.jsonl when available."""
        runs_path = source_path / "runs.jsonl"
        if not runs_path.exists():
            return self._fallback_source_metric(source_goal, fallback_metrics)

        variant_runs = [
            _dict_to_run(d)
            for d in read_jsonl(runs_path)
            if d.get("attack_variant_id") == variant_id
        ]
        if not variant_runs:
            return self._fallback_source_metric(source_goal, fallback_metrics)

        if source_goal == "leakage":
            return float(
                compute_all_leakage_metrics(variant_runs, tasks_map).get("leakage_asr", 0.0)
            )
        clean_runs = [
            _dict_to_run(d)
            for d in read_jsonl(runs_path)
            if not d.get("attack_variant_id")
        ]
        if not clean_runs:
            return self._fallback_source_metric(source_goal, fallback_metrics)
        return float(
            compute_all_performance_metrics(clean_runs, variant_runs).get("utility_drop", 0.0)
        )

    def _fallback_source_metric(self, source_goal: str, metrics: Dict[str, Any]) -> float:
        if source_goal == "leakage":
            return float(metrics.get("leakage", {}).get("leakage_asr", 0.0))
        return float(metrics.get("performance", {}).get("utility_drop", 0.0))

    def _load_variants(self, source_path: Path) -> List[AttackVariant]:
        best_variants_raw = read_jsonl(source_path / "best_variants.jsonl")
        seen: set[str] = set()
        variants: List[AttackVariant] = []
        for record in best_variants_raw:
            variant = _dict_to_variant(record)
            if variant.id in seen:
                continue
            seen.add(variant.id)
            variants.append(variant)
        return variants[:5]

    def _infer_system(self, experiment_name: str) -> str:
        name = experiment_name.lower()
        if "agentdojo" in name:
            return "agentdojo"
        if "langgraph" in name:
            return "langgraph_synthetic"
        if "autogen" in name:
            return "autogen_synthetic"
        if "crewai" in name:
            return "crewai_synthetic"
        if "mock" in name:
            return "mock"
        return "mock"
