"""Tests for leakage metrics."""

from agent_redteam.data.canaries import CANARY_CLIENT_ID_042
from agent_redteam.evaluation.leakage_metrics import (
    attach_canaries,
    channel_breakdown,
    final_output_leakage_rate,
    internal_leakage_rate,
    leakage_asr,
    total_exposure_rate,
)
from agent_redteam.schemas import RunResult, Trace


def _make_run(task_id: str, output: str, internal: list[str], attacked: bool = True):
    trace = Trace(
        final_output=output,
        inter_agent_messages=internal,
    )
    return RunResult(
        task_id=task_id,
        system_name="mock",
        attack_variant_id="atk_001" if attacked else None,
        defense_name="D0",
        final_output=output,
        task_success=True,
        latency_seconds=1.0,
        token_count=100,
        estimated_cost=0.01,
        tool_calls=2,
        retries=0,
        errors=[],
        trace=trace,
    )


def _tasks_map():
    return {
        "task_000": type("T", (), {"sensitive_canaries": [CANARY_CLIENT_ID_042]})(),
    }


def test_leakage_asr():
    runs = [
        _make_run("task_000", f"leaked {CANARY_CLIENT_ID_042}", []),
        _make_run("task_000", "clean output", []),
    ]
    tasks_map = _tasks_map()
    rate = leakage_asr(runs, tasks_map)
    assert rate == 0.5


def test_internal_leakage_rate():
    runs = [
        _make_run("task_000", "clean", [f"internal {CANARY_CLIENT_ID_042}"]),
    ]
    rate = internal_leakage_rate(runs, _tasks_map())
    assert rate == 1.0


def test_final_output_leakage_rate():
    runs = [
        _make_run("task_000", f"out {CANARY_CLIENT_ID_042}", []),
    ]
    rate = final_output_leakage_rate(runs, _tasks_map())
    assert rate == 1.0


def test_channel_breakdown():
    runs = [
        _make_run("task_000", f"out {CANARY_CLIENT_ID_042}", ["clean"]),
    ]
    breakdown = channel_breakdown(runs, _tasks_map())
    assert breakdown["final_output"] == 1.0
    assert breakdown["inter_agent_messages"] == 0.0


def test_total_exposure_rate():
    runs = [_make_run("task_000", f"{CANARY_CLIENT_ID_042}", [])]
    assert total_exposure_rate(runs, _tasks_map()) == 1.0
