"""Real LangGraph adapter using an actual LangGraph StateGraph workflow."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional

from agent_redteam.adapters.agent_runner import grade_task_success
from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.calibration import LeakageCalibrator, load_calibration
from agent_redteam.adapters.langgraph_llm_workflow import (
    build_langgraph_llm_workflow,
    initial_state_llm,
)
from agent_redteam.adapters.langgraph_real_workflow import (
    _LANGGRAPH_IMPORT_ERROR,
    build_langgraph_workflow,
    initial_state,
    injected_channel_from_state,
    try_import_langgraph,
)
from agent_redteam.defenses.filters import apply_defense
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.llm.factory import create_llm_client
from agent_redteam.llm.base import LLMClient
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


class LangGraphRealAdapter(AgentSystemAdapter):
    """Runs a real LangGraph workflow; final output is the graph's final node response."""

    system_name = "langgraph_real"
    adapter_name = "LangGraphRealAdapter"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._graph: Any = None
        self._calibrator: LeakageCalibrator = LeakageCalibrator(load_calibration({}))
        self._llm_client: Optional[LLMClient] = None
        self._integration_mode: str = "controlled"

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)
        try_import_langgraph()
        self._integration_mode = self._resolve_integration_mode()
        if self._integration_mode == "llm":
            self._llm_client = create_llm_client(config)
            self._graph = build_langgraph_llm_workflow(self._llm_client)
        else:
            self._calibrator = LeakageCalibrator(load_calibration(config))
            self._graph = build_langgraph_workflow(self._calibrator)
        self.system_name = "langgraph_real"

    def _resolve_integration_mode(self) -> str:
        mode = str(self._config.get("integration_mode", "controlled")).lower().strip()
        if mode in ("real", "controlled"):
            return "controlled"
        if mode == "llm":
            return "llm"
        return mode

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
        self._graph = None
        self._llm_client = None

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
        if not self._graph:
            raise RuntimeError("LangGraphRealAdapter.setup() must be called before running tasks")

        rng_seed = self._task_seed(task, attack.id if attack else None)
        profile = str(self._config.get("calibration_profile", "medium"))
        if self._integration_mode == "llm":
            state = initial_state_llm(task, attack, rng_seed, profile)
        else:
            state = initial_state(task, attack, rng_seed, profile)

        start = time.perf_counter()
        result = self._graph.invoke(state)
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
                "integration_mode": self._integration_mode,
            },
        )

        if defense:
            trace = apply_defense(trace, defense, task.sensitive_canaries)
            final_output = trace.final_output or final_output

        if self._integration_mode == "llm":
            task_success = grade_task_success(
                final_output,
                task.expected_answer,
                task=task,
                adapter_config=self._config,
            )
        elif attack is None:
            task_success = grade_task_success(final_output, task.expected_answer)
        else:
            task_success = bool(result.get("task_success", True))

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
            retries=int(result.get("retries", 0)),
            errors=list(result.get("errors") or []),
            trace=trace,
        )


def langgraph_import_error_message() -> str:
    return _LANGGRAPH_IMPORT_ERROR
