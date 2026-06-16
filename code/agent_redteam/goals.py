"""Goal classification helpers."""

from __future__ import annotations

LEAKAGE_GOALS = frozenset({"leakage", "external_leakage"})


def is_leakage_goal(goal: str) -> bool:
    return goal in LEAKAGE_GOALS


def is_external_leakage_goal(goal: str) -> bool:
    return goal == "external_leakage"
