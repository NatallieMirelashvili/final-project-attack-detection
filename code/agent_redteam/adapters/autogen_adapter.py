"""AutoGen-style synthetic multi-agent adapter."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from agent_redteam.adapters.autogen_llm_workflow import run_autogen_llm_workflow
from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.llm_adapter_helpers import execute_llm_workflow
from agent_redteam.adapters.llm_workflow_state import initial_state_llm
from agent_redteam.adapters.synthetic_workflow_base import SyntheticWorkflowRunner, WorkflowLabels
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.llm.base import LLMClient
from agent_redteam.llm.factory import create_llm_client
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


def _try_import_autogen() -> Optional[Any]:
    try:
        import autogen  # noqa: F401
        return autogen
    except ImportError:
        try:
            import pyautogen  # noqa: F401
            return pyautogen
        except ImportError:
            return None


class AutoGenSyntheticAdapter(AgentSystemAdapter):
    """AutoGen-style conversation adapter with synthetic fallback or LLM mode."""

    system_name = "autogen_synthetic"
    adapter_name = "AutoGenSyntheticAdapter"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._runner: Optional[SyntheticWorkflowRunner] = None
        self._llm_client: Optional[LLMClient] = None
        self._use_autogen = False
        self._integration_mode: str = "synthetic_fallback"

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)
        suffix = config.get("variant_suffix", "")
        if suffix:
            self.system_name = f"autogen_synthetic_{suffix}"
        else:
            self.system_name = "autogen_synthetic"

        self._integration_mode = self._resolve_integration_mode()
        if self._integration_mode == "llm":
            self._llm_client = create_llm_client(config)
            self._runner = None
            return

        labels = WorkflowLabels(
            coordinator="UserProxy",
            retriever="RetrieverAgent",
            worker="AssistantAgent",
            reviewer="ReviewerAgent",
            coordinator_role="Coordinator",
            retriever_role="Tool Agent",
            worker_role="Worker Agent",
            reviewer_role="Reviewer Agent",
        )

        autogen = _try_import_autogen()
        self._use_autogen = autogen is not None

        self._runner = SyntheticWorkflowRunner(
            system_name=self.system_name,
            labels=labels,
            seed_prefix="autogen",
            config=config,
        )

    def _resolve_integration_mode(self) -> str:
        mode = str(self._config.get("integration_mode", "synthetic_fallback")).lower().strip()
        if mode == "llm":
            return "llm"
        return "synthetic_fallback"

    def _task_seed(self, task: Task, attack_id: Optional[str]) -> int:
        key = f"{self._config.get('random_seed', 42)}:{task.id}:{attack_id or 'clean'}"
        digest = hashlib.sha256(key.encode()).hexdigest()
        return int(digest[:8], 16)

    def run_clean(self, task: Task) -> RunResult:
        if self._integration_mode == "llm":
            return self._execute_llm(task, attack=None, defense=None)
        assert self._runner is not None
        return self._runner.execute(task, attack=None, defense=None)

    def run_attacked(
        self,
        task: Task,
        attack_variant: AttackVariant,
        defense_config: Optional[DefenseConfig],
    ) -> RunResult:
        if self._integration_mode == "llm":
            return self._execute_llm(task, attack=attack_variant, defense=defense_config)
        assert self._runner is not None
        return self._runner.execute(task, attack=attack_variant, defense=defense_config)

    def _execute_llm(
        self,
        task: Task,
        attack: Optional[AttackVariant],
        defense: Optional[DefenseConfig],
    ) -> RunResult:
        if not self._llm_client:
            raise RuntimeError("AutoGenSyntheticAdapter LLM client not initialized")
        profile = str(self._config.get("calibration_profile", "medium"))
        rng_seed = self._task_seed(task, attack.id if attack else None)
        state = initial_state_llm(task, attack, rng_seed, profile)
        return execute_llm_workflow(
            task=task,
            attack=attack,
            defense=defense,
            state=state,
            llm_client=self._llm_client,
            workflow_fn=run_autogen_llm_workflow,
            system_name=self.system_name,
            integration_mode="llm",
            adapter_config=self._config,
        )

    def collect_trace(self, run_result: RunResult) -> Trace:
        return run_result.trace

    def teardown(self) -> None:
        self._runner = None
        self._llm_client = None
