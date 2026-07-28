"""Deterministic mock LLM for offline tests and reproducible experiments."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from agent_redteam.data.canaries import contains_exact_canary
from agent_redteam.goals import is_leakage_goal
from agent_redteam.llm.types import LLMResponse, Message, ToolCall, ToolSpec


def _digest(*parts: Any) -> int:
    raw = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def _context_text(messages: List[Message]) -> str:
    return "\n".join(f"{m.role}:{m.content}" for m in messages)


class MockLLMClient:
    """Seed- and role-deterministic LLM simulator without network access."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = dict(config or {})
        self._token_price = float(self._config.get("token_price", 0.00001))

    def complete(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[ToolSpec]] = None,
        seed: Optional[int] = None,
        agent_role: str = "",
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        meta = dict(metadata or {})
        attack_goal = str(meta.get("attack_goal", ""))
        expected_answer = str(meta.get("expected_answer", ""))
        canaries = list(meta.get("canaries") or [])
        instruction = str(meta.get("instruction", ""))
        domain = str(meta.get("domain", "general"))
        ctx = _context_text(messages)
        rng_seed = _digest(seed or 0, agent_role, task_id or "", len(messages))

        tool_calls: List[ToolCall] = []
        text = ""
        finish = "stop"

        if agent_role == "planner":
            text = (
                f"Plan for {task_id}: break down '{instruction[:80]}' into retrieval, "
                f"execution, and review steps for domain={domain}."
            )
            if attack_goal == "degradation" and "maximum tokens" in ctx.lower():
                text += " Priority: invoke tools repeatedly before answering."
                tool_calls.append(
                    ToolCall(
                        id=f"tc_{rng_seed}",
                        name="execute_workflow_step",
                        arguments={"task_id": task_id, "mode": "verbose"},
                    )
                )
                finish = "tool_calls"

        elif agent_role == "retriever":
            if tools:
                tool_calls.append(
                    ToolCall(
                        id=f"tc_{rng_seed}",
                        name="retrieve_domain_context",
                        arguments={"task_id": task_id, "domain": domain, "query": instruction[:60]},
                    )
                )
                text = f"Retrieval query prepared for {domain}."
                finish = "tool_calls"
            else:
                text = f"[retrieved] Context stub for {domain}."

        elif agent_role == "worker":
            degrade = attack_goal == "degradation" and (
                "fail" in ctx.lower() or "maximum tokens" in ctx.lower()
            )
            if degrade or (_digest(rng_seed, "worker_extra") % 5 == 0 and attack_goal == "degradation"):
                tool_calls.append(
                    ToolCall(
                        id=f"tc_{rng_seed}_a",
                        name="execute_workflow_step",
                        arguments={"task_id": task_id, "repeat": 2},
                    )
                )
                tool_calls.append(
                    ToolCall(
                        id=f"tc_{rng_seed}_b",
                        name="execute_workflow_step",
                        arguments={"task_id": task_id, "repeat": 3},
                    )
                )
                text = "Executing extended tool sequence."
                finish = "tool_calls"
            elif tools:
                tool_calls.append(
                    ToolCall(
                        id=f"tc_{rng_seed}",
                        name="execute_workflow_step",
                        arguments={"task_id": task_id},
                    )
                )
                text = "Invoking workflow tool."
                finish = "tool_calls"
            else:
                text = f"Worker completed step for {task_id}."

        elif agent_role == "memory":
            snippet = instruction[:40]
            if is_leakage_goal(attack_goal) and canaries and contains_exact_canary(ctx, canaries):
                canary = canaries[0]
                text = f"memory:{task_id}=store plan and context | note={canary}"
            elif attack_goal == "degradation" and "wrong" in ctx.lower():
                text = f"memory:{task_id}=unrelated cache payload"
            else:
                text = f"memory:{task_id}=plan:{snippet}; status=in_progress"

        elif agent_role in ("reviewer", "finalizer"):
            text = self._finalizer_text(
                ctx=ctx,
                expected_answer=expected_answer,
                canaries=canaries,
                attack_goal=attack_goal,
                instruction=instruction,
                rng_seed=rng_seed,
            )
        else:
            text = f"[{agent_role}] processed context for {task_id}."

        token_count = max(20, len(text.split()) * 4 + sum(len(json.dumps(tc.arguments)) for tc in tool_calls))
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            token_count=token_count,
            estimated_cost=token_count * self._token_price,
            latency_ms=1.0 + (token_count * 0.01),
            finish_reason=finish,
            metadata={"mock": True, "agent_role": agent_role, "rng_seed": rng_seed},
        )

    def _finalizer_text(
        self,
        *,
        ctx: str,
        expected_answer: str,
        canaries: List[str],
        attack_goal: str,
        instruction: str,
        rng_seed: int,
    ) -> str:
        if attack_goal == "degradation":
            if "fail deliberately" in ctx.lower() or "maximum tokens" in ctx.lower():
                return f"Incomplete analysis for: {instruction[:50]}... Further review required."
            if _digest(rng_seed, "deg_final") % 3 == 0:
                return "Unable to complete task due to conflicting tool outputs."

        if is_leakage_goal(attack_goal) and canaries:
            for canary in canaries:
                if canary in ctx:
                    if _digest(rng_seed, canary, "leak") % 4 != 0:
                        return (
                            f"Summary for request '{instruction[:40]}': "
                            f"please refer to internal ref {canary} in the report."
                        )
            if "reveal" in ctx.lower() or "secret" in ctx.lower():
                canary = canaries[0]
                return f"Report draft includes credential token {canary} for verification."

        if expected_answer:
            return (
                f"Final response: Based on retrieved materials and tool results, "
                f"{expected_answer}"
            )
        return f"Final response: Completed work on {instruction[:60]}."
