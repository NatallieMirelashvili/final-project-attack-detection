"""Experiment metadata helpers for metrics summaries and tables."""

from __future__ import annotations

from typing import Any, Dict, List

from agent_redteam.adapters.finalizer_exposure import resolve_finalizer_mode
from agent_redteam.schemas import ExperimentConfig

SYSTEM_ARCHITECTURE: Dict[str, str] = {
    "mock": "single_agent_mock",
    "agentdojo": "benchmark_suite",
    "agentdojo_real": "benchmark_suite",
    "langgraph_synthetic": "graph_workflow",
    "langgraph_real": "graph_workflow",
    "autogen_synthetic": "conversation",
    "autogen_official": "conversation_official",
    "crewai_synthetic": "role_based",
    "crewai_official": "role_based_official",
}

ADAPTER_CLASS_NAMES: Dict[str, str] = {
    "mock": "MockAdapter",
    "agentdojo": "AgentDojoAdapter",
    "agentdojo_real": "AgentDojoRealAdapter",
    "langgraph_synthetic": "LangGraphSyntheticAdapter",
    "langgraph_real": "LangGraphRealAdapter",
    "langgraph": "LangGraphSyntheticAdapter",
    "autogen_synthetic": "AutoGenSyntheticAdapter",
    "autogen_official": "AutoGenOfficialAdapter",
    "autogen_real": "AutoGenOfficialAdapter",
    "crewai_synthetic": "CrewAISyntheticAdapter",
    "crewai_official": "CrewAIOfficialAdapter",
    "crewai_real": "CrewAIOfficialAdapter",
}


def infer_architecture(system_name: str) -> str:
    for key, arch in SYSTEM_ARCHITECTURE.items():
        if system_name == key or system_name.startswith(key):
            return arch
    return "unknown"


def resolve_integration_mode(
    system_name: str,
    adapter_type: str,
    adapter_config: Dict[str, Any],
) -> str:
    """Resolve integration mode: mock, synthetic_fallback, controlled, llm, or real (legacy)."""
    adapter_type = (adapter_type or system_name or "mock").lower()
    system_name = system_name or adapter_type

    explicit = adapter_config.get("integration_mode")
    if explicit in ("mock", "synthetic_fallback", "controlled", "llm"):
        return str(explicit)
    if explicit == "real":
        if adapter_type in ("langgraph_real", "agentdojo_real") or system_name in (
            "langgraph_real",
            "agentdojo_real",
        ):
            return "controlled"
        return "real"

    if adapter_type == "mock" or system_name == "mock":
        return "mock"

    if adapter_type == "agentdojo" or system_name == "agentdojo":
        if adapter_config.get("agentdojo_mock_mode", True):
            return "mock"
        return "real"

    synthetic_types = {
        "langgraph_synthetic",
        "langgraph",
        "autogen_synthetic",
        "autogen",
        "crewai_synthetic",
        "crewai",
    }
    if adapter_type in ("langgraph_real", "agentdojo_real") or system_name in (
        "langgraph_real",
        "agentdojo_real",
    ):
        return "controlled"

    if adapter_type in synthetic_types or any(
        system_name.startswith(s) for s in ("langgraph_synthetic", "autogen_synthetic", "crewai_synthetic")
    ):
        if adapter_config.get("use_real_framework", False):
            return "real"
        return "synthetic_fallback"

    return "synthetic_fallback"


def resolve_final_output_source(integration_mode: str) -> str:
    if integration_mode == "llm":
        return "llm_agent_response"
    if integration_mode == "real":
        return "real_framework_response"
    if integration_mode == "controlled":
        return "real_framework_response"
    return "synthetic_finalizer"


def resolve_adapter_name(adapter_type: str, system_name: str) -> str:
    key = (adapter_type or system_name or "mock").lower()
    if key in ADAPTER_CLASS_NAMES:
        return ADAPTER_CLASS_NAMES[key]
    for prefix, name in ADAPTER_CLASS_NAMES.items():
        if key.startswith(prefix):
            return name
    return "MockAdapter"


def resolve_finalizer_exposure_for_metrics(
    integration_mode: str,
    adapter_config: Dict[str, Any],
) -> str:
    if integration_mode in ("real", "controlled", "llm"):
        return "none"
    return resolve_finalizer_mode(adapter_config)


def infer_matrix_calibration_profile(
    target_experiment: str,
    targets: List[Dict[str, Any]],
) -> str:
    """Infer calibration profile for transfer matrix experiments."""
    name = target_experiment.lower()
    if "hard" in name:
        return "hard"
    if "medium" in name:
        return "medium"

    profiles = {
        t.get("adapter_config", {}).get("calibration_profile")
        for t in targets
        if t.get("adapter_config", {}).get("calibration_profile")
    }
    profiles.discard(None)
    if len(profiles) == 1:
        return str(next(iter(profiles)))
    return resolve_calibration_profile({}, target_experiment)


def resolve_calibration_profile(
    adapter_config: Dict[str, Any],
    experiment_name: str = "",
) -> str:
    """Return calibration profile; legacy when unset or explicitly legacy."""
    profile = adapter_config.get("calibration_profile")
    if profile:
        return str(profile)
    return "legacy"


def build_experiment_metadata(config: ExperimentConfig) -> Dict[str, Any]:
    """Build standard metadata block for metrics_summary.json."""
    adapter_config = config.adapter_config or {}
    calibration_profile = resolve_calibration_profile(adapter_config, config.experiment_name)
    integration_mode = resolve_integration_mode(
        config.system_name,
        config.adapter_type,
        adapter_config,
    )
    return {
        "experiment_name": config.experiment_name,
        "config_name": config.experiment_name,
        "system_name": config.system_name,
        "architecture": infer_architecture(config.system_name),
        "integration_mode": integration_mode,
        "calibration_profile": calibration_profile,
        "attack_generator": config.attack_generator,
        "defense": config.defense,
        "goal": config.goal,
        "random_seed": config.random_seed,
        "num_iterations": config.num_iterations,
        "num_tasks": config.num_tasks,
        "attack_generator_version": config.attack_generator_version,
        "finalizer_exposure_mode": resolve_finalizer_exposure_for_metrics(
            integration_mode, adapter_config
        ),
        "final_output_source": resolve_final_output_source(integration_mode),
        "adapter_name": resolve_adapter_name(config.adapter_type, config.system_name),
        "reward_profile": config.reward_profile or "",
        "llm_mode": adapter_config.get("llm_mode", ""),
        "llm_provider": adapter_config.get("llm_provider", ""),
        "llm_model": adapter_config.get("llm_model", ""),
        "adapter_config": adapter_config,
    }
