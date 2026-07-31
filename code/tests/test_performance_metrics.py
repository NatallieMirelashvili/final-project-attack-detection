"""Tests for performance metrics."""

from agent_redteam.evaluation.performance_metrics import (
    attacked_task_success_rate,
    clean_task_success_rate,
    compute_all_performance_metrics,
    cost_amplification,
    utility_drop,
)
from agent_redteam.schemas import RunResult, Trace


def _run(success: bool, cost: float = 0.01, latency: float = 1.0, tool_calls: int = 2):
    return RunResult(
        task_id="task_000",
        system_name="mock",
        attack_variant_id=None,
        defense_name="D0",
        final_output="ok",
        task_success=success,
        latency_seconds=latency,
        token_count=100,
        estimated_cost=cost,
        tool_calls=tool_calls,
        retries=0,
        errors=[],
        trace=Trace(),
    )


def test_clean_task_success_rate():
    runs = [_run(True), _run(False)]
    assert clean_task_success_rate(runs) == 0.5


def test_utility_drop():
    clean = [_run(True), _run(True)]
    attacked = [_run(True), _run(False)]
    assert utility_drop(clean, attacked) == 0.5


def test_cost_amplification():
    clean = [_run(True, cost=0.01)]
    attacked = [_run(True, cost=0.02)]
    assert cost_amplification(clean, attacked) == 1.0


def test_compute_all_performance_metrics():
    clean = [_run(True, cost=0.01, latency=1.0, tool_calls=2)]
    attacked = [_run(False, cost=0.03, latency=3.0, tool_calls=6)]
    metrics = compute_all_performance_metrics(clean, attacked)
    assert metrics["utility_drop"] == 1.0
    assert metrics["cost_amplification"] > 0
    assert metrics["latency_increase"] > 0
    assert metrics["final_output_empty_rate"] == 0.0
    assert metrics["operational_degradation_score"] > 0
