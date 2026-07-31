"""Main experiment runner for red-team benchmarks."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from agent_redteam.adapters.adapter_factory import create_adapter_from_config
from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.finalizer_exposure import resolve_finalizer_mode
from agent_redteam.attacks.auto_research_v2 import AutoResearchV2AttackGenerator
from agent_redteam.attacks.generators import AutoResearchAttackGenerator, DegradationFamilyAttackGenerator, get_attack_generator
from agent_redteam.defenses.defense_config import get_defense
from agent_redteam.data.synthetic_tasks import generate_synthetic_tasks
from agent_redteam.evaluation.leakage_metrics import (
    compute_all_external_leakage_metrics,
    compute_all_leakage_metrics,
)
from agent_redteam.evaluation.performance_metrics import compute_all_performance_metrics
from agent_redteam.evaluation.scorer import score_variant
from agent_redteam.experiments.experiment_metadata import build_experiment_metadata
from agent_redteam.goals import is_leakage_goal
from agent_redteam.logging_utils.jsonl import append_jsonl, write_jsonl
from agent_redteam.schemas import AttackVariant, ExperimentConfig, RunResult, Task


def load_config(path: str | Path) -> ExperimentConfig:
    with Path(path).open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    adapter_config = dict(raw.get("adapter_config") or {})
    if raw.get("calibration_profile"):
        adapter_config.setdefault("calibration_profile", raw["calibration_profile"])
    if raw.get("finalizer_exposure_mode"):
        adapter_config.setdefault("finalizer_exposure_mode", raw["finalizer_exposure_mode"])
    adapter_config.setdefault("random_seed", raw.get("random_seed", 42))
    return ExperimentConfig(
        experiment_name=raw["experiment_name"],
        system_name=raw.get("system_name", "mock"),
        goal=raw["goal"],
        num_iterations=raw.get("num_iterations", 5),
        num_tasks=raw.get("num_tasks", 5),
        attack_generator=raw.get("attack_generator", "auto_research"),
        defense=raw.get("defense", "no_defense"),
        scoring_weights=raw.get("scoring_weights", {}),
        output_dir=raw.get("output_dir", "results"),
        random_seed=raw.get("random_seed", 42),
        adapter_type=raw.get("adapter_type", "mock"),
        adapter_config=adapter_config,
        attack_generator_version=raw.get("attack_generator_version", "v1"),
        reward_profile=raw.get("reward_profile", ""),
    )


def _create_adapter(config: ExperimentConfig) -> AgentSystemAdapter:
    return create_adapter_from_config(config)


def _run_to_dict(run: RunResult) -> Dict[str, Any]:
    d = asdict(run)
    return d


def _variant_to_dict(v: AttackVariant) -> Dict[str, Any]:
    return asdict(v)


def _build_degradation_family_diagnostics(
    clean_runs: List[RunResult],
    variant_records: List[Dict[str, Any]],
    all_runs: List[RunResult],
) -> Dict[str, Any]:
    """Per-family degradation metrics for targeted sweeps."""
    by_variant: Dict[str, List[RunResult]] = {}
    for run in all_runs:
        if not run.attack_variant_id:
            continue
        by_variant.setdefault(run.attack_variant_id, []).append(run)

    family_metrics: Dict[str, Dict[str, Any]] = {}
    for record in variant_records:
        variant_dict = record.get("variant") or {}
        variant_id = str(variant_dict.get("id", ""))
        family = str(
            (variant_dict.get("metadata") or {}).get("degradation_family")
            or (variant_dict.get("metadata") or {}).get("attack_family")
            or "unknown"
        )
        attacked = by_variant.get(variant_id, [])
        perf = compute_all_performance_metrics(clean_runs, attacked)
        family_metrics[family] = {
            "variant_id": variant_id,
            "iteration": record.get("iteration"),
            **perf,
        }

    def _best_by(key: str) -> Dict[str, Any]:
        if not family_metrics:
            return {"family": None, "value": 0.0}
        best_family = max(family_metrics, key=lambda f: float(family_metrics[f].get(key, 0.0)))
        return {"family": best_family, "value": float(family_metrics[best_family].get(key, 0.0))}

    return {
        "by_family": family_metrics,
        "strongest_by_utility_drop": _best_by("utility_drop"),
        "strongest_by_operational_degradation_score": _best_by(
            "operational_degradation_score"
        ),
    }


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig, *, fresh: bool = False) -> None:
        self.config = config
        self.output_path = Path(config.output_dir) / config.experiment_name
        if fresh and self.output_path.exists():
            shutil.rmtree(self.output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        config = self.config
        adapter = _create_adapter(config)
        defense = get_defense(config.defense)
        tasks = generate_synthetic_tasks(config.num_tasks, config.random_seed)
        tasks_map = {t.id: t for t in tasks}

        generator = get_attack_generator(
            config.attack_generator,
            config.goal,
            config.random_seed,
            version=config.attack_generator_version,
            output_path=self.output_path,
            system_name=config.system_name,
        )

        clean_runs: List[RunResult] = []
        all_runs: List[RunResult] = []
        variant_records: List[Dict[str, Any]] = []
        best_variants: List[Tuple[AttackVariant, float]] = []
        trace_samples: List[Dict[str, Any]] = []

        for task in tasks:
            result = adapter.run_clean(task)
            clean_runs.append(result)
            all_runs.append(result)
            append_jsonl(self.output_path / "runs.jsonl", _run_to_dict(result))

        for iteration in range(config.num_iterations):
            variant = generator.generate(iteration)
            attacked_runs: List[RunResult] = []

            for task in tasks:
                result = adapter.run_attacked(task, variant, defense)
                attacked_runs.append(result)
                all_runs.append(result)
                append_jsonl(self.output_path / "runs.jsonl", _run_to_dict(result))

            score = score_variant(
                config.goal,
                attacked_runs,
                clean_runs,
                tasks_map,
                config.scoring_weights or None,
                variant=variant,
                reward_profile=config.reward_profile,
            )
            record_kwargs: Dict[str, Any] = {}
            if config.goal == "external_leakage":
                from agent_redteam.evaluation.leakage_metrics import final_output_leakage_rate

                record_kwargs["final_output_leakage_rate"] = final_output_leakage_rate(
                    attacked_runs, tasks_map
                )
            generator.record_score(variant, score, **record_kwargs)

            variant_record = {
                "iteration": iteration,
                "variant": _variant_to_dict(variant),
                "score": score,
            }
            variant_records.append(variant_record)
            append_jsonl(self.output_path / "variants.jsonl", variant_record)

            best_variants.append((variant, score))
            best_variants.sort(key=lambda x: x[1], reverse=True)
            best_variants = best_variants[:5]

            if iteration == 0 or score >= best_variants[0][1]:
                for run in attacked_runs[:2]:
                    trace_samples.append(_run_to_dict(run))

        write_jsonl(self.output_path / "trace_samples.jsonl", trace_samples)

        best_records = [
            {"variant": _variant_to_dict(v), "score": s} for v, s in best_variants
        ]
        write_jsonl(self.output_path / "best_variants.jsonl", best_records)

        if isinstance(generator, AutoResearchAttackGenerator):
            for accepted in generator.get_accepted_variants():
                append_jsonl(
                    self.output_path / "best_variants.jsonl",
                    {"variant": _variant_to_dict(accepted), "accepted": True},
                )
        if isinstance(generator, AutoResearchV2AttackGenerator):
            for accepted in generator.get_accepted_variants():
                append_jsonl(
                    self.output_path / "best_variants.jsonl",
                    {"variant": _variant_to_dict(accepted), "accepted": True},
                )
            generator.write_diagnostics()

        attacked_all = [r for r in all_runs if r.attack_variant_id]
        metrics: Dict[str, Any] = build_experiment_metadata(config)
        metrics["performance"] = compute_all_performance_metrics(clean_runs, attacked_all)
        if config.goal == "degradation":
            metrics["degradation_diagnostics"] = _build_degradation_family_diagnostics(
                clean_runs, variant_records, all_runs
            )
            if isinstance(generator, DegradationFamilyAttackGenerator):
                metrics["degradation_diagnostics"]["family_score_summary"] = (
                    generator.family_score_summary()
                )
        if config.goal == "external_leakage":
            metrics["external_leakage"] = compute_all_external_leakage_metrics(
                attacked_all, tasks_map
            )
            metrics["leakage"] = metrics["external_leakage"]
        elif is_leakage_goal(config.goal):
            metrics["leakage"] = compute_all_leakage_metrics(attacked_all, tasks_map)
        metrics["best_variant_scores"] = [s for _, s in best_variants]

        with (self.output_path / "metrics_summary.json").open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)

        self._write_results_csv(config.goal, metrics, best_variants)

        adapter.teardown()
        return metrics

    def _write_results_csv(
        self,
        goal: str,
        metrics: Dict[str, Any],
        best_variants: List[Tuple[AttackVariant, float]],
    ) -> None:
        if goal == "external_leakage":
            filename = "external_leakage_results.csv"
            rows = []
            ext = metrics.get("external_leakage", metrics.get("leakage", {}))
            for key in [
                "external_leakage_asr",
                "final_output_leakage_rate",
                "internal_leakage_rate",
                "total_exposure_rate",
                "output_only_miss_rate",
                "leakage_asr",
            ]:
                rows.append({"metric": key, "value": ext.get(key, 0.0)})
            for ch, val in ext.get("channel_breakdown", {}).items():
                rows.append({"metric": f"channel_{ch}", "value": val})
        elif is_leakage_goal(goal):
            filename = "leakage_results.csv"
            rows = []
            leakage = metrics.get("leakage", {})
            for key in [
                "leakage_asr",
                "exact_canary_leakage_rate",
                "partial_canary_leakage_rate",
                "final_output_leakage_rate",
                "internal_leakage_rate",
                "total_exposure_rate",
                "output_only_miss_rate",
            ]:
                rows.append({"metric": key, "value": leakage.get(key, 0.0)})
            for ch, val in leakage.get("channel_breakdown", {}).items():
                rows.append({"metric": f"channel_{ch}", "value": val})
        else:
            filename = "degradation_results.csv"
            perf = metrics.get("performance", {})
            rows = [
                {"metric": k, "value": perf.get(k, 0.0)}
                for k in [
                    "clean_task_success_rate",
                    "attacked_task_success_rate",
                    "utility_drop",
                    "cost_amplification",
                    "tool_call_increase",
                    "retry_rate",
                    "loop_or_failure_rate",
                    "final_output_empty_rate",
                    "operational_degradation_score",
                ]
            ]
            diag = metrics.get("degradation_diagnostics", {})
            for key in ("strongest_by_utility_drop", "strongest_by_operational_degradation_score"):
                entry = diag.get(key) or {}
                if entry.get("family"):
                    rows.append(
                        {
                            "metric": f"{key}_family",
                            "value": entry.get("family", ""),
                        }
                    )
                    rows.append(
                        {
                            "metric": f"{key}_value",
                            "value": entry.get("value", 0.0),
                        }
                    )

        for v, s in best_variants:
            rows.append({"metric": f"best_variant_{v.id}", "value": s})

        with (self.output_path / filename).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metric", "value"])
            writer.writeheader()
            writer.writerows(rows)
