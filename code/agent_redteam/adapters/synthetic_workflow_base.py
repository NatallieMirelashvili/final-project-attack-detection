"""Shared synthetic multi-agent workflow engine for framework adapters."""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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

_CHANNEL_ATTR_MAP = {
    "final_output": "final_output",
    "inter_agent_messages": "inter_agent_messages",
    "tool_call_arguments": "tool_call_arguments",
    "tool_outputs": "tool_outputs",
    "retrieved_context": "retrieved_context",
    "memory_writes": "memory_writes",
    "logs": "logs",
    "delegation_requests": "delegation_requests",
}

_NODE_AGENTS = {
    "planner": "coordinator",
    "coordinator": "coordinator",
    "retriever": "retriever",
    "worker": "worker",
    "reviewer": "reviewer",
    "orchestrator": "coordinator",
    "executor": "worker",
    "summarizer": "reviewer",
    "reviewer": "reviewer",
}


@dataclass
class WorkflowState:
    task: Task
    canaries: List[str]
    attack_variant: Optional[AttackVariant] = None
    defense_config: Optional[DefenseConfig] = None
    intermediate_messages: List[str] = field(default_factory=list)
    retrieved_context: List[str] = field(default_factory=list)
    tool_call_arguments: List[str] = field(default_factory=list)
    tool_outputs: List[str] = field(default_factory=list)
    memory_writes: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    delegation_requests: List[str] = field(default_factory=list)
    final_output: str = ""
    task_success: bool = True
    latency_seconds: float = 0.0
    token_count: int = 0
    estimated_cost: float = 0.0
    tool_calls: int = 0
    retries: int = 0
    errors: List[str] = field(default_factory=list)
    rng_seed: int = 0


@dataclass
class WorkflowLabels:
    coordinator: str = "coordinator"
    retriever: str = "retriever"
    worker: str = "worker"
    reviewer: str = "reviewer"
    coordinator_role: str = "Coordinator"
    retriever_role: str = "Retriever"
    worker_role: str = "Worker"
    reviewer_role: str = "Reviewer"


