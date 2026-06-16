"""Tests for canary utilities."""

from agent_redteam.data.canaries import (
    CANARY_CLIENT_ID_042,
    CANARY_FAKE_API_KEY_093,
    contains_exact_canary,
    contains_partial_canary,
    generate_canaries,
    redact_canaries,
)


def test_base_canaries_present():
    canaries = generate_canaries(4)
    assert CANARY_CLIENT_ID_042 in canaries
    assert CANARY_FAKE_API_KEY_093 in canaries


def test_generate_canaries_deterministic():
    a = generate_canaries(6)
    b = generate_canaries(6)
    assert a == b
    assert len(a) == 6


def test_contains_exact_canary():
    canaries = [CANARY_CLIENT_ID_042]
    assert contains_exact_canary("prefix CANARY_CLIENT_ID_042 suffix", canaries)
    assert not contains_exact_canary("no canary here", canaries)


def test_contains_partial_canary():
    canaries = [CANARY_CLIENT_ID_042]
    assert contains_partial_canary("CANARY_CLIENT", canaries)
    assert not contains_partial_canary("short", canaries)


def test_redact_canaries():
    canaries = [CANARY_CLIENT_ID_042]
    text = f"secret={CANARY_CLIENT_ID_042}"
    redacted = redact_canaries(text, canaries)
    assert CANARY_CLIENT_ID_042 not in redacted
    assert "[REDACTED]" in redacted
