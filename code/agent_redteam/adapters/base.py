"""Abstract base class for agent system adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from agent_redteam.schemas import AttackVariant, RunResult, Task, Trace


class AgentSystemAdapter(ABC):
    system_name: str

    @abstractmethod
    def setup(self, config: Dict[str, Any]) -> None:
        """Initialize the adapter with configuration."""

    @abstractmethod
    def run_clean(self, task: Task) -> RunResult:
        """Run a task without any attack."""

    @abstractmethod
    def run_attacked(
        self,
        task: Task,
        attack_variant: AttackVariant,
        defense_config: Optional[Any],
    ) -> RunResult:
        """Run a task under attack with optional defense."""

    @abstractmethod
    def collect_trace(self, run_result: RunResult) -> Trace:
        """Extract trace from a run result."""

    @abstractmethod
    def teardown(self) -> None:
        """Clean up adapter resources."""
