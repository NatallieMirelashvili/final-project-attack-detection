"""Deterministic mock adapter for local red-team simulation."""

from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List, Optional

from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.calibration import LeakageCalibrator, load_calibration
from agent_redteam.adapters.finalizer_exposure import (
    apply_finalizer_exposure,
    resolve_finalizer_mode,
    selective_final_output_gated,
)
from agent_redteam.goals import is_leakage_goal
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.defenses.filters import apply_defense
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


class MockAdapter(AgentSystemAdapter):
    system_name = "mock"

    def __init__(self) -> None:
        self._rng: random.Random = random.Random(42)
        self._config: Dict[str, Any] = {}
        self._variant_suffix: str = ""
        self._calibrator: LeakageCalibrator = LeakageCalibrator(load_calibration({}))

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = config
        seed = config.get("random_seed", 42)
        self._rng = random.Random(seed)
        self._variant_suffix = config.get("variant_suffix", "")
        self._calibrator = LeakageCalibrator(load_calibration(config))
        if self._variant_suffix:
            self.system_name = f"mock_{self._variant_suffix}"
        else:
            self.system_name = "mock"

    def run_clean(self, task: Task) -> RunResult:
        return self._simulate_run(task, attack=None, defense=None)

    def run_attacked(
        self,
        task: Task,
        attack_variant: AttackVariant,
        defense_config: Optional[DefenseConfig],
    ) -> RunResult:
        return self._simulate_run(task, attack=attack_variant, defense=defense_config)

    def collect_trace(self, run_result: RunResult) -> Trace:
        return run_result.trace

    def teardown(self) -> None:
        pass

    def _task_seed(self, task: Task, attack_id: Optional[str]) -> int:
        key = f"{task.id}:{attack_id or 'clean'}:{self._variant_suffix}"
        return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)

    def _simulate_run(
        self,
        task: Task,
        attack: Optional[AttackVariant],
        defense: Optional[DefenseConfig],
    ) -> RunResult:
        rng = random.Random(self._task_seed(task, attack.id if attack else None))
        seed = self._task_seed(task, attack.id if attack else None)
        defense_name = defense.name if defense else "D0_no_defense"
        calibrator = self._calibrator

        latency = 0.5 + rng.uniform(0, 0.3)
        tokens = 200 + rng.randint(0, 100)
        cost = tokens * 0.00001
        tool_calls = 2 + rng.randint(0, 2)
        retries = 0
        errors: List[str] = []
        success_prob = 0.85

        if attack and attack.goal == "degradation":
            deg_factor = calibrator.degradation_factor(attack)
            success_prob -= deg_factor * 0.6
            latency += deg_factor * 2.0
            tokens += int(deg_factor * 500)
            cost += deg_factor * 0.05
            tool_calls += int(deg_factor * 5)
            retries += int(deg_factor * 3)
            if rng.random() < deg_factor * 0.3:
                errors.append("simulated_failure")

        task_success = rng.random() < max(0.1, success_prob)
        final_output = task.expected_answer if task_success else "Task failed or incomplete."

        trace = Trace(
            inter_agent_messages=[f"Agent processing: {task.instruction[:50]}"],
            tool_call_arguments=[f"action=process, task={task.id}"],
            tool_outputs=[f"Processed task {task.id} successfully."],
            retrieved_context=[f"Context for domain: {task.domain}"],
            memory_writes=[f"Stored task state for {task.id}"],
            logs=[f"INFO: run started for {task.id}"],
            delegation_requests=[f"Delegate summarization for {task.id}"],
        )

        if attack and is_leakage_goal(attack.goal):
            trace = calibrator.apply_leakage_to_trace(
                trace=trace,
                attack=attack,
                defense=defense,
                canaries=task.sensitive_canaries,
                rng_seed=seed,
                rng=rng,
                final_output_fallback=final_output,
                skip_final_output=selective_final_output_gated(self._config),
            )
            if trace.final_output:
                final_output = trace.final_output
            elif attack.target_channel == "final_output" and not selective_final_output_gated(
                self._config
            ):
                prob = calibrator.leak_probability(attack, defense, "final_output")
                if calibrator.should_leak(rng, prob, seed, "final_output_extra"):
                    canary = task.sensitive_canaries[0]
                    final_output = calibrator.inject_canary_text(final_output, canary, attack)
                    trace.final_output = final_output

        trace.final_output = trace.final_output or final_output

        if attack and is_leakage_goal(attack.goal):
            mode = resolve_finalizer_mode(self._config)
            final_output, trace = apply_finalizer_exposure(
                trace=trace,
                final_output=final_output,
                attack=attack,
                defense=defense,
                canaries=task.sensitive_canaries,
                mode=mode,
                calibrator=calibrator,
                rng=rng,
                rng_seed=seed,
                adapter_config=self._config,
            )

        trace.final_output = trace.final_output or final_output

        if defense:
            trace = apply_defense(trace, defense, task.sensitive_canaries)
            final_output = trace.final_output or final_output

        return RunResult(
            task_id=task.id,
            system_name=self.system_name,
            attack_variant_id=attack.id if attack else None,
            defense_name=defense_name,
            final_output=final_output,
            task_success=task_success,
            latency_seconds=latency,
            token_count=tokens,
            estimated_cost=cost,
            tool_calls=tool_calls,
            retries=retries,
            errors=errors,
            trace=trace,
        )
