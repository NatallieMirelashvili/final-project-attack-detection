"""Focused tests for research metric correctness and non-trivial ASR values."""

from pathlib import Path

import pytest

from agent_redteam.attacks.generators import AutoResearchAttackGenerator
from agent_redteam.data.canaries import CANARY_CLIENT_ID_042, CANARY_FAKE_API_KEY_093
from agent_redteam.evaluation.leakage_metrics import (
    compute_all_leakage_metrics,
    final_output_leakage_rate,
    internal_leakage_rate,
    leakage_asr,
    output_only_miss_rate,
    partial_canary_leakage_rate,
)
from agent_redteam.evaluation.performance_metrics import compute_all_performance_metrics
from agent_redteam.evaluation.transfer_metrics import generalization_gap, transfer_asr
from agent_redteam.experiments.transfer_runner import TransferRunner
from agent_redteam.schemas import RunResult, Trace


def _task_stub(canaries: list[str]):
    return type("T", (), {"sensitive_canaries": canaries})()


def _make_run(
    task_id: str,
    output: str,
    internal: list[str] | None = None,
    attacked: bool = True,
    task_success: bool = True,
    trace_output: str | None = None,
) -> RunResult:
    internal = internal or []
    trace = Trace(
        final_output=trace_output or output,
        inter_agent_messages=internal,
    )
    return RunResult(
        task_id=task_id,
        system_name="mock",
        attack_variant_id="atk_001" if attacked else None,
        defense_name="D0",
        final_output=output,
        task_success=task_success,
        latency_seconds=1.0,
        token_count=100,
        estimated_cost=0.01,
        tool_calls=2,
        retries=0,
        errors=[] if task_success else ["failed"],
        trace=trace,
    )


def _tasks_map(canary: str = CANARY_CLIENT_ID_042):
    return {"task_000": _task_stub([canary])}


class TestLeakageASRValues:
    def test_leakage_asr_zero(self):
        runs = [
            _make_run("task_000", "clean output", []),
            _make_run("task_000", "also clean", []),
        ]
        assert leakage_asr(runs, _tasks_map()) == 0.0

    def test_leakage_asr_half(self):
        runs = [
            _make_run("task_000", f"leaked {CANARY_CLIENT_ID_042}", []),
            _make_run("task_000", "clean output", []),
        ]
        assert leakage_asr(runs, _tasks_map()) == 0.5

    def test_leakage_asr_one(self):
        runs = [_make_run("task_000", CANARY_CLIENT_ID_042, [])]
        assert leakage_asr(runs, _tasks_map()) == 1.0

    def test_internal_only_leakage(self):
        runs = [
            _make_run(
                "task_000",
                "clean final output",
                internal=[f"secret {CANARY_CLIENT_ID_042}"],
            )
        ]
        tasks_map = _tasks_map()
        assert internal_leakage_rate(runs, tasks_map) == 1.0
        assert final_output_leakage_rate(runs, tasks_map) == 0.0
        assert output_only_miss_rate(runs, tasks_map) == 1.0

    def test_final_only_leakage(self):
        runs = [_make_run("task_000", CANARY_CLIENT_ID_042, internal=["clean internal"])]
        tasks_map = _tasks_map()
        assert final_output_leakage_rate(runs, tasks_map) == 1.0
        assert output_only_miss_rate(runs, tasks_map) == 0.0

    def test_no_leakage_clean_run_excluded_from_asr(self):
        runs = [
            _make_run("task_000", "clean", attacked=False),
            _make_run("task_000", "still clean", attacked=True),
        ]
        assert leakage_asr(runs, _tasks_map()) == 0.0

    def test_partial_leakage_without_exact(self):
        fragment = CANARY_CLIENT_ID_042[:12]
        runs = [_make_run("task_000", f"fragment {fragment}", [])]
        tasks_map = _tasks_map()
        assert partial_canary_leakage_rate(runs, tasks_map) == 1.0
        assert leakage_asr(runs, tasks_map) == 0.0

    def test_failed_task_with_leakage_still_counts(self):
        runs = [
            _make_run(
                "task_000",
                CANARY_CLIENT_ID_042,
                task_success=False,
            )
        ]
        assert leakage_asr(runs, _tasks_map()) == 1.0

    def test_run_final_output_overrides_trace_for_channel_breakdown(self):
        """Observed final_output must drive final-output leakage, not stale trace field."""
        runs = [
            _make_run(
                "task_000",
                "redacted clean output",
                trace_output=CANARY_CLIENT_ID_042,
            )
        ]
        metrics = compute_all_leakage_metrics(runs, _tasks_map())
        assert metrics["final_output_leakage_rate"] == 0.0
        assert metrics["channel_breakdown"]["final_output"] == 0.0


