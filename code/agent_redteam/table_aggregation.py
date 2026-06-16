"""Helpers for summary table metadata, grouping, deduplication, and clean analysis filters."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from agent_redteam.experiments.experiment_metadata import (
    infer_architecture,
    resolve_calibration_profile,
    resolve_integration_mode,
)

CONFIG_ALIAS_MAP: Dict[str, str] = {
    "langgraph_defense_memory_or_inter_agent_redaction": "langgraph_defense_memory_redaction",
}

DEDUPE_KEY_FIELDS: List[str] = [
    "system",
    "integration_mode",
    "calibration_profile",
    "goal",
    "attack_type",
    "defense",
    "random_seed",
    "num_iterations",
    "num_tasks",
]

COMMON_METADATA_FIELDS: List[str] = [
    "experiment_name",
    "config_name",
    "experiment_group",
    "system",
    "architecture",
    "integration_mode",
    "calibration_profile",
    "goal",
    "attack_type",
    "defense",
    "random_seed",
    "num_iterations",
    "num_tasks",
    "is_alias_config",
    "finalizer_exposure_mode",
    "attack_generator_version",
    "final_output_source",
    "adapter_name",
]

REAL_CLEAN_METRIC_FIELDS: List[str] = [
    "leakage_asr",
    "external_leakage_asr",
    "final_output_leakage_rate",
    "internal_leakage_rate",
    "total_exposure_rate",
    "output_only_miss_rate",
]

REAL_CLEAN_DEDUPE_KEY_FIELDS: List[str] = [
    "experiment_name",
    "config_name",
    "system",
    "integration_mode",
    "calibration_profile",
    "goal",
    "attack_type",
    "attack_generator_version",
    "defense",
    "random_seed",
    "num_iterations",
    "num_tasks",
]

REAL_CLEAN_TABLE_FIELDNAMES: List[str] = REAL_CLEAN_METRIC_FIELDS + COMMON_METADATA_FIELDS

REAL_FRAMEWORK_SYSTEMS: frozenset[str] = frozenset({"langgraph_real", "agentdojo_real"})

EXTENDED_VARIANT_FIELDS: List[str] = [
    "attack_family",
    "intended_propagation_path",
]


def infer_system(exp_name: str, metrics: Dict[str, Any]) -> str:
    if metrics.get("system_name"):
        return str(metrics["system_name"])
    name = exp_name.lower()
    for key in (
        "langgraph_real",
        "langgraph_synthetic",
        "autogen_synthetic",
        "crewai_synthetic",
        "agentdojo_real",
        "agentdojo",
        "mock",
    ):
        if key in name:
            return key
    return "mock"


def infer_integration_mode(exp_name: str, metrics: Dict[str, Any], system: str) -> str:
    if metrics.get("integration_mode"):
        return str(metrics["integration_mode"])
    adapter_config = metrics.get("adapter_config") or {}
    return resolve_integration_mode(system, system, adapter_config)


def infer_calibration_profile(exp_name: str, metrics: Dict[str, Any]) -> str:
    if metrics.get("calibration_profile"):
        return str(metrics["calibration_profile"])
    if metrics.get("difficulty_profile"):
        return str(metrics["difficulty_profile"])
    adapter_config = metrics.get("adapter_config") or {}
    return resolve_calibration_profile(adapter_config, exp_name)


def infer_experiment_group(
    exp_name: str,
    config_name: str,
    goal: str,
    calibration_profile: str,
    metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """Infer experiment group for summary table rows."""
    name = (exp_name or config_name or "").lower()
    metrics = metrics or {}

    if calibration_profile == "legacy":
        return "legacy_validation"

    if goal == "external_leakage" or "external_leakage" in name:
        return "external_leakage"

    if goal == "degradation" or "degradation" in name:
        return "degradation"

    if "leakage_medium" in name or "leakage_hard" in name:
        return "difficulty"

    if "attack_compare" in name:
        return "attack_comparison"

    if "defense" in name:
        return "defense_comparison"

    if (
        metrics.get("transfer_matrix")
        or metrics.get("transfer_results")
        or "transfer" in name
        or "matrix" in name
    ):
        return "transfer"

    return "general"


def compute_alias_flags(experiment_names: Sequence[str]) -> Dict[str, bool]:
    """Return is_alias_config for each experiment name when canonical also exists."""
    existing: Set[str] = set(experiment_names)
    flags: Dict[str, bool] = {}
    for exp in experiment_names:
        canonical = CONFIG_ALIAS_MAP.get(exp)
        flags[exp] = bool(canonical and canonical in existing)
    return flags


def build_experiment_metadata(
    exp_dir_name: str,
    metrics: Dict[str, Any],
    alias_flags: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """Build common metadata columns for a summary table row."""
    experiment_name = str(metrics.get("experiment_name", exp_dir_name))
    config_name = str(metrics.get("config_name", experiment_name))
    system = infer_system(exp_dir_name, metrics)
    calibration_profile = infer_calibration_profile(exp_dir_name, metrics)
    goal = str(metrics.get("goal", ""))
    experiment_group = infer_experiment_group(
        experiment_name, config_name, goal, calibration_profile, metrics
    )
    is_alias = False
    if alias_flags is not None:
        is_alias = alias_flags.get(experiment_name, False)

    return {
        "experiment_name": experiment_name,
        "config_name": config_name,
        "experiment_group": experiment_group,
        "system": system,
        "architecture": metrics.get("architecture") or infer_architecture(system),
        "integration_mode": infer_integration_mode(exp_dir_name, metrics, system),
        "calibration_profile": calibration_profile,
        "goal": goal,
        "attack_type": metrics.get("attack_generator", "auto_research"),
        "defense": metrics.get("defense", "no_defense"),
        "random_seed": metrics.get("random_seed", ""),
        "num_iterations": metrics.get("num_iterations", ""),
        "num_tasks": metrics.get("num_tasks", ""),
        "is_alias_config": is_alias,
        "finalizer_exposure_mode": metrics.get(
            "finalizer_exposure_mode",
            (metrics.get("adapter_config") or {}).get("finalizer_exposure_mode", "safe_finalizer"),
        ),
        "attack_generator_version": metrics.get("attack_generator_version", "v1"),
        "final_output_source": metrics.get("final_output_source", ""),
        "adapter_name": metrics.get("adapter_name", ""),
    }


def with_metadata(
    row: Dict[str, Any],
    metadata: Dict[str, Any],
    extra_fields: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Merge metadata into a row, preserving metric columns."""
    fields = list(COMMON_METADATA_FIELDS)
    if extra_fields:
        fields.extend(extra_fields)
    merged = dict(row)
    for key in fields:
        if key in metadata:
            merged[key] = metadata[key]
    return merged


