"""Official framework import helpers with clear dependency errors."""

from __future__ import annotations

import os
from typing import Any, Tuple


def configure_official_runtime_env() -> None:
    """Disable third-party telemetry before official framework imports/runs."""
    os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
    os.environ["CREWAI_DISABLE_TRACKING"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

AUTOGEN_OFFICIAL_IMPORT_ERROR = (
    "Official AutoGen is not installed. Install optional dependency with: "
    "pip install 'agent-redteam[autogen]'"
)

CREWAI_OFFICIAL_IMPORT_ERROR = (
    "Official CrewAI is not installed. Install optional dependency with: "
    "pip install 'agent-redteam[crewai]'"
)


def try_import_autogen_official() -> Tuple[Any, Any, Any, Any]:
    """Import official AutoGen agent-chat APIs or raise ImportError."""
    configure_official_runtime_env()
    try:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_core.models import ChatCompletionClient
    except ImportError as exc:
        raise ImportError(AUTOGEN_OFFICIAL_IMPORT_ERROR) from exc
    return AssistantAgent, RoundRobinGroupChat, MaxMessageTermination, ChatCompletionClient


def try_import_crewai_official() -> Tuple[Any, Any, Any, Any]:
    """Import official CrewAI APIs or raise ImportError."""
    configure_official_runtime_env()
    try:
        from crewai import Agent, Crew, Process, Task
    except ImportError as exc:
        raise ImportError(CREWAI_OFFICIAL_IMPORT_ERROR) from exc
    return Agent, Task, Crew, Process


def is_autogen_official_available() -> bool:
    try:
        try_import_autogen_official()
        return True
    except ImportError:
        return False


def is_crewai_official_available() -> bool:
    try:
        try_import_crewai_official()
        return True
    except ImportError:
        return False


configure_official_runtime_env()
