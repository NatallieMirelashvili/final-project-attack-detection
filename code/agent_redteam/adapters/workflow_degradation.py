"""Shared per-node degradation logic for real and synthetic workflows."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional

from agent_redteam.adapters.calibration import LeakageCalibrator
from agent_redteam.schemas import AttackVariant

_NODE_AGENT_ALIASES: Dict[str, str] = {
    "planner": "coordinator",
    "coordinator": "coordinator",
    "retriever": "retriever",
    "worker": "worker",
    "executor": "worker",
    "tool": "worker",
    "memory": "worker",
    "agentdojo-agent": "coordinator",
    "agentdojo-tool": "worker",
    "agentdojo-env": "worker",
}


def attack_targets_node(attack: AttackVariant, node_agent: str) -> bool:
    mapped = _NODE_AGENT_ALIASES.get(attack.target_agent, attack.target_agent)
    node_mapped = _NODE_AGENT_ALIASES.get(node_agent, node_agent)
    return mapped == node_mapped or attack.target_agent == node_agent


def attack_from_state(state: Dict[str, Any]) -> Optional[AttackVariant]:
    variant_id = state.get("attack_variant_id")
    if not variant_id:
        return None
    return AttackVariant(
        id=str(variant_id),
        goal=state.get("attack_goal", "leakage"),
        prompt_template=str(state.get("attack_prompt_template", "")),
        injection_location=str(state.get("attack_injection_location", "")),
        target_channel=str(state.get("attack_target_channel", "")),
        target_agent=str(state.get("attack_target_agent", "")),
        stealth_level=float(state.get("attack_stealth_level", 0.0)),
    )


def maybe_apply_degradation(
    state: Dict[str, Any],
    attack: AttackVariant | None,
    rng: random.Random,
    node_agent: str,
    calibrator: LeakageCalibrator,
) -> Dict[str, Any]:
    """Apply calibrated degradation effects to workflow state fields."""
    if not attack or attack.goal != "degradation":
        return state

    deg = calibrator.degradation_factor(attack)
    if attack_targets_node(attack, node_agent) or rng.random() < deg * 0.5:
        state["latency_seconds"] = float(state.get("latency_seconds", 0.0)) + deg * 0.5
        state["token_count"] = int(state.get("token_count", 0)) + int(deg * 80)
        state["estimated_cost"] = float(state.get("estimated_cost", 0.0)) + deg * 0.01
        state["tool_calls"] = int(state.get("tool_calls", 0)) + int(deg * 2)
        state["retries"] = int(state.get("retries", 0)) + int(deg * 2)
        if rng.random() < deg * 0.4:
            state["task_success"] = False
            errors = list(state.get("errors") or [])
            errors.append(f"degradation_at_{node_agent}")
            state["errors"] = errors
        if rng.random() < deg * 0.3:
            delegation = list(state.get("delegation_requests") or [])
            delegation.append(f"wrong_delegation:{node_agent}->unknown_agent")
            state["delegation_requests"] = delegation
    return state
