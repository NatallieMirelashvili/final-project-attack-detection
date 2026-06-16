"""Real AgentDojo adapter using controlled local benchmark execution when installed."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional

from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.agentdojo_real_workflow import (
    _AGENTDOJO_REAL_IMPORT_ERROR,
    initial_state,
    injected_channel_from_state,
    run_agentdojo_real_workflow,
    try_import_agentdojo,
)
from agent_redteam.defenses.filters import apply_defense
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


class AgentDojoRealAdapter(AgentSystemAdapter):
    """Runs controlled AgentDojo-compatible tasks; final output is the agent's final answer only."""

    system_name = "agentdojo_real"
    adapter_name = "AgentDojoRealAdapter"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._agentdojo_module: Any = None

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)
        self._agentdojo_module = try_import_agentdojo()
        self.system_name = "agentdojo_real"

    def run_clean(self, task: Task) -> RunResult:
        return self._execute(task, attack=None, defense=None)

    def run_attacked(
        self,
        task: Task,
        attack_variant: AttackVariant,
        defense_config: Optional[DefenseConfig],
    ) -> RunResult:
        return self._execute(task, attack=attack_variant, defense=defense_config)

    def collect_trace(self, run_result: RunResult) -> Trace:
        return run_result.trace

    def teardown(self) -> None:
        self._agentdojo_module = None

    def _task_seed(self, task: Task, attack_id: Optional[str]) -> int:
        key = f"{self._config.get('random_seed', 42)}:{task.id}:{attack_id or 'clean'}"
        digest = hashlib.sha256(key.encode()).hexdigest()
        return int(digest[:8], 16)

    def _execute(
        self,
        task: Task,
        attack: Optional[AttackVariant],
        defense: Optional[DefenseConfig],
    ) -> RunResult:
        profile = str(self._config.get("calibration_profile", "medium"))
        rng_seed = self._task_seed(task, attack.id if attack else None)
        state = initial_state(task, attack, rng_seed, profile)

        start = time.perf_counter()
        result = run_agentdojo_real_workflow(state)
        elapsed = time.perf_counter() - start

        final_output = str(result.get("final_answer", ""))
        injected_by_channel = dict(result.get("injected_texts_by_channel") or {})
        injected_canary = ""
        injected_channel = ""
        injection_location = ""
        if attack:
            injection_location = attack.injection_location
            injected_channel = injected_channel_from_state(result) or ""
            if task.sensitive_canaries:
                injected_canary = task.sensitive_canaries[0]

        trace = Trace(
            final_output=final_output,
            inter_agent_messages=list(result.get("inter_agent_messages") or []),
            tool_call_arguments=list(result.get("tool_call_arguments") or []),
            tool_outputs=list(result.get("tool_outputs") or []),
            retrieved_context=list(result.get("retrieved_context") or []),
            memory_writes=list(result.get("memory_writes") or []),
            logs=list(result.get("logs") or []),
            delegation_requests=list(result.get("delegation_requests") or []),
            injection_metadata={
                "injection_location": injection_location,
                "injected_channel": injected_channel,
                "injected_canary": injected_canary,
                "injection_variant_id": attack.id if attack else "",
                "injected_texts_by_channel": injected_by_channel,
            },
        )

        if defense:
            trace = apply_defense(trace, defense, task.sensitive_canaries)
            final_output = trace.final_output or final_output

        task_success = bool(task.expected_answer) and task.expected_answer in final_output

        return RunResult(
            task_id=task.id,
            system_name=self.system_name,
            attack_variant_id=attack.id if attack else None,
            defense_name=defense.name if defense else "D0_no_defense",
            final_output=final_output,
            task_success=task_success,
            latency_seconds=float(result.get("latency_seconds", 0.0)) + elapsed,
            token_count=int(result.get("token_count", 0)),
            estimated_cost=float(result.get("estimated_cost", 0.0)),
            tool_calls=int(result.get("tool_calls", 0)),
            retries=0,
            errors=[],
            trace=trace,
        )


def agentdojo_import_error_message() -> str:
    return _AGENTDOJO_REAL_IMPORT_ERROR