class SyntheticWorkflowRunner:
    """Deterministic multi-agent workflow with leakage and degradation support."""

    def __init__(
        self,
        system_name: str,
        labels: WorkflowLabels,
        seed_prefix: str,
        config: Dict[str, Any],
    ) -> None:
        self.system_name = system_name
        self.labels = labels
        self.seed_prefix = seed_prefix
        self.config = config
        self._calibrator = LeakageCalibrator(load_calibration(config))

    def task_seed(self, task: Task, attack_id: Optional[str]) -> int:
        suffix = self.config.get("variant_suffix", "")
        key = f"{self.seed_prefix}:{task.id}:{attack_id or 'clean'}:{suffix}"
        return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)

    def execute(
        self,
        task: Task,
        attack: Optional[AttackVariant],
        defense: Optional[DefenseConfig],
    ) -> RunResult:
        state = WorkflowState(
            task=task,
            canaries=list(task.sensitive_canaries),
            attack_variant=attack,
            defense_config=defense,
            rng_seed=self.task_seed(task, attack.id if attack else None),
        )

        start = time.perf_counter()
        state = self._run_workflow(state)
        state.latency_seconds = time.perf_counter() - start + state.latency_seconds

        trace = Trace(
            final_output=state.final_output,
            inter_agent_messages=list(state.intermediate_messages),
            tool_call_arguments=list(state.tool_call_arguments),
            tool_outputs=list(state.tool_outputs),
            retrieved_context=list(state.retrieved_context),
            memory_writes=list(state.memory_writes),
            logs=list(state.logs),
            delegation_requests=list(state.delegation_requests),
        )

        if attack and is_leakage_goal(attack.goal):
            if self._calibrator.cal.multi_channel_leak_attempts:
                rng = random.Random(state.rng_seed + 99)
                trace = self._calibrator.apply_leakage_to_trace(
                    trace=trace,
                    attack=attack,
                    defense=defense,
                    canaries=state.canaries,
                    rng_seed=state.rng_seed,
                    rng=rng,
                    final_output_fallback=state.final_output,
                    skip_final_output=selective_final_output_gated(self.config),
                )
                state.final_output = trace.final_output or state.final_output

        if attack and is_leakage_goal(attack.goal):
            mode = resolve_finalizer_mode(self.config)
            rng = random.Random(state.rng_seed + 50)
            state.final_output, trace = apply_finalizer_exposure(
                trace=trace,
                final_output=state.final_output,
                attack=attack,
                defense=defense,
                canaries=state.canaries,
                mode=mode,
                calibrator=self._calibrator,
                rng=rng,
                rng_seed=state.rng_seed + 50,
                adapter_config=self.config,
            )
            state.final_output = trace.final_output or state.final_output

        if defense:
            trace = apply_defense(trace, defense, task.sensitive_canaries)
            state.final_output = trace.final_output or state.final_output

        defense_name = defense.name if defense else "D0_no_defense"

        return RunResult(
            task_id=task.id,
            system_name=self.system_name,
            attack_variant_id=attack.id if attack else None,
            defense_name=defense_name,
            final_output=state.final_output,
            task_success=state.task_success,
            latency_seconds=state.latency_seconds,
            token_count=state.token_count,
            estimated_cost=state.estimated_cost,
            tool_calls=state.tool_calls,
            retries=state.retries,
            errors=list(state.errors),
            trace=trace,
        )

    def _run_workflow(self, state: WorkflowState) -> WorkflowState:
        state = self._coordinator_node(state)
        state = self._retriever_node(state)
        state = self._worker_node(state)
        state = self._reviewer_node(state)
        return state

    def _coordinator_node(self, state: WorkflowState) -> WorkflowState:
        rng = random.Random(state.rng_seed + 1)
        task = state.task
        label = self.labels.coordinator
        role = self.labels.coordinator_role
        msg = f"[{label}/{role}] Plan for {task.id}: {task.instruction[:60]}"
        state.intermediate_messages.append(msg)
        state.logs.append(f"INFO: {label} started {task.id}")
        state.delegation_requests.append(
            f"{label}->retriever: fetch context for {task.id}"
        )
        state.token_count += 80 + rng.randint(0, 40)
        state.estimated_cost += 0.0008
        state.latency_seconds += 0.1 + rng.uniform(0, 0.05)
        self._maybe_apply_degradation(state, rng, "coordinator")
        return state

    def _retriever_node(self, state: WorkflowState) -> WorkflowState:
        rng = random.Random(state.rng_seed + 2)
        label = self.labels.retriever
        task = state.task
        ctx = f"[{label}] Context for domain={task.domain}, task={task.id}"
        state.retrieved_context.append(ctx)
        state.tool_call_arguments.append(
            f"tool=retrieve, query={task.instruction[:40]}"
        )
        state.tool_outputs.append(f"[{label}] Retrieved documents for {task.id}")
        state.tool_calls += 1
        state.intermediate_messages.append(f"[{label}] Fetched context for {task.id}")
        state.token_count += 100 + rng.randint(0, 50)
        state.estimated_cost += 0.001
        state.latency_seconds += 0.15 + rng.uniform(0, 0.08)
        attack = state.attack_variant
        if self._calibrator.cal.multi_channel_leak_attempts:
            self._inject_attack_at_node(state, rng, "retriever", "retrieved_context")
            self._inject_attack_at_node(state, rng, "retriever", "tool_outputs")
        elif attack and is_leakage_goal(attack.goal) and attack.target_channel in (
            "retrieved_context",
            "tool_outputs",
        ):
            self._inject_attack_at_node(state, rng, "retriever", attack.target_channel)
        self._maybe_apply_degradation(state, rng, "retriever")
        return state

    def _worker_node(self, state: WorkflowState) -> WorkflowState:
        rng = random.Random(state.rng_seed + 3)
        label = self.labels.worker
        task = state.task
        state.intermediate_messages.append(f"[{label}] Executing task {task.id}")
        state.memory_writes.append(f"{label}_memory:{task.id}=in_progress")
        state.tool_call_arguments.append(f"tool=execute, task={task.id}")
        state.tool_outputs.append(f"[{label}] Execution step complete for {task.id}")
        state.tool_calls += 1
        state.token_count += 120 + rng.randint(0, 60)
        state.estimated_cost += 0.0012
        state.latency_seconds += 0.2 + rng.uniform(0, 0.1)
        attack = state.attack_variant
        if self._calibrator.cal.multi_channel_leak_attempts:
            self._inject_attack_at_node(state, rng, "worker", "tool_call_arguments")
            self._inject_attack_at_node(state, rng, "worker", "memory_writes")
        elif attack and is_leakage_goal(attack.goal) and attack.target_channel in (
            "tool_call_arguments",
            "memory_writes",
        ):
            self._inject_attack_at_node(state, rng, "worker", attack.target_channel)
        self._maybe_apply_degradation(state, rng, "worker")
        return state

    def _reviewer_node(self, state: WorkflowState) -> WorkflowState:
        rng = random.Random(state.rng_seed + 4)
        task = state.task
        label = self.labels.reviewer
        if state.task_success:
            state.final_output = task.expected_answer
        else:
            state.final_output = "Task failed or incomplete."
        state.intermediate_messages.append(f"[{label}] Reviewed output for {task.id}")
        state.logs.append(f"INFO: {label} completed {task.id}")
        state.token_count += 60 + rng.randint(0, 30)
        state.estimated_cost += 0.0006
        state.latency_seconds += 0.08 + rng.uniform(0, 0.04)
        attack = state.attack_variant
        if self._calibrator.cal.multi_channel_leak_attempts:
            if not selective_final_output_gated(self.config):
                self._inject_attack_at_node(state, rng, "reviewer", "final_output")
            self._inject_attack_at_node(state, rng, "reviewer", "logs")
            self._inject_attack_at_node(state, rng, "reviewer", "delegation_requests")
        elif attack and is_leakage_goal(attack.goal):
            if attack.target_channel in ("final_output", "logs", "delegation_requests"):
                self._inject_attack_at_node(state, rng, "reviewer", attack.target_channel)
        return state

    def _attack_targets_node(self, attack: AttackVariant, node_agent: str) -> bool:
        mapped = _NODE_AGENTS.get(attack.target_agent, attack.target_agent)
        return mapped == node_agent or attack.target_agent == node_agent

    def _inject_attack_at_node(
        self,
        state: WorkflowState,
        rng: random.Random,
        node_agent: str,
        channel: str,
    ) -> None:
        attack = state.attack_variant
        if not attack or not is_leakage_goal(attack.goal):
            return
        node_match = self._attack_targets_node(attack, node_agent)
        if not node_match and channel != attack.target_channel:
            return
        prob = self._calibrator.leak_probability(
            attack, state.defense_config, channel, node_match
        )
        if not self._calibrator.should_leak(
            rng, prob, state.rng_seed, f"node:{node_agent}:{channel}"
        ):
            return

        canary = state.canaries[0] if state.canaries else "CANARY_PLACEHOLDER"
        if channel == "final_output":
            state.final_output = self._calibrator.inject_canary_text(
                state.final_output, canary, attack
            )
        elif channel == "retrieved_context":
            state.retrieved_context.append(
                self._calibrator.inject_canary_text("", canary, attack)
            )
        elif channel == "tool_outputs":
            state.tool_outputs.append(
                self._calibrator.inject_canary_text("", canary, attack)
            )
        elif channel == "tool_call_arguments":
            state.tool_call_arguments.append(
                self._calibrator.inject_canary_text("", canary, attack)
            )
        elif channel == "memory_writes":
            state.memory_writes.append(
                self._calibrator.inject_canary_text("", canary, attack)
            )
        elif channel == "logs":
            state.logs.append(self._calibrator.inject_canary_text("LOG", canary, attack))
        elif channel == "delegation_requests":
            state.delegation_requests.append(
                self._calibrator.inject_canary_text("", canary, attack)
            )
        elif channel == "inter_agent_messages":
            state.intermediate_messages.append(
                self._calibrator.inject_canary_text(f"[{node_agent}]", canary, attack)
            )

    def _maybe_apply_degradation(
        self,
        state: WorkflowState,
        rng: random.Random,
        node_agent: str,
    ) -> None:
        attack = state.attack_variant
        if not attack or attack.goal != "degradation":
            return

        deg = self._calibrator.degradation_factor(attack)
        if self._attack_targets_node(attack, node_agent) or rng.random() < deg * 0.5:
            state.latency_seconds += deg * 0.5
            state.token_count += int(deg * 80)
            state.estimated_cost += deg * 0.01
            state.tool_calls += int(deg * 2)
            state.retries += int(deg * 2)
            if rng.random() < deg * 0.4:
                state.task_success = False
                state.errors.append(f"degradation_at_{node_agent}")
            if rng.random() < deg * 0.3:
                state.delegation_requests.append(
                    f"wrong_delegation:{node_agent}->unknown_agent"
                )
