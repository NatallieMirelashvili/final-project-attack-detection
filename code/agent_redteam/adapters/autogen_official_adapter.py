"""Official AutoGen adapter using autogen-agentchat runtime APIs."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from agent_redteam.adapters.autogen_official_workflow import run_autogen_official_workflow
from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.llm_adapter_helpers import execute_llm_workflow
from agent_redteam.adapters.llm_workflow_state import initial_state_llm
from agent_redteam.adapters.official_runtime import configure_official_runtime_env, try_import_autogen_official
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


class AutoGenOfficialAdapter(AgentSystemAdapter):
    """Runs official AutoGen RoundRobinGroupChat; never routes to style-compatible workflow."""

    system_name = "autogen_official"
    adapter_name = "AutoGenOfficialAdapter"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._integration_mode: str = "llm"

    def setup(self, config: Dict[str, Any]) -> None:
        configure_official_runtime_env()
        self._config = dict(config)
        try_import_autogen_official()
        self._integration_mode = self._resolve_integration_mode()
        if self._integration_mode != "llm":
            raise ValueError(
                "AutoGenOfficialAdapter only supports integration_mode: llm "
                "(official AutoGen runtime)."
            )
        self.system_name = "autogen_official"

    def _resolve_integration_mode(self) -> str:
        mode = str(self._config.get("integration_mode", "llm")).lower().strip()
        if mode != "llm":
            raise ValueError("autogen_official requires integration_mode: llm")
        return "llm"

    def _task_seed(self, task: Task, attack_id: Optional[str]) -> int:
        key = f"{self._config.get('random_seed', 42)}:{task.id}:{attack_id or 'clean'}"
        digest = hashlib.sha256(key.encode()).hexdigest()
        return int(digest[:8], 16)

    def run_clean(self, task: Task) -> RunResult:
        return self._execute(task, attack=None, defense=None)

    def run_attacked(
        self,
        task: Task,
        attack_variant: AttackVariant,
        defense_config: Optional[DefenseConfig],
    ) -> RunResult:
        return self._execute(task, attack=attack_variant, defense=defense_config)

    def _execute(
        self,
        task: Task,
        attack: Optional[AttackVariant],
        defense: Optional[DefenseConfig],
    ) -> RunResult:
        profile = str(self._config.get("calibration_profile", "medium"))
        rng_seed = self._task_seed(task, attack.id if attack else None)
        state = initial_state_llm(task, attack, rng_seed, profile)

        def _workflow(state_in, _unused=None):
            return run_autogen_official_workflow(state_in, self._config)

        return execute_llm_workflow(
            task=task,
            attack=attack,
            defense=defense,
            state=state,
            llm_client=None,  # type: ignore[arg-type]
            workflow_fn=_workflow,
            system_name=self.system_name,
            integration_mode="llm",
            adapter_config=self._config,
        )

    def collect_trace(self, run_result: RunResult) -> Trace:
        return run_result.trace

    def teardown(self) -> None:
        return None
