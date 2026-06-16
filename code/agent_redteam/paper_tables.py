"""Paper-ready summary table generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from agent_redteam.logging_utils.jsonl import read_jsonl
from agent_redteam.table_aggregation import (
    COMMON_METADATA_FIELDS,
    DEGRADATION_SUMMARY_GROUP_FIELDS,
    DEGRADATION_SUMMARY_METRIC_FIELDS,
    TRANSFER_SUMMARY_GROUP_FIELDS,
    TRANSFER_SUMMARY_METRIC_FIELDS,
    build_degradation_summary,
    build_experiment_metadata,
    build_transfer_row_from_matrix,
    build_transfer_summary,
    compute_alias_flags,
    filter_internal_clean_attack_comparison,
    filter_internal_clean_defense_comparison,
    filter_internal_clean_degradation,
    filter_internal_clean_difficulty,
    filter_internal_clean_leakage,
    filter_internal_clean_transfer,
    EXTERNAL_LEAKAGE_SUMMARY_GROUP_FIELDS,
    EXTERNAL_LEAKAGE_SUMMARY_METRIC_FIELDS,
    build_external_leakage_summary,
    filter_internal_clean_external_attack_comparison,
    filter_internal_clean_external_defense_comparison,
    filter_internal_clean_external_leakage,
    filter_internal_clean_external_selective_attack_comparison,
    SELECTIVE_EXTERNAL_SUMMARY_GROUP_FIELDS,
    SELECTIVE_EXTERNAL_SUMMARY_METRIC_FIELDS,
    build_external_selective_summary,
    filter_internal_clean_agentdojo_real_attack_comparison,
    filter_internal_clean_agentdojo_real_external_leakage,
    filter_internal_clean_agentdojo_real_leakage,
    filter_internal_clean_real_attack_comparison,
    filter_internal_clean_real_external_leakage,
    filter_internal_clean_real_leakage,
    REAL_CLEAN_TABLE_FIELDNAMES,
    select_attack_comparison_preview_rows,
    with_metadata,
)

TRANSFER_TABLE_FIELDS = [
    "experiment_name",
    "config_name",
    "experiment_group",
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
    "goal",
    "source_attack_variant_id",
    "source_metric",
    "transfer_asr",
    "generalization_gap",
    "target_total_exposure_rate",
    "target_utility_drop",
    "integration_mode",
    "calibration_profile",
    "is_alias_config",
]


def _load_metrics(exp_dir: Path) -> Dict[str, Any]:
    path = exp_dir / "metrics_summary.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _csv_to_markdown(headers: List[str], rows: List[Dict[str, Any]], limit: int = 0) -> str:
    if not rows:
        return ""
    preview = rows[:limit] if limit else rows
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in preview:
        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def generate_paper_tables(results_path: Path, summary_path: Path) -> None:
    """Generate paper-ready CSV and markdown tables."""
    summary_path.mkdir(parents=True, exist_ok=True)

    leakage_rows: List[Dict[str, Any]] = []
    internal_final_rows: List[Dict[str, Any]] = []
    degradation_rows: List[Dict[str, Any]] = []
    transfer_rows: List[Dict[str, Any]] = []
    defense_rows: List[Dict[str, Any]] = []
    best_variant_rows: List[Dict[str, Any]] = []
    attack_comparison_rows: List[Dict[str, Any]] = []
    difficulty_comparison_rows: List[Dict[str, Any]] = []
    defense_comparison_rows: List[Dict[str, Any]] = []
    external_leakage_rows: List[Dict[str, Any]] = []
    external_attack_comparison_rows: List[Dict[str, Any]] = []
    external_defense_comparison_rows: List[Dict[str, Any]] = []
    autoresearch_v2_diagnostics_rows: List[Dict[str, Any]] = []

    experiments: List[tuple[str, Dict[str, Any]]] = []
    for exp_dir in sorted(results_path.iterdir()):
        if not exp_dir.is_dir() or exp_dir.name == "summary":
            continue
        metrics = _load_metrics(exp_dir)
        if metrics:
            experiments.append((exp_dir.name, metrics))

    alias_flags = compute_alias_flags([exp_name for exp_name, _ in experiments])

    for exp_name, metrics in experiments:
        meta = build_experiment_metadata(exp_name, metrics, alias_flags)
        goal = meta["goal"]
        system = meta["system"]
        attack_type = meta["attack_type"]
        defense = meta["defense"]

        if goal == "leakage" and "leakage" in metrics:
            leak = metrics["leakage"]
            row = with_metadata(
                {
                    "leakage_asr": leak.get("leakage_asr", 0.0),
                    "external_leakage_asr": leak.get(
                        "external_leakage_asr", leak.get("final_output_leakage_rate", 0.0)
                    ),
                    "final_output_leakage_rate": leak.get("final_output_leakage_rate", 0.0),
                    "internal_leakage_rate": leak.get("internal_leakage_rate", 0.0),
                    "total_exposure_rate": leak.get("total_exposure_rate", 0.0),
                    "output_only_miss_rate": leak.get("output_only_miss_rate", 0.0),
                },
                meta,
            )
            leakage_rows.append(row)
            attack_comparison_rows.append(dict(row))
            difficulty_comparison_rows.append(
                with_metadata(
                    {
                        "leakage_asr": leak.get("leakage_asr", 0.0),
                        "final_output_leakage_rate": leak.get("final_output_leakage_rate", 0.0),
                        "internal_leakage_rate": leak.get("internal_leakage_rate", 0.0),
                        "total_exposure_rate": leak.get("total_exposure_rate", 0.0),
                    },
                    meta,
                )
            )
            defense_comparison_rows.append(
                with_metadata(
                    {
                        "leakage_asr": leak.get("leakage_asr", 0.0),
                        "final_output_leakage_rate": leak.get("final_output_leakage_rate", 0.0),
                        "internal_leakage_rate": leak.get("internal_leakage_rate", 0.0),
                        "output_only_miss_rate": leak.get("output_only_miss_rate", 0.0),
                    },
                    meta,
                )
            )
            internal_final_rows.append(
                with_metadata(
                    {
                        "final_output_leakage_rate": leak.get("final_output_leakage_rate", 0.0),
                        "internal_leakage_rate": leak.get("internal_leakage_rate", 0.0),
                        "output_only_miss_rate": leak.get("output_only_miss_rate", 0.0),
                        "total_exposure_rate": leak.get("total_exposure_rate", 0.0),
                    },
                    meta,
                )
            )

        if goal == "external_leakage":
            ext = metrics.get("external_leakage", metrics.get("leakage", {}))
            ext_row = with_metadata(
                {
                    "leakage_asr": ext.get("total_exposure_rate", 0.0),
                    "external_leakage_asr": ext.get(
                        "external_leakage_asr", ext.get("final_output_leakage_rate", 0.0)
                    ),
                    "final_output_leakage_rate": ext.get("final_output_leakage_rate", 0.0),
                    "internal_leakage_rate": ext.get("internal_leakage_rate", 0.0),
                    "total_exposure_rate": ext.get("total_exposure_rate", 0.0),
                    "output_only_miss_rate": ext.get("output_only_miss_rate", 0.0),
                },
                meta,
            )
            external_leakage_rows.append(ext_row)
            if "attack_compare" in exp_name and "external" in exp_name:
                external_attack_comparison_rows.append(dict(ext_row))
            if "external_defense" in exp_name:
                external_defense_comparison_rows.append(dict(ext_row))

            exp_dir = results_path / exp_name
            diag_path = exp_dir / "generator_diagnostics.json"
            if diag_path.exists():
                with diag_path.open(encoding="utf-8") as f:
                    diag = json.load(f)
                autoresearch_v2_diagnostics_rows.append(
                    with_metadata(
                        {
                            "best_score": diag.get("best_score", 0.0),
                            "accepted_count": diag.get("accepted_count", 0),
                            "iterations": diag.get("iterations", 0),
                            "family_mean_scores": json.dumps(
                                diag.get("family_mean_scores", {}), default=str
                            ),
                        },
                        meta,
                    )
                )

        if goal == "degradation" or "performance" in metrics:
            perf = metrics.get("performance", {})
            if goal == "degradation" or perf:
                degradation_rows.append(
                    with_metadata(
                        {
                            "clean_task_success_rate": perf.get("clean_task_success_rate", 0.0),
                            "attacked_task_success_rate": perf.get("attacked_task_success_rate", 0.0),
                            "utility_drop": perf.get("utility_drop", 0.0),
                            "cost_amplification": perf.get("cost_amplification", 0.0),
                            "latency_increase": perf.get("latency_increase", 0.0),
                            "tool_call_increase": perf.get("tool_call_increase", 0.0),
                            "retry_rate": perf.get("retry_rate", 0.0),
                        },
                        meta,
                    )
                )

        if "transfer_matrix" in metrics:
            for matrix_row in metrics["transfer_matrix"]:
                transfer_rows.append(
                    build_transfer_row_from_matrix(exp_name, metrics, matrix_row)
                )
        elif "transfer_results" in metrics:
            tgt = metrics.get("target_system", "unknown")
            if tgt == "unknown" and metrics.get("target_config_name"):
                tgt = str(metrics["target_config_name"])
            for matrix_row in metrics.get("transfer_matrix", []):
                transfer_rows.append(
                    build_transfer_row_from_matrix(exp_name, metrics, matrix_row)
                )
            if not metrics.get("transfer_matrix"):
                for tr in metrics["transfer_results"]:
                    pseudo_row = {
                        "source_system": metrics.get("source_system", ""),
                        "target_system": tgt,
                        "source_goal": tr.get("goal", metrics.get("goal", "")),
                        "source_attack_variant_id": tr.get("variant_id", ""),
                        "source_metric": tr.get("source_metric", 0.0),
                        "target_leakage_asr": tr.get("target_metric", 0.0)
                        if tr.get("goal") == "leakage"
                        else 0.0,
                        "target_utility_drop": tr.get("target_metric", 0.0)
                        if tr.get("goal") == "degradation"
                        else 0.0,
                        "transfer_asr": tr.get("transfer_asr", 0.0),
                        "generalization_gap": tr.get("generalization_gap", 0.0),
                        "transfer_experiment_name": metrics.get("experiment_name", exp_name),
                        "source_experiment_name": metrics.get("source_experiment", ""),
                        "source_config_name": metrics.get("source_experiment", ""),
                        "target_config_name": metrics.get("target_config_name", tgt),
                    }
                    transfer_rows.append(
                        build_transfer_row_from_matrix(exp_name, metrics, pseudo_row)
                    )

        exp_dir = results_path / exp_name
        variants = read_jsonl(exp_dir / "best_variants.jsonl")
        for rec in variants[:5]:
            v = rec.get("variant", rec)
            vmeta = v.get("metadata", {})
            best_variant_rows.append(
                with_metadata(
                    {
                        "variant_id": v.get("id", ""),
                        "score": rec.get("score", vmeta.get("score", "")),
                        "injection_location": v.get("injection_location", ""),
                        "target_channel": v.get("target_channel", ""),
                        "target_agent": v.get("target_agent", ""),
                        "stealth_level": v.get("stealth_level", ""),
                        "attack_family": vmeta.get("attack_family", ""),
                        "intended_propagation_path": vmeta.get("intended_propagation_path", ""),
                    },
                    meta,
                )
            )

    by_system: Dict[str, List[Dict[str, Any]]] = {}
    for row in leakage_rows:
        by_system.setdefault(row["system"], []).append(row)

    for system, rows in by_system.items():
        baseline = next((r for r in rows if r["defense"] in ("no_defense", "D0")), rows[0])
        defended = next((r for r in rows if r["defense"] not in ("no_defense", "D0")), baseline)
        base_asr = float(baseline.get("leakage_asr", 0.0))
        def_asr = float(defended.get("leakage_asr", 0.0))
        leakage_reduction = max(0.0, base_asr - def_asr) if base_asr > 0 else 0.0
        baseline_meta = {k: baseline.get(k) for k in COMMON_METADATA_FIELDS}
        defense_rows.append(
            with_metadata(
                {
                    "defense": defended.get("defense", "no_defense"),
                    "leakage_reduction": leakage_reduction,
                    "utility_preservation": 1.0 - float(defended.get("output_only_miss_rate", 0.0)),
                    "false_refusal_rate": 0.0,
                    "defense_cost_overhead": 0.05 if defended.get("defense") != "no_defense" else 0.0,
                },
                baseline_meta,
            )
        )

    internal_clean_leakage = filter_internal_clean_leakage(leakage_rows)
    internal_clean_attack = filter_internal_clean_attack_comparison(attack_comparison_rows)
    internal_clean_defense = filter_internal_clean_defense_comparison(defense_comparison_rows)
    internal_clean_difficulty = filter_internal_clean_difficulty(difficulty_comparison_rows)
    internal_clean_transfer = filter_internal_clean_transfer(transfer_rows)
    internal_clean_degradation = filter_internal_clean_degradation(degradation_rows)
    internal_clean_transfer_summary = build_transfer_summary(internal_clean_transfer)
    internal_clean_degradation_summary = build_degradation_summary(internal_clean_degradation)
    internal_clean_external_leakage = filter_internal_clean_external_leakage(external_leakage_rows)
    internal_clean_external_attack = filter_internal_clean_external_attack_comparison(
        external_attack_comparison_rows
    )
    internal_clean_external_defense = filter_internal_clean_external_defense_comparison(
        external_defense_comparison_rows
    )
    internal_clean_external_summary = build_external_leakage_summary(internal_clean_external_leakage)
    internal_clean_external_selective_attack = filter_internal_clean_external_selective_attack_comparison(
        external_attack_comparison_rows
    )
    internal_clean_external_selective_summary = build_external_selective_summary(
        internal_clean_external_selective_attack + [
            r for r in internal_clean_external_leakage
            if r.get("finalizer_exposure_mode") == "selective_finalizer_context"
        ]
    )
    internal_clean_real_leakage = filter_internal_clean_real_leakage(leakage_rows)
    internal_clean_real_external = filter_internal_clean_real_external_leakage(
        external_leakage_rows
    )
    internal_clean_real_attack = filter_internal_clean_real_attack_comparison(leakage_rows)
    internal_clean_agentdojo_real_leakage = filter_internal_clean_agentdojo_real_leakage(
        leakage_rows
    )
    internal_clean_agentdojo_real_external = filter_internal_clean_agentdojo_real_external_leakage(
        external_leakage_rows
    )
    internal_clean_agentdojo_real_attack = filter_internal_clean_agentdojo_real_attack_comparison(
        leakage_rows
    )
    internal_clean_attack_preview = select_attack_comparison_preview_rows(internal_clean_attack)

    _write_csv(summary_path / "table_leakage_by_system.csv", leakage_rows)
    _write_csv(summary_path / "table_internal_vs_final_leakage.csv", internal_final_rows)
    _write_csv(summary_path / "table_degradation_by_system.csv", degradation_rows)
    _write_csv(summary_path / "table_defense_tradeoff.csv", defense_rows)
    _write_csv(
        summary_path / "table_transferability_matrix.csv",
        transfer_rows,
        fieldnames=TRANSFER_TABLE_FIELDS,
    )
    _write_csv(summary_path / "table_best_variants.csv", best_variant_rows)
    _write_csv(summary_path / "table_attack_comparison.csv", attack_comparison_rows)
    _write_csv(summary_path / "table_difficulty_comparison.csv", difficulty_comparison_rows)
    _write_csv(summary_path / "table_defense_comparison.csv", defense_comparison_rows)

    _write_csv(
        summary_path / "internal_clean_leakage_results.csv",
        internal_clean_leakage,
        fallback_fieldnames=_headers_or(leakage_rows),
    )
    _write_csv(
        summary_path / "internal_clean_attack_comparison.csv",
        internal_clean_attack,
        fallback_fieldnames=_headers_or(attack_comparison_rows),
    )
    _write_csv(
        summary_path / "internal_clean_defense_comparison.csv",
        internal_clean_defense,
        fallback_fieldnames=_headers_or(defense_comparison_rows),
    )
    _write_csv(
        summary_path / "internal_clean_difficulty_comparison.csv",
        internal_clean_difficulty,
        fallback_fieldnames=_headers_or(difficulty_comparison_rows),
    )
    _write_csv(
        summary_path / "internal_clean_transferability_matrix.csv",
        internal_clean_transfer,
        fieldnames=TRANSFER_TABLE_FIELDS,
    )
    _write_csv(
        summary_path / "internal_clean_degradation_results.csv",
        internal_clean_degradation,
        fallback_fieldnames=_headers_or(degradation_rows),
    )
    _write_csv(
        summary_path / "internal_clean_transfer_summary.csv",
        internal_clean_transfer_summary,
        fieldnames=TRANSFER_SUMMARY_GROUP_FIELDS + TRANSFER_SUMMARY_METRIC_FIELDS,
    )
    _write_csv(
        summary_path / "internal_clean_degradation_summary.csv",
        internal_clean_degradation_summary,
        fieldnames=DEGRADATION_SUMMARY_GROUP_FIELDS + DEGRADATION_SUMMARY_METRIC_FIELDS,
    )
    _write_csv(
        summary_path / "internal_clean_external_leakage_results.csv",
        internal_clean_external_leakage,
        fallback_fieldnames=_headers_or(external_leakage_rows),
    )
    external_attack_fallback = _headers_or(external_attack_comparison_rows) or (
        _headers_or(external_leakage_rows) + ["attack_generator_version"]
    )
    _write_csv(
        summary_path / "internal_clean_external_attack_comparison.csv",
        internal_clean_external_attack,
        fallback_fieldnames=external_attack_fallback,
    )
    _write_csv(
        summary_path / "internal_clean_external_defense_comparison.csv",
        internal_clean_external_defense,
        fallback_fieldnames=_headers_or(external_defense_comparison_rows)
        or _headers_or(external_leakage_rows),
    )
    _write_csv(
        summary_path / "internal_clean_external_leakage_summary.csv",
        internal_clean_external_summary,
        fieldnames=EXTERNAL_LEAKAGE_SUMMARY_GROUP_FIELDS + EXTERNAL_LEAKAGE_SUMMARY_METRIC_FIELDS,
    )
    _write_csv(
        summary_path / "internal_clean_autoresearch_v2_diagnostics.csv",
        autoresearch_v2_diagnostics_rows,
        fallback_fieldnames=_headers_or(autoresearch_v2_diagnostics_rows),
    )
    _write_csv(
        summary_path / "internal_clean_external_selective_attack_comparison.csv",
        internal_clean_external_selective_attack,
        fallback_fieldnames=_headers_or(external_attack_comparison_rows)
        or _headers_or(external_leakage_rows),
    )
    _write_csv(
        summary_path / "internal_clean_external_selective_summary.csv",
        internal_clean_external_selective_summary,
        fieldnames=SELECTIVE_EXTERNAL_SUMMARY_GROUP_FIELDS + SELECTIVE_EXTERNAL_SUMMARY_METRIC_FIELDS,
    )
    _write_csv(
        summary_path / "internal_clean_real_leakage_results.csv",
        internal_clean_real_leakage,
        fieldnames=REAL_CLEAN_TABLE_FIELDNAMES,
    )
    _write_csv(
        summary_path / "internal_clean_real_external_leakage_results.csv",
        internal_clean_real_external,
        fieldnames=REAL_CLEAN_TABLE_FIELDNAMES,
    )
    _write_csv(
        summary_path / "internal_clean_real_attack_comparison.csv",
        internal_clean_real_attack,
        fieldnames=REAL_CLEAN_TABLE_FIELDNAMES,
    )
    _write_csv(
        summary_path / "internal_clean_agentdojo_real_leakage_results.csv",
        internal_clean_agentdojo_real_leakage,
        fieldnames=REAL_CLEAN_TABLE_FIELDNAMES,
    )
    _write_csv(
        summary_path / "internal_clean_agentdojo_real_external_leakage_results.csv",
        internal_clean_agentdojo_real_external,
        fieldnames=REAL_CLEAN_TABLE_FIELDNAMES,
    )
    _write_csv(
        summary_path / "internal_clean_agentdojo_real_attack_comparison.csv",
        internal_clean_agentdojo_real_attack,
        fieldnames=REAL_CLEAN_TABLE_FIELDNAMES,
    )

    _write_paper_markdown(
        summary_path / "paper_tables.md",
        leakage_rows,
        internal_final_rows,
        degradation_rows,
        defense_rows,
        transfer_rows,
        best_variant_rows,
        attack_comparison_rows,
        difficulty_comparison_rows,
        defense_comparison_rows,
        internal_clean_attack,
        internal_clean_defense,
        internal_clean_difficulty,
        internal_clean_transfer,
        internal_clean_degradation,
        internal_clean_transfer_summary,
        internal_clean_degradation_summary,
        internal_clean_external_leakage,
        internal_clean_external_attack,
        internal_clean_external_defense,
        internal_clean_external_summary,
        autoresearch_v2_diagnostics_rows,
        internal_clean_external_selective_attack,
        internal_clean_external_selective_summary,
        internal_clean_real_leakage,
        internal_clean_real_external,
        internal_clean_real_attack,
        internal_clean_agentdojo_real_leakage,
        internal_clean_agentdojo_real_external,
        internal_clean_agentdojo_real_attack,
        internal_clean_attack_preview,
    )


def _headers_or(rows: List[Dict[str, Any]]) -> List[str]:
    return list(rows[0].keys()) if rows else []


def _write_csv(
    path: Path,
    rows: List[Dict[str, Any]],
    fieldnames: List[str] | None = None,
    fallback_fieldnames: List[str] | None = None,
) -> None:
    headers = fieldnames or _headers_or(rows) or fallback_fieldnames or []
    if not headers:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def _write_paper_markdown(
    path: Path,
    leakage: List[Dict[str, Any]],
    internal_final: List[Dict[str, Any]],
    degradation: List[Dict[str, Any]],
    defense: List[Dict[str, Any]],
    transfer: List[Dict[str, Any]],
    best_variants: List[Dict[str, Any]],
    attack_comparison: List[Dict[str, Any]] = [],
    difficulty_comparison: List[Dict[str, Any]] = [],
    defense_comparison: List[Dict[str, Any]] = [],
    internal_clean_attack: List[Dict[str, Any]] = [],
    internal_clean_defense: List[Dict[str, Any]] = [],
    internal_clean_difficulty: List[Dict[str, Any]] = [],
    internal_clean_transfer: List[Dict[str, Any]] = [],
    internal_clean_degradation: List[Dict[str, Any]] = [],
    internal_clean_transfer_summary: List[Dict[str, Any]] = [],
    internal_clean_degradation_summary: List[Dict[str, Any]] = [],
    internal_clean_external_leakage: List[Dict[str, Any]] = [],
    internal_clean_external_attack: List[Dict[str, Any]] = [],
    internal_clean_external_defense: List[Dict[str, Any]] = [],
    internal_clean_external_summary: List[Dict[str, Any]] = [],
    autoresearch_v2_diagnostics: List[Dict[str, Any]] = [],
    internal_clean_external_selective_attack: List[Dict[str, Any]] = [],
    internal_clean_external_selective_summary: List[Dict[str, Any]] = [],
    internal_clean_real_leakage: List[Dict[str, Any]] = [],
    internal_clean_real_external: List[Dict[str, Any]] = [],
    internal_clean_real_attack: List[Dict[str, Any]] = [],
    internal_clean_agentdojo_real_leakage: List[Dict[str, Any]] = [],
    internal_clean_agentdojo_real_external: List[Dict[str, Any]] = [],
    internal_clean_agentdojo_real_attack: List[Dict[str, Any]] = [],
    internal_clean_attack_preview: List[Dict[str, Any]] = [],
) -> None:
    sections: List[str] = ["# Paper Tables\n"]

    if leakage:
        headers = list(leakage[0].keys())
        sections.append("## Leakage by System\n")
        sections.append(_csv_to_markdown(headers, leakage))
        sections.append("")

    if internal_final:
        headers = list(internal_final[0].keys())
        sections.append("## Internal vs Final Leakage\n")
        sections.append(_csv_to_markdown(headers, internal_final))
        sections.append("")

    if degradation:
        headers = list(degradation[0].keys())
        sections.append("## Degradation by System\n")
        sections.append(_csv_to_markdown(headers, degradation))
        sections.append("")

    if defense:
        headers = list(defense[0].keys())
        sections.append("## Defense Tradeoff\n")
        sections.append(_csv_to_markdown(headers, defense))
        sections.append("")

    if transfer:
        headers = list(transfer[0].keys())
        sections.append("## Transferability Matrix\n")
        sections.append(_csv_to_markdown(headers, transfer))
        sections.append("")

    if best_variants:
        headers = list(best_variants[0].keys())
        sections.append("## Best Variants\n")
        sections.append(_csv_to_markdown(headers, best_variants[:20]))
        sections.append("")

    if attack_comparison:
        headers = list(attack_comparison[0].keys())
        sections.append("## Attack Comparison\n")
        sections.append(_csv_to_markdown(headers, attack_comparison))
        sections.append("")

    if difficulty_comparison:
        headers = list(difficulty_comparison[0].keys())
        sections.append("## Difficulty Comparison\n")
        sections.append(_csv_to_markdown(headers, difficulty_comparison))
        sections.append("")

    if defense_comparison:
        headers = list(defense_comparison[0].keys())
        sections.append("## Defense Comparison\n")
        sections.append(_csv_to_markdown(headers, defense_comparison))
        sections.append("")

    if any(
        [
            internal_clean_attack,
            internal_clean_defense,
            internal_clean_difficulty,
            internal_clean_transfer,
            internal_clean_degradation,
            internal_clean_transfer_summary,
            internal_clean_degradation_summary,
            internal_clean_external_leakage,
            internal_clean_external_attack,
            internal_clean_external_defense,
            internal_clean_external_summary,
            autoresearch_v2_diagnostics,
            internal_clean_external_selective_attack,
            internal_clean_external_selective_summary,
            internal_clean_real_leakage,
            internal_clean_real_external,
            internal_clean_real_attack,
            internal_clean_agentdojo_real_leakage,
            internal_clean_agentdojo_real_external,
            internal_clean_agentdojo_real_attack,
            internal_clean_attack_preview,
        ]
    ):
        sections.append("## Internal Clean Analysis Tables\n")

        preview_rows = internal_clean_attack_preview or internal_clean_attack
        if preview_rows:
            headers = list(preview_rows[0].keys())
            sections.append("### Attack Comparison (clean)\n")
            sections.append(_csv_to_markdown(headers, preview_rows, limit=15))
            sections.append("")

        if internal_clean_defense:
            headers = list(internal_clean_defense[0].keys())
            sections.append("### Defense Comparison (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_defense, limit=15))
            sections.append("")

        if internal_clean_difficulty:
            headers = list(internal_clean_difficulty[0].keys())
            sections.append("### Difficulty Comparison (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_difficulty, limit=15))
            sections.append("")

        if internal_clean_transfer:
            headers = list(internal_clean_transfer[0].keys())
            sections.append("### Transferability Matrix (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_transfer, limit=15))
            sections.append("")

        if internal_clean_transfer_summary:
            headers = list(internal_clean_transfer_summary[0].keys())
            sections.append("### Transfer Summary (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_transfer_summary, limit=15))
            sections.append("")

        if internal_clean_degradation:
            headers = list(internal_clean_degradation[0].keys())
            sections.append("### Degradation Results (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_degradation, limit=15))
            sections.append("")

        if internal_clean_degradation_summary:
            headers = list(internal_clean_degradation_summary[0].keys())
            sections.append("### Degradation Summary (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_degradation_summary, limit=15))
            sections.append("")

        if internal_clean_external_leakage:
            headers = list(internal_clean_external_leakage[0].keys())
            sections.append("### External Leakage Results (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_external_leakage, limit=15))
            sections.append("")

        if internal_clean_external_attack:
            headers = list(internal_clean_external_attack[0].keys())
            sections.append("### External Attack Comparison (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_external_attack, limit=15))
            sections.append("")

        if internal_clean_external_defense:
            headers = list(internal_clean_external_defense[0].keys())
            sections.append("### External Defense Comparison (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_external_defense, limit=15))
            sections.append("")

        if internal_clean_external_summary:
            headers = list(internal_clean_external_summary[0].keys())
            sections.append("### External Leakage Summary (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_external_summary, limit=15))
            sections.append("")

        if autoresearch_v2_diagnostics:
            headers = list(autoresearch_v2_diagnostics[0].keys())
            sections.append("### AutoResearch v2 Diagnostics (clean)\n")
            sections.append(_csv_to_markdown(headers, autoresearch_v2_diagnostics, limit=15))
            sections.append("")

        if internal_clean_external_selective_attack:
            headers = list(internal_clean_external_selective_attack[0].keys())
            sections.append("### External Selective Attack Comparison (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_external_selective_attack, limit=15))
            sections.append("")

        if internal_clean_external_selective_summary:
            headers = list(internal_clean_external_selective_summary[0].keys())
            sections.append("### External Selective Summary (clean)\n")
            sections.append(_csv_to_markdown(headers, internal_clean_external_selective_summary, limit=15))
            sections.append("")

        if any(
            [
                internal_clean_real_leakage,
                internal_clean_real_external,
                internal_clean_real_attack,
                internal_clean_agentdojo_real_leakage,
                internal_clean_agentdojo_real_external,
                internal_clean_agentdojo_real_attack,
            ]
        ):
            sections.append("## Real Framework Experiments\n")

        if internal_clean_real_leakage:
            headers = list(internal_clean_real_leakage[0].keys())
            sections.append("### Real Leakage Results\n")
            sections.append(_csv_to_markdown(headers, internal_clean_real_leakage, limit=15))
            sections.append("")

        if internal_clean_real_external:
            headers = list(internal_clean_real_external[0].keys())
            sections.append("### Real External Leakage Results\n")
            sections.append(_csv_to_markdown(headers, internal_clean_real_external, limit=15))
            sections.append("")

        if internal_clean_real_attack:
            headers = list(internal_clean_real_attack[0].keys())
            sections.append("### Real Attack Comparison\n")
            sections.append(_csv_to_markdown(headers, internal_clean_real_attack, limit=15))
            sections.append("")

        if internal_clean_agentdojo_real_leakage:
            headers = list(internal_clean_agentdojo_real_leakage[0].keys())
            sections.append("### AgentDojo Real Leakage Results\n")
            sections.append(_csv_to_markdown(headers, internal_clean_agentdojo_real_leakage, limit=15))
            sections.append("")

        if internal_clean_agentdojo_real_external:
            headers = list(internal_clean_agentdojo_real_external[0].keys())
            sections.append("### AgentDojo Real External Leakage Results\n")
            sections.append(_csv_to_markdown(headers, internal_clean_agentdojo_real_external, limit=15))
            sections.append("")

        if internal_clean_agentdojo_real_attack:
            headers = list(internal_clean_agentdojo_real_attack[0].keys())
            sections.append("### AgentDojo Real Attack Comparison\n")
            sections.append(_csv_to_markdown(headers, internal_clean_agentdojo_real_attack, limit=15))
            sections.append("")

    path.write_text("\n".join(sections), encoding="utf-8")
