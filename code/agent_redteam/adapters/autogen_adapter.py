"""AutoGen-style synthetic multi-agent adapter."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.synthetic_workflow_base import SyntheticWorkflowRunner, WorkflowLabels
from agent_redteam.defenses.defense_config import DefenseConfig
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
    """AutoGen-style conversation adapter with deterministic fallback."""

    system_name = "autogen_synthetic"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._runner: Optional[SyntheticWorkflowRunner] = None
        self._use_autogen = False

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = config
        suffix = config.get("variant_suffix", "")
        if suffix:
            self.system_name = f"autogen_synthetic_{suffix}"
        else:
            self.system_name = "autogen_synthetic"

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
        # Fallback workflow is always used; AutoGen import enables future real wiring.

        self._runner = SyntheticWorkflowRunner(
            system_name=self.system_name,
            labels=labels,
            seed_prefix="autogen",
            config=config,
        )

    def run_clean(self, task: Task) -> RunResult:
        return self._runner.execute(task, attack=None, defense=None)

    def run_attacked(
        self,
        task: Task,
        attack_variant: AttackVariant,
        defense_config: Optional[DefenseConfig],
    ) -> RunResult:
        return self._runner.execute(task, attack=attack_variant, defense=defense_config)

    def collect_trace(self, run_result: RunResult) -> Trace:
        return run_result.trace

    def teardown(self) -> None:
        self._runner = None
