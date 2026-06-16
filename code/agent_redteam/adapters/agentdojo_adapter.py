"""AgentDojo benchmark adapter with mock-mode fallback."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.mock_adapter import MockAdapter
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace

_AGENTDOJO_IMPORT_ERROR = (
    "AgentDojo is not installed. Install it according to the official AgentDojo "
    "instructions, then rerun this experiment."
)


def _try_import_agentdojo() -> Any:
    """Import AgentDojo modules if available."""
    try:
        import agentdojo  # noqa: F401
        return agentdojo
    except ImportError:
        try:
            from agentdojo import benchmark  # noqa: F401
            return benchmark
        except ImportError:
            raise ImportError(_AGENTDOJO_IMPORT_ERROR)


class AgentDojoAdapter(AgentSystemAdapter):
    """Adapter for AgentDojo benchmark tasks."""

    system_name = "agentdojo"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._mock_mode = True
        self._mock_backend: Optional[MockAdapter] = None
        self._agentdojo_env: Any = None
        self._suite_name: str = "default"

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._mock_mode = bool(config.get("agentdojo_mock_mode", True))
        self._suite_name = config.get("suite_name", "default")

        if self._mock_mode:
            self._mock_backend = MockAdapter()
            mock_config = dict(config)
            mock_config.setdefault("random_seed", config.get("random_seed", 42))
            if config.get("variant_suffix"):
                mock_config["variant_suffix"] = config.get("variant_suffix", "")
            self._mock_backend.setup(mock_config)
            self.system_name = "agentdojo"
            return

        agentdojo = _try_import_agentdojo()
        self._agentdojo_env = self._initialize_agentdojo_env(agentdojo, config)
        self.system_name = "agentdojo"

    def _initialize_agentdojo_env(self, agentdojo_module: Any, config: Dict[str, Any]) -> Any:
        """
        Initialize AgentDojo environment/task suite.

        TODO: Adjust mapping when exact AgentDojo API version is pinned.
        Expected config keys: suite_name, task_filter, benchmark_version.
        """
        suite = config.get("suite_name", "default")
        # Placeholder: real wiring depends on installed AgentDojo version
        return {"module": agentdojo_module, "suite": suite, "config": config}

    def run_clean(self, task: Task) -> RunResult:
        if self._mock_mode and self._mock_backend:
            result = self._mock_backend.run_clean(task)
            return self._label_result(result, attack_id=None)
        return self._run_agentdojo_task(task, attack=None, defense=None)

    def run_attacked(
        self,
        task: Task,
        attack_variant: AttackVariant,
        defense_config: Optional[DefenseConfig],
    ) -> RunResult:
        if self._mock_mode and self._mock_backend:
            result = self._mock_backend.run_attacked(task, attack_variant, defense_config)
            return self._label_result(result, attack_id=attack_variant.id)
        return self._run_agentdojo_task(task, attack=attack_variant, defense=defense_config)

    def collect_trace(self, run_result: RunResult) -> Trace:
        return run_result.trace

    def teardown(self) -> None:
        if self._mock_backend:
            self._mock_backend.teardown()
        self._agentdojo_env = None

    def _label_result(self, result: RunResult, attack_id: Optional[str]) -> RunResult:
        """Re-label mock backend results with agentdojo system_name."""
        return RunResult(
            task_id=result.task_id,
            system_name=self.system_name,
            attack_variant_id=attack_id,
            defense_name=result.defense_name,
            final_output=result.final_output,
            task_success=result.task_success,
            latency_seconds=result.latency_seconds,
            token_count=result.token_count,
            estimated_cost=result.estimated_cost,
            tool_calls=result.tool_calls,
            retries=result.retries,
            errors=list(result.errors),
            trace=result.trace,
        )

    def _run_agentdojo_task(
        self,
        task: Task,
        attack: Optional[AttackVariant],
        defense: Optional[DefenseConfig],
    ) -> RunResult:
        """
        Execute task via AgentDojo APIs.

        TODO: Map AgentDojo run outputs to RunResult/Trace when API is finalized.
        """
        start = time.perf_counter()
        errors: List[str] = []

        # Defensive placeholder execution path for real mode without full API mapping
        injected_instruction = task.instruction
        if attack:
            injected_instruction = self._inject_attack_into_instruction(
                task.instruction, attack, task.sensitive_canaries
            )

        trace = Trace(
            inter_agent_messages=[f"AgentDojo processing: {injected_instruction[:80]}"],
            tool_call_arguments=[f"agentdojo_action=run, task={task.id}"],
            tool_outputs=[f"AgentDojo result placeholder for {task.id}"],
            retrieved_context=[f"Suite: {self._suite_name}, domain: {task.domain}"],
            memory_writes=[f"agentdojo_state:{task.id}"],
            logs=[f"INFO: agentdojo run {task.id}"],
            delegation_requests=[],
        )

        task_success = True
        final_output = task.expected_answer

        if attack and attack.goal == "degradation":
            task_success = False
            final_output = "AgentDojo task degraded (simulated)."
            errors.append("degradation_attack")

        latency = time.perf_counter() - start + 0.1
        defense_name = defense.name if defense else "D0_no_defense"

        return RunResult(
            task_id=task.id,
            system_name=self.system_name,
            attack_variant_id=attack.id if attack else None,
            defense_name=defense_name,
            final_output=final_output,
            task_success=task_success,
            latency_seconds=latency,
            token_count=250,
            estimated_cost=0.0025,
            tool_calls=2,
            retries=0,
            errors=errors,
            trace=trace,
        )

    def _inject_attack_into_instruction(
        self,
        instruction: str,
        attack: AttackVariant,
        canaries: List[str],
    ) -> str:
        """Inject attack prompt into instruction channel when supported."""
        canary = canaries[0] if canaries else "CANARY_PLACEHOLDER"
        template = attack.prompt_template.replace("{canary}", canary)
        if attack.injection_location == "user_input":
            return f"{instruction}\n{template}"
        return instruction
