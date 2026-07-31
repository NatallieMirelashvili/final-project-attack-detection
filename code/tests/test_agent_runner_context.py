"""Tests for shared LLM agent runner context handling and final answer resolution."""

from __future__ import annotations

from agent_redteam.adapters.agent_runner import (
    _truncate_context,
    grade_task_success,
    resolve_final_answer_from_state,
)
from agent_redteam.data.synthetic_tasks import generate_synthetic_tasks
from agent_redteam.evaluation.task_grading import grade_task_success_live


def test_truncate_context_shortens_long_messages():
    text = "a" * 1000
    truncated = _truncate_context(text, max_chars=100)
    assert len(truncated) == 100
    assert truncated.endswith("...")


def test_resolve_final_answer_prefers_finalizer_text():
    state = {
        "inter_agent_messages": [
            "[planner] plan text",
            "[finalizer] Quarterly report summary for leadership.",
        ],
        "final_answer": "",
    }
    assert (
        resolve_final_answer_from_state(state, "")
        == "Quarterly report summary for leadership."
    )


def test_resolve_final_answer_falls_back_to_last_agent_message():
    state = {
        "inter_agent_messages": [
            "[planner] Short quarterly report summary with revenue and expenses.",
        ],
        "final_answer": "",
    }
    resolved = resolve_final_answer_from_state(state, "")
    assert "quarterly report summary" in resolved.lower()


def test_live_grader_accepts_natural_langgraph_style_output():
    tasks = generate_synthetic_tasks(1, 42)
    task = tasks[0]
    output = (
        "Quarterly report summary for leadership: revenue grew 12% and operating "
        "expenses declined this quarter."
    )
    assert grade_task_success_live(output, task)
    assert grade_task_success(
        output,
        task.expected_answer,
        task=task,
        adapter_config={"llm_mode": "live"},
    )


def test_strict_grader_still_used_for_mock_mode():
    tasks = generate_synthetic_tasks(1, 42)
    task = tasks[0]
    natural = "Quarterly report summary for leadership with revenue growth."
    strict_answer = task.expected_answer
    assert not grade_task_success(
        natural,
        strict_answer,
        task=task,
        adapter_config={"llm_mode": "mock"},
    )
    mock_output = f"Final response: {strict_answer}"
    assert grade_task_success(
        mock_output,
        strict_answer,
        task=task,
        adapter_config={"llm_mode": "mock"},
    )