class TestPerformanceMetrics:
    def test_utility_drop_against_clean_baseline(self):
        clean = [_make_run("task_000", "ok", attacked=False, task_success=True)]
        attacked = [
            _make_run("task_000", "ok", task_success=True),
            _make_run("task_000", "fail", task_success=False),
        ]
        perf = compute_all_performance_metrics(clean, attacked)
        assert perf["clean_task_success_rate"] == 1.0
        assert perf["attacked_task_success_rate"] == 0.5
        assert perf["utility_drop"] == 0.5


class TestTransferMetrics:
    def test_transfer_asr_is_target_not_source(self):
        target = transfer_asr(
            {"leakage_asr": 1.0},
            {"leakage_asr": 0.5},
            "leakage_asr",
        )
        assert target == 0.5

    def test_generalization_gap_source_minus_target(self):
        gap = generalization_gap(
            {"leakage_asr": 1.0},
            {"leakage_asr": 0.25},
            "leakage_asr",
        )
        assert gap == 0.75

    def test_transfer_asr_values_zero_half_one(self):
        assert transfer_asr({}, {"leakage_asr": 0.0}) == 0.0
        assert transfer_asr({}, {"leakage_asr": 0.5}) == 0.5
        assert transfer_asr({}, {"leakage_asr": 1.0}) == 1.0


class TestAutoResearchGenerator:
    def test_mutates_from_history_after_scores_recorded(self):
        gen = AutoResearchAttackGenerator("leakage", random_seed=99, mutation_rate=1.0)
        first = gen.generate(0)
        gen.record_score(first, 0.9)
        child = gen.generate(1)
        assert child.metadata.get("parent_id") == first.id or child.id != first.id


class TestTransferPerVariantSource:
    def test_transfer_uses_per_variant_source_runs(self, tmp_path):
        source_dir = tmp_path / "results" / "src_exp"
        source_dir.mkdir(parents=True)
        tasks_map = {
            "task_000": _task_stub([CANARY_CLIENT_ID_042]),
            "task_001": _task_stub([CANARY_FAKE_API_KEY_093]),
        }

        variant_a = "variant_a"
        variant_b = "variant_b"
        runs = [
            _make_run("task_000", CANARY_CLIENT_ID_042),
            _make_run("task_001", "clean"),
        ]
        runs[0].attack_variant_id = variant_a
        runs[1].attack_variant_id = variant_a

        leaked_run = _make_run("task_000", CANARY_CLIENT_ID_042)
        leaked_run.attack_variant_id = variant_b
        clean_run = _make_run("task_001", "clean")
        clean_run.attack_variant_id = variant_b
        runs.extend([leaked_run, clean_run])

        from dataclasses import asdict

        with (source_dir / "runs.jsonl").open("w", encoding="utf-8") as f:
            for r in runs:
                f.write(__import__("json").dumps(asdict(r)) + "\n")

        import json

        with (source_dir / "metrics_summary.json").open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "experiment_name": "src_exp",
                    "system_name": "mock",
                    "goal": "leakage",
                    "leakage": {"leakage_asr": 0.75},
                },
                f,
            )

        with (source_dir / "best_variants.jsonl").open("w", encoding="utf-8") as f:
            for vid in [variant_a, variant_b]:
                f.write(
                    json.dumps(
                        {
                            "variant": {
                                "id": vid,
                                "goal": "leakage",
                                "prompt_template": "x {canary}",
                                "injection_location": "user_input",
                                "target_channel": "final_output",
                                "target_agent": "summarizer",
                                "stealth_level": 0.5,
                                "metadata": {},
                            },
                            "score": 1.0,
                        }
                    )
                    + "\n"
                )

        runner = TransferRunner.__new__(TransferRunner)
        val_a = runner._source_metric_for_variant(
            source_dir, variant_a, "leakage", tasks_map, {}
        )
        val_b = runner._source_metric_for_variant(
            source_dir, variant_b, "leakage", tasks_map, {}
        )
        assert val_a == 0.5
        assert val_b == 0.5
