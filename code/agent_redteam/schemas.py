"""Core dataclass schemas for agent red-team experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class Task:
    id: str
    domain: str
    instruction: str
    sensitive_canaries: List[str]
    expected_answer: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttackVariant:
    id: str
    goal: Literal["leakage", "degradation", "external_leakage"]
    prompt_template: str
    injection_location: str
    target_channel: str
    target_agent: str
    stealth_level: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    final_output: str = ""
    inter_agent_messages: List[str] = field(default_factory=list)
    tool_call_arguments: List[str] = field(default_factory=list)
    tool_outputs: List[str] = field(default_factory=list)
    retrieved_context: List[str] = field(default_factory=list)
    memory_writes: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    delegation_requests: List[str] = field(default_factory=list)
    injection_metadata: Dict[str, Any] = field(default_factory=dict)

    # Pre-defense snapshots for measuring defense effectiveness
    pre_defense_final_output: str = ""
    pre_defense_inter_agent_messages: List[str] = field(default_factory=list)
    pre_defense_tool_outputs: List[str] = field(default_factory=list)
    pre_defense_memory_writes: List[str] = field(default_factory=list)


@dataclass
class RunResult:
    task_id: str
    system_name: str
    attack_variant_id: Optional[str]
    defense_name: str
    final_output: str
    task_success: bool
    latency_seconds: float
    token_count: int
    estimated_cost: float
    tool_calls: int
    retries: int
    errors: List[str]
    trace: Trace


@dataclass
class ExperimentConfig:
    experiment_name: str
    system_name: str
    goal: Literal["leakage", "degradation", "external_leakage"]
    num_iterations: int
    num_tasks: int
    attack_generator: str
    defense: str
    scoring_weights: Dict[str, float]
    output_dir: str
    random_seed: int
    adapter_type: str = "mock"
    adapter_config: Dict[str, Any] = field(default_factory=dict)
    attack_generator_version: str = "v1"
    reward_profile: str = ""
