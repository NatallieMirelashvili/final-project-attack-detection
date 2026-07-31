"""CLI entry point for running experiments."""

from __future__ import annotations

from agent_redteam.adapters.official_runtime import configure_official_runtime_env

configure_official_runtime_env()

import argparse
import sys

from agent_redteam.experiments.runner import ExperimentRunner, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run agent red-team experiment")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete the experiment output directory before running (avoids appending to runs.jsonl)",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    runner = ExperimentRunner(config, fresh=args.fresh)
    metrics = runner.run()

    print(f"Experiment '{config.experiment_name}' completed.")
    print(f"Output: {runner.output_path}")
    if config.goal == "leakage":
        leakage = metrics.get("leakage", {})
        print(f"Leakage ASR: {leakage.get('leakage_asr', 0.0):.3f}")
    else:
        perf = metrics.get("performance", {})
        print(f"Utility drop: {perf.get('utility_drop', 0.0):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
