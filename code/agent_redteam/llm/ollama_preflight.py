"""Preflight checks for local Ollama before live LLM experiments."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Tuple

from agent_redteam.llm.ollama_client import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    is_ollama_model_available,
    is_ollama_running,
    list_ollama_models,
)


def run_preflight(
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> Tuple[int, List[str]]:
    """Run Ollama preflight checks. Returns (exit_code, message_lines)."""
    lines: List[str] = []
    lines.append(f"Ollama preflight")
    lines.append(f"  base_url: {base_url}")
    lines.append(f"  model:    {model}")
    lines.append("")

    if not is_ollama_running(base_url):
        lines.append(f"FAIL: Ollama is not reachable at {base_url}.")
        lines.append("")
        lines.append("Start Ollama, then retry:")
        lines.append("  - Open the Ollama desktop app, or")
        lines.append("  - Run: ollama serve")
        lines.append("")
        lines.append(f"After Ollama is running, pull the model:")
        lines.append(f"  ollama pull {model}")
        return 1, lines

    lines.append(f"OK: Ollama is reachable at {base_url}.")

    models = list_ollama_models(base_url)
    if models:
        lines.append("")
        lines.append("Available models:")
        for name in sorted(models):
            lines.append(f"  - {name}")
    else:
        lines.append("")
        lines.append("WARN: Ollama responded but no models were listed.")

    lines.append("")
    if is_ollama_model_available(model, base_url):
        lines.append(f"OK: Model '{model}' is available locally.")
        lines.append("")
        lines.append("Ready for live Ollama smoke experiments.")
        return 0, lines

    lines.append(f"FAIL: Model '{model}' is not available locally.")
    lines.append("")
    lines.append("Pull the model with:")
    lines.append(f"  ollama pull {model}")
    lines.append("")
    lines.append("Optional lighter fallback:")
    lines.append("  ollama pull llama3.2:1b")
    lines.append("  # then set llm_model: llama3.2:1b in adapter_config")
    return 1, lines


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Ollama availability before live LLM experiments.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_OLLAMA_BASE_URL,
        help=f"Ollama base URL (default: {DEFAULT_OLLAMA_BASE_URL})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_OLLAMA_MODEL,
        help=f"Expected model name (default: {DEFAULT_OLLAMA_MODEL})",
    )
    args = parser.parse_args(argv)
    exit_code, lines = run_preflight(base_url=args.base_url, model=args.model)
    print("\n".join(lines))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
