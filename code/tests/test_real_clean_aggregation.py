"""Tests for real-framework clean table deduplication and previews."""

from __future__ import annotations

from agent_redteam.table_aggregation import (
    deduplicate_real_clean_rows,
    filter_internal_clean_real_attack_comparison,
    select_attack_comparison_preview_rows,
)


def _base_row(**overrides):
    row = {
        "experiment_name": "langgraph_real_attack_compare_auto_v2",
        "config_name": "langgraph_real_attack_compare_auto_v2",
        "system": "langgraph_real",
        "integration_mode": "real",
        "calibration_profile": "medium",
        "goal": "leakage",
        "attack_type": "auto_research",
        "attack_generator_version": "v2",
        "defense": "no_defense",
        "random_seed": 42,
        "num_iterations": 12,
        "num_tasks": 8,
        "leakage_asr": 0.9,
        "external_leakage_asr": "",
        "final_output_leakage_rate": 0.0,
        "internal_leakage_rate": 0.9,
        "total_exposure_rate": 0.9,
        "output_only_miss_rate": 0.9,
        "final_output_source": "",
        "adapter_name": "",
    }
    row.update(overrides)
    return row


def test_deduplicate_real_clean_prefers_external_asr_row():
    sparse = _base_row()
    rich = _base_row(
        external_leakage_asr=0.323,
        final_output_leakage_rate=0.323,
        final_output_source="real_framework_response",
        adapter_name="LangGraphRealAdapter",
    )
    deduped = deduplicate_real_clean_rows([sparse, rich])
    assert len(deduped) == 1
    assert deduped[0]["external_leakage_asr"] == 0.323
    assert deduped[0]["final_output_source"] == "real_framework_response"
    assert deduped[0]["adapter_name"] == "LangGraphRealAdapter"


def test_real_attack_comparison_deduplicates_to_one_row_per_config():
    rows = [
        _base_row(experiment_group="attack_comparison"),
        _base_row(
            external_leakage_asr=0.323,
            final_output_leakage_rate=0.323,
            final_output_source="real_framework_response",
            adapter_name="LangGraphRealAdapter",
        ),
    ]
    filtered = filter_internal_clean_real_attack_comparison(rows)
    assert len(filtered) == 1
    assert filtered[0]["attack_generator_version"] == "v2"
    assert filtered[0]["final_output_leakage_rate"] == 0.323


def test_attack_comparison_preview_includes_langgraph_auto_v2():
    rows = []
    for version in ("random", "manual_baseline", "v1", "v2"):
        name = f"langgraph_real_attack_compare_{version}"
        attack_type = "manual_baseline" if version == "manual_baseline" else (
            "auto_research" if version != "random" else "random"
        )
        gen_version = "v1" if version in ("random", "manual_baseline", "v1") else "v2"
        rows.append(
            {
                "experiment_name": name,
                "config_name": name,
                "experiment_group": "attack_comparison",
                "system": "langgraph_synthetic",
                "integration_mode": "synthetic_fallback",
                "calibration_profile": "medium",
                "goal": "leakage",
                "attack_type": attack_type,
                "attack_generator_version": gen_version,
                "defense": "no_defense",
                "random_seed": 42,
                "num_iterations": 12,
                "num_tasks": 8,
                "leakage_asr": 0.5,
            }
        )
    for version in ("random", "manual", "auto_v1", "auto_v2"):
        name = f"langgraph_real_attack_compare_{version}"
        rows.append(
            _base_row(
                experiment_name=name,
                config_name=name,
                experiment_group="attack_comparison",
                attack_type="random" if version == "random" else (
                    "manual_baseline" if version == "manual" else "auto_research"
                ),
                attack_generator_version="v2" if version == "auto_v2" else "v1",
                external_leakage_asr=0.323 if version == "auto_v2" else 0.0,
                final_output_leakage_rate=0.323 if version == "auto_v2" else 0.0,
                final_output_source="real_framework_response",
                adapter_name="LangGraphRealAdapter",
            )
        )
    preview = select_attack_comparison_preview_rows(rows, limit=15)
    real_names = {
        r["experiment_name"]
        for r in preview
        if r.get("system") == "langgraph_real" and "attack_compare" in r["experiment_name"]
    }
    assert "langgraph_real_attack_compare_auto_v2" in real_names
    assert preview[0]["experiment_name"] == "langgraph_real_attack_compare_auto_v2"
