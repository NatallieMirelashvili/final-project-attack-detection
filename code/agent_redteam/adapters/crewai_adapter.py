"""CrewAI-style synthetic multi-agent adapter."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.synthetic_workflow_base import SyntheticWorkflowRunner, WorkflowLabels
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


def _try_import_crewai() -> Optional[Any]:
    try:
        import crewai  # noqa: F401
        return crewai
    except ImportError:
        return None


class CrewAISyntheticAdapter(AgentSystemAdapter):
    """CrewAI-style role-based adapter with deterministic fallback."""

    system_name = "crewai_synthetic"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._runner: Optional[SyntheticWorkflowRunner] = None
        self._use_crewai = False

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = config
        suffix = config.get("variant_suffix", "")
        if suffix:
            self.system_name = f"crewai_synthetic_{suffix}"
        else:
            self.system_name = "crewai_synthetic"

        labels = WorkflowLabels(
            coordinator="CrewManager",
            retriever="ResearchAnalyst",
            worker="TaskExecutor",
            reviewer="QualityReviewer",
            coordinator_role="Crew Manager",
            retriever_role="Research Analyst",
            worker_role="Task Executor",
            reviewer_role="Quality Reviewer",
        )

        crewai = _try_import_crewai()
        self._use_crewai = crewai is not None
        # Fallback workflow is always used; CrewAI import enables future real wiring.

        self._runner = SyntheticWorkflowRunner(
            system_name=self.system_name,
            labels=labels,
            seed_prefix="crewai",
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