def _drop_alias_when_canonical_present(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop alias-config rows when the canonical experiment is also present."""
    names = {r.get("experiment_name") for r in rows}
    return [
        r
        for r in rows
        if not (
            r.get("is_alias_config")
            and CONFIG_ALIAS_MAP.get(str(r.get("experiment_name", "")), "") in names
        )
    ]


def _infer_profile_from_experiment_name(name: str) -> Optional[str]:
    lowered = (name or "").lower()
    if "hard" in lowered:
        return "hard"
    if "medium" in lowered:
        return "medium"
    if "easy" in lowered:
        return "easy"
    return None


def deduplicate_analysis_rows(
    rows: List[Dict[str, Any]],
    key_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Remove alias duplicates; prefer canonical (non-alias) rows."""
    rows = _drop_alias_when_canonical_present(rows)
    keys = key_fields or DEDUPE_KEY_FIELDS
    buckets: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        bucket_key = tuple(row.get(k) for k in keys)
        buckets.setdefault(bucket_key, []).append(row)

    result: List[Dict[str, Any]] = []
    for group in buckets.values():
        non_alias = [r for r in group if not r.get("is_alias_config")]
        result.append(non_alias[0] if non_alias else group[0])
    return result


def build_transfer_row_from_matrix(
    exp_dir_name: str,
    metrics: Dict[str, Any],
    matrix_row: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a transferability table row from metrics_summary transfer_matrix entry."""
    transfer_experiment = str(
        matrix_row.get("transfer_experiment_name", metrics.get("experiment_name", exp_dir_name))
    )
    source_experiment = str(
        matrix_row.get("source_experiment_name", metrics.get("source_experiment", ""))
    )
    source_cal = matrix_row.get("source_calibration_profile")
    if not source_cal or source_cal == "legacy":
        source_cal = _infer_profile_from_experiment_name(source_experiment)
    if not source_cal or source_cal == "legacy":
        source_cal = infer_calibration_profile(source_experiment, metrics)
    if (not source_cal or source_cal == "legacy") and source_experiment == "matrix":
        matrix_profile = _infer_profile_from_experiment_name(transfer_experiment)
        if matrix_profile:
            source_cal = matrix_profile

    target_cal = matrix_row.get("target_calibration_profile")
    if not target_cal:
        target_cal = _infer_profile_from_experiment_name(transfer_experiment)
    if not target_cal or target_cal == "legacy":
        inferred = _infer_profile_from_experiment_name(transfer_experiment)
        if inferred:
            target_cal = inferred
        else:
            target_cal = infer_calibration_profile(transfer_experiment, metrics)
    source_system = matrix_row.get("source_system", metrics.get("source_system", ""))
    target_system = matrix_row.get("target_system", metrics.get("target_system", "unknown"))

    source_int = matrix_row.get("source_integration_mode") or infer_integration_mode(
        matrix_row.get("source_experiment_name", ""), metrics, str(source_system)
    )
    target_int = matrix_row.get("target_integration_mode") or infer_integration_mode(
        transfer_experiment, metrics, str(target_system)
    )

    goal = matrix_row.get("source_goal", metrics.get("goal", ""))
    metrics_for_group = dict(metrics)
    if target_cal not in ("legacy", ""):
        metrics_for_group["calibration_profile"] = target_cal
    meta = build_experiment_metadata(exp_dir_name, metrics_for_group)
    meta["experiment_group"] = "transfer"
    meta["calibration_profile"] = target_cal

    row = {
        "transfer_experiment_name": transfer_experiment,
        "source_experiment_name": matrix_row.get(
            "source_experiment_name", metrics.get("source_experiment", "")
        ),
        "source_config_name": matrix_row.get(
            "source_config_name",
            matrix_row.get("source_experiment_name", metrics.get("source_experiment", "")),
        ),
        "target_config_name": matrix_row.get(
            "target_config_name",
            matrix_row.get("target_system", metrics.get("target_system", "")),
        ),
        "source_system": source_system,
        "target_system": target_system,
        "source_integration_mode": source_int,
        "target_integration_mode": target_int,
        "source_calibration_profile": source_cal,
        "target_calibration_profile": target_cal,
        "goal": goal,
        "source_attack_variant_id": matrix_row.get("source_attack_variant_id", ""),
        "source_metric": matrix_row.get("source_metric", 0.0),
        "transfer_asr": matrix_row.get("transfer_asr", 0.0),
        "generalization_gap": matrix_row.get("generalization_gap", 0.0),
        "target_total_exposure_rate": matrix_row.get("target_leakage_asr", 0.0),
        "target_utility_drop": matrix_row.get("target_utility_drop", 0.0),
    }
    return with_metadata(row, meta)


def filter_internal_clean_leakage(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("goal") == "leakage"
        and r.get("calibration_profile") in ("medium", "hard")
        and r.get("integration_mode") in ("mock", "synthetic_fallback")
        and r.get("calibration_profile") != "legacy"
    ]
    return deduplicate_analysis_rows(filtered)


def filter_internal_clean_attack_comparison(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("experiment_group") == "attack_comparison"
        and r.get("calibration_profile") == "medium"
        and r.get("calibration_profile") != "legacy"
    ]
    return deduplicate_analysis_rows(filtered)


def filter_internal_clean_defense_comparison(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("experiment_group") == "defense_comparison"
        and r.get("calibration_profile") == "medium"
        and r.get("system") == "langgraph_synthetic"
    ]
    return deduplicate_analysis_rows(filtered)


def filter_internal_clean_difficulty(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("experiment_group") == "difficulty"
        and r.get("calibration_profile") in ("medium", "hard")
        and r.get("attack_type") == "auto_research"
        and r.get("defense") == "no_defense"
        and r.get("calibration_profile") != "legacy"
    ]
    return deduplicate_analysis_rows(filtered)


def _transfer_has_medium_or_hard_calibration(row: Dict[str, Any]) -> bool:
    profiles = [
        row.get("source_calibration_profile"),
        row.get("target_calibration_profile"),
        row.get("calibration_profile"),
    ]
    return any(p in ("medium", "hard") for p in profiles)


def _transfer_is_legacy_only(row: Dict[str, Any]) -> bool:
    source_cal = row.get("source_calibration_profile") or "legacy"
    target_cal = row.get("target_calibration_profile") or "legacy"
    return source_cal == "legacy" and target_cal == "legacy"


def _drop_unknown_target_when_known_exists(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop unknown target_system rows only when the same transfer has known targets."""
    by_experiment: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        exp = str(row.get("transfer_experiment_name", row.get("experiment_name", "")))
        by_experiment[exp].append(row)

    kept: List[Dict[str, Any]] = []
    for group in by_experiment.values():
        has_known_target = any(
            g.get("target_system") not in (None, "", "unknown") for g in group
        )
        for row in group:
            if row.get("target_system") == "unknown" and has_known_target:
                continue
            kept.append(row)
    return kept


def filter_internal_clean_transfer(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter transfer rows for clean analysis; keep all variant rows (no deduplication)."""
    filtered = [
        r
        for r in rows
        if r.get("experiment_group") == "transfer"
        and r.get("goal") == "leakage"
        and _transfer_has_medium_or_hard_calibration(r)
        and not _transfer_is_legacy_only(r)
    ]
    return _drop_unknown_target_when_known_exists(filtered)


def filter_internal_clean_degradation(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("goal") == "degradation"
        and r.get("calibration_profile") in ("medium", "hard")
        and r.get("integration_mode") in ("mock", "synthetic_fallback")
        and r.get("calibration_profile") != "legacy"
    ]
    return deduplicate_analysis_rows(filtered)


TRANSFER_SUMMARY_GROUP_FIELDS: List[str] = [
    "transfer_experiment_name",
    "source_system",
    "target_system",
    "source_calibration_profile",
    "target_calibration_profile",
    "source_integration_mode",
    "target_integration_mode",
]

TRANSFER_SUMMARY_METRIC_FIELDS: List[str] = [
    "mean_transfer_asr",
    "median_transfer_asr",
    "min_transfer_asr",
    "max_transfer_asr",
    "mean_generalization_gap",
    "median_generalization_gap",
    "num_variants",
    "num_successful_variants",
    "success_variant_rate",
]

DEGRADATION_SUMMARY_GROUP_FIELDS: List[str] = [
    "system",
    "integration_mode",
    "calibration_profile",
    "attack_type",
    "defense",
]

DEGRADATION_SUMMARY_METRIC_FIELDS: List[str] = [
    "mean_utility_drop",
    "mean_cost_amplification",
    "mean_latency_increase",
    "mean_tool_call_increase",
    "mean_retry_rate",
    "num_experiments",
]


def build_transfer_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate clean transfer rows by source/target system and calibration profile."""
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in TRANSFER_SUMMARY_GROUP_FIELDS)
        groups[key].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for group in groups.values():
        transfer_asrs = [float(g.get("transfer_asr", 0.0)) for g in group]
        gaps = [float(g.get("generalization_gap", 0.0)) for g in group]
        num_variants = len(group)
        num_successful = sum(1 for v in transfer_asrs if v > 0.0)
        base = {field: group[0].get(field) for field in TRANSFER_SUMMARY_GROUP_FIELDS}
        base.update(
            {
                "mean_transfer_asr": statistics.mean(transfer_asrs),
                "median_transfer_asr": statistics.median(transfer_asrs),
                "min_transfer_asr": min(transfer_asrs),
                "max_transfer_asr": max(transfer_asrs),
                "mean_generalization_gap": statistics.mean(gaps),
                "median_generalization_gap": statistics.median(gaps),
                "num_variants": num_variants,
                "num_successful_variants": num_successful,
                "success_variant_rate": num_successful / num_variants if num_variants else 0.0,
            }
        )
        summary_rows.append(base)
    return summary_rows


def filter_internal_clean_external_leakage(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("goal") == "external_leakage"
        and r.get("calibration_profile") in ("medium", "hard")
        and r.get("integration_mode") in ("mock", "synthetic_fallback")
    ]
    return deduplicate_analysis_rows(filtered)


def filter_internal_clean_external_attack_comparison(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Keep all attack-comparison rows; v1 and v2 differ by version not dedupe key."""
    return [
        r
        for r in rows
        if r.get("goal") == "external_leakage"
        and "attack_compare" in str(r.get("experiment_name", ""))
        and "external" in str(r.get("experiment_name", ""))
        and r.get("calibration_profile") == "medium"
    ]


def filter_internal_clean_external_defense_comparison(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("goal") == "external_leakage"
        and "external_defense" in str(r.get("experiment_name", ""))
        and r.get("calibration_profile") == "medium"
        and r.get("system") == "langgraph_synthetic"
    ]
    return _drop_alias_when_canonical_present(filtered)


EXTERNAL_LEAKAGE_SUMMARY_GROUP_FIELDS: List[str] = [
    "system",
    "integration_mode",
    "calibration_profile",
    "finalizer_exposure_mode",
    "attack_generator_version",
    "defense",
]

EXTERNAL_LEAKAGE_SUMMARY_METRIC_FIELDS: List[str] = [
    "mean_external_leakage_asr",
    "mean_final_output_leakage_rate",
    "mean_internal_leakage_rate",
    "mean_total_exposure_rate",
    "mean_output_only_miss_rate",
    "num_experiments",
]


def filter_internal_clean_external_selective_attack_comparison(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return [
        r
        for r in rows
        if r.get("goal") == "external_leakage"
        and r.get("finalizer_exposure_mode") == "selective_finalizer_context"
        and "selective" in str(r.get("experiment_name", ""))
        and "attack_compare" in str(r.get("experiment_name", ""))
        and r.get("calibration_profile") == "medium"
        and r.get("system") == "langgraph_synthetic"
        and r.get("calibration_profile") != "legacy"
    ]


SELECTIVE_EXTERNAL_SUMMARY_GROUP_FIELDS: List[str] = [
    "system",
    "finalizer_exposure_mode",
    "attack_type",
    "attack_generator_version",
]

SELECTIVE_EXTERNAL_SUMMARY_METRIC_FIELDS: List[str] = [
    "mean_external_leakage_asr",
    "mean_final_output_leakage_rate",
    "mean_internal_leakage_rate",
    "num_experiments",
]


def build_external_selective_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in SELECTIVE_EXTERNAL_SUMMARY_GROUP_FIELDS)
        groups[key].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for group in groups.values():
        ext_asr = [
            float(g.get("external_leakage_asr", g.get("final_output_leakage_rate", 0))) for g in group
        ]
        final_out = [float(g.get("final_output_leakage_rate", 0)) for g in group]
        internal = [float(g.get("internal_leakage_rate", 0)) for g in group]
        base = {field: group[0].get(field) for field in SELECTIVE_EXTERNAL_SUMMARY_GROUP_FIELDS}
        base.update(
            {
                "mean_external_leakage_asr": statistics.mean(ext_asr),
                "mean_final_output_leakage_rate": statistics.mean(final_out),
                "mean_internal_leakage_rate": statistics.mean(internal),
                "num_experiments": len(group),
            }
        )
        summary_rows.append(base)
    return summary_rows


def build_external_leakage_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in EXTERNAL_LEAKAGE_SUMMARY_GROUP_FIELDS)
        groups[key].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for group in groups.values():
        ext_asr = [float(g.get("external_leakage_asr", g.get("final_output_leakage_rate", 0))) for g in group]
        final_out = [float(g.get("final_output_leakage_rate", 0)) for g in group]
        internal = [float(g.get("internal_leakage_rate", 0)) for g in group]
        total = [float(g.get("total_exposure_rate", 0)) for g in group]
        miss = [float(g.get("output_only_miss_rate", 0)) for g in group]
        base = {field: group[0].get(field) for field in EXTERNAL_LEAKAGE_SUMMARY_GROUP_FIELDS}
        base.update(
            {
                "mean_external_leakage_asr": statistics.mean(ext_asr),
                "mean_final_output_leakage_rate": statistics.mean(final_out),
                "mean_internal_leakage_rate": statistics.mean(internal),
                "mean_total_exposure_rate": statistics.mean(total),
                "mean_output_only_miss_rate": statistics.mean(miss),
                "num_experiments": len(group),
            }
        )
        summary_rows.append(base)
    return summary_rows


def _is_external_asr_populated(value: Any) -> bool:
    if value is None or value == "":
        return False
    try:
        return float(value) >= 0.0
    except (TypeError, ValueError):
        return bool(value)


def _real_clean_row_score(row: Dict[str, Any]) -> tuple:
    ext_ok = _is_external_asr_populated(row.get("external_leakage_asr"))
    final_src_ok = row.get("final_output_source") == "real_framework_response"
    adapter_ok = bool(row.get("adapter_name"))
    metric_populated = sum(
        1
        for field in REAL_CLEAN_METRIC_FIELDS
        if row.get(field) is not None and row.get(field) != ""
    )
    return (ext_ok, final_src_ok, adapter_ok, metric_populated)


def deduplicate_real_clean_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate real clean rows; prefer richer metric/metadata rows."""
    buckets: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in REAL_CLEAN_DEDUPE_KEY_FIELDS)
        buckets[key].append(row)
    deduped: List[Dict[str, Any]] = []
    for group in buckets.values():
        deduped.append(max(group, key=_real_clean_row_score))
    return deduped


def _filter_real_framework_rows(
    rows: List[Dict[str, Any]],
    system: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("integration_mode") == "real"
        and r.get("calibration_profile") in ("medium", "hard")
        and r.get("calibration_profile") != "legacy"
    ]
    if system:
        filtered = [r for r in filtered if r.get("system") == system]
    else:
        filtered = [r for r in filtered if r.get("system") in REAL_FRAMEWORK_SYSTEMS]
    return filtered


def filter_internal_clean_real_leakage(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in _filter_real_framework_rows(rows)
        if r.get("goal") == "leakage"
        and "attack_compare" not in str(r.get("experiment_name", ""))
    ]
    return deduplicate_real_clean_rows(_drop_alias_when_canonical_present(filtered))


def filter_internal_clean_real_external_leakage(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in _filter_real_framework_rows(rows)
        if r.get("goal") == "external_leakage"
    ]
    return deduplicate_real_clean_rows(_drop_alias_when_canonical_present(filtered))


def filter_internal_clean_real_attack_comparison(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in _filter_real_framework_rows(rows)
        if "attack_compare" in str(r.get("experiment_name", ""))
        and r.get("calibration_profile") == "medium"
    ]
    return deduplicate_real_clean_rows(_drop_alias_when_canonical_present(filtered))


def filter_internal_clean_agentdojo_real_leakage(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in _filter_real_framework_rows(rows, system="agentdojo_real")
        if r.get("goal") == "leakage"
        and "attack_compare" not in str(r.get("experiment_name", ""))
    ]
    return deduplicate_real_clean_rows(_drop_alias_when_canonical_present(filtered))


def filter_internal_clean_agentdojo_real_external_leakage(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in _filter_real_framework_rows(rows, system="agentdojo_real")
        if r.get("goal") == "external_leakage"
    ]
    return deduplicate_real_clean_rows(_drop_alias_when_canonical_present(filtered))


def filter_internal_clean_agentdojo_real_attack_comparison(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    filtered = [
        r
        for r in _filter_real_framework_rows(rows, system="agentdojo_real")
        if "attack_compare" in str(r.get("experiment_name", ""))
        and r.get("calibration_profile") == "medium"
    ]
    return deduplicate_real_clean_rows(_drop_alias_when_canonical_present(filtered))


def select_attack_comparison_preview_rows(
    rows: List[Dict[str, Any]],
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Build attack-comparison preview prioritizing real LangGraph auto_v2 and all real compare rows."""
    real_langgraph = [
        r
        for r in rows
        if r.get("integration_mode") == "real"
        and r.get("system") == "langgraph_real"
        and "attack_compare" in str(r.get("experiment_name", ""))
    ]
    real_ids = {r.get("experiment_name") for r in real_langgraph}
    others = [r for r in rows if r.get("experiment_name") not in real_ids]

    v2_rows = [r for r in real_langgraph if r.get("attack_generator_version") == "v2"]
    rest_real = [r for r in real_langgraph if r.get("attack_generator_version") != "v2"]
    rest_real.sort(key=lambda r: str(r.get("experiment_name", "")))
    prioritized = v2_rows + rest_real

    if len(prioritized) >= limit:
        return prioritized[:limit]
    remaining = limit - len(prioritized)
    return prioritized + others[:remaining]


def build_degradation_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate clean degradation rows by system and calibration profile."""
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in DEGRADATION_SUMMARY_GROUP_FIELDS)
        groups[key].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for group in groups.values():
        utility = [float(g.get("utility_drop", 0.0)) for g in group]
        cost = [float(g.get("cost_amplification", 0.0)) for g in group]
        latency = [float(g.get("latency_increase", 0.0)) for g in group]
        tool_calls = [float(g.get("tool_call_increase", 0.0)) for g in group]
        retries = [float(g.get("retry_rate", 0.0)) for g in group]
        base = {field: group[0].get(field) for field in DEGRADATION_SUMMARY_GROUP_FIELDS}
        base.update(
            {
                "mean_utility_drop": statistics.mean(utility),
                "mean_cost_amplification": statistics.mean(cost),
                "mean_latency_increase": statistics.mean(latency),
                "mean_tool_call_increase": statistics.mean(tool_calls),
                "mean_retry_rate": statistics.mean(retries),
                "num_experiments": len(group),
            }
        )
        summary_rows.append(base)
    return summary_rows
