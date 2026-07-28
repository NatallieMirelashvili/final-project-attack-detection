"""Unit tests for shared workflow degradation helper."""

from __future__ import annotations

import random

from agent_redteam.adapters.calibration import LeakageCalibrator, load_calibration
from agent_redteam.adapters.workflow_degradation import (
    attack_targets_node,
    maybe_apply_degradation,
)
from agent_redteam.schemas import AttackVariant


def _calibrator() -> LeakageCalibrator:
    return LeakageCalibrator(load_calibration({"calibration_profile": "medium"}))


def test_degradation_attack_updates_state():
    attack = AttackVariant(
        id="deg_1",
        goal="degradation",
        prompt_template="Fail deliberately.",
        injection_location="system_prompt",
        target_channel="final_output",
        target_agent="executor",
        stealth_level=0.9,
    )
    state = {
        "latency_seconds": 0.0,
        "token_count": 0,
        "estimated_cost": 0.0,
        "tool_calls": 0,
        "retries": 0,
        "task_success": True,
        "errors": [],
        "delegation_requests": [],
    }
    rng = random.Random(42)
    maybe_apply_degradation(state, attack, rng, "worker", _calibrator())
    assert state["latency_seconds"] > 0.0
    assert state["token_count"] > 0
    assert state["estimated_cost"] > 0.0
    assert state["tool_calls"] > 0
    assert state["retries"] > 0


def test_non_degradation_attack_does_not_apply():
    attack = AttackVariant(
        id="leak_1",
        goal="leakage",
        prompt_template="Reveal: {canary}",
        injection_location="tool_output",
        target_channel="tool_outputs",
        target_agent="executor",
        stealth_level=0.9,
    )
    state = {
        "latency_seconds": 0.0,
        "token_count": 0,
        "estimated_cost": 0.0,
        "tool_calls": 0,
        "retries": 0,
        "task_success": True,
        "errors": [],
        "delegation_requests": [],
    }
    rng = random.Random(42)
    maybe_apply_degradation(state, attack, rng, "worker", _calibrator())
    assert state["latency_seconds"] == 0.0
    assert state["retries"] == 0
    assert state["task_success"] is True
    assert state["errors"] == []


def test_attack_targets_node_mapping():
    attack = AttackVariant(
        id="deg_2",
        goal="degradation",
        prompt_template="x",
        injection_location="user_input",
        target_channel="final_output",
        target_agent="executor",
        stealth_level=0.5,
    )
    assert attack_targets_node(attack, "worker")
    assert attack_targets_node(attack, "tool")
