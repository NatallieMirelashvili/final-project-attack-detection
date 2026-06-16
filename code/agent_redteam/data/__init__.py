"""Synthetic data and canary utilities."""

from agent_redteam.data.canaries import (
    CANARY_CLIENT_ID_042,
    CANARY_FAKE_API_KEY_093,
    CANARY_PRIVATE_DOC_008,
    CANARY_SALARY_TABLE_017,
    contains_exact_canary,
    contains_partial_canary,
    generate_canaries,
    redact_canaries,
)
from agent_redteam.data.synthetic_tasks import generate_synthetic_tasks

__all__ = [
    "CANARY_CLIENT_ID_042",
    "CANARY_FAKE_API_KEY_093",
    "CANARY_SALARY_TABLE_017",
    "CANARY_PRIVATE_DOC_008",
    "contains_exact_canary",
    "contains_partial_canary",
    "generate_canaries",
    "generate_synthetic_tasks",
    "redact_canaries",
]
