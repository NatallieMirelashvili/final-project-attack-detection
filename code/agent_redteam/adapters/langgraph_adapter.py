"""LangGraph-based synthetic multi-agent workflow adapter."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agent_redteam.adapters.base import AgentSystemAdapter
from agent_redteam.adapters.synthetic_workflow_base import (
    SyntheticWorkflowRunner,
    WorkflowLabels,
)
from agent_redteam.defenses.defense_config import DefenseConfig
from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


def _try_import_langgraph() -> Optional[Any]:
    try:
        from langgraph.graph import END, StateGraph  # noqa: F401
        return True
    except ImportError:
        return None


class LangGraphSyntheticAdapter(AgentSystemAdapter):
    """Multi-agent workflow adapter with LangGraph or deterministic fallback."""

    system_name = "langgraph_synthetic"

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._runner: Optional[SyntheticWorkflowRunner] = None
        self._use_langgraph = False

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = config
        suffix = config.get("variant_suffix", "")
        if suffix:
            self.system_name = f"langgraph_synthetic_{suffix}"
        else:
            self.system_name = "langgraph_synthetic"

        self._use_langgraph = _try_import_langgraph() is not None

        labels = WorkflowLabels(
            coordinator="planner",
            retriever="retriever",
            worker="worker",
            reviewer="reviewer",
            coordinator_role="Planner",
            retriever_role="Retriever",
            worker_role="Worker",
            reviewer_role="Reviewer",
        )
        self._runner = SyntheticWorkflowRunner(
            system_name=self.system_name,
            labels=labels,
            seed_prefix="lg",
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
