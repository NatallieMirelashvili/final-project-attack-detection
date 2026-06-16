"""CLI entry point for transfer experiments."""

from __future__ import annotations

import argparse
import sys

from agent_redteam.experiments.transfer_runner import TransferRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run transfer experiment")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args(argv)

    runner = TransferRunner(args.config)
    metrics = runner.run()

    print("Transfer experiment completed.")
    print(f"Source: {metrics.get('source_experiment', 'N/A')}")
    print(f"Target: {metrics.get('target_experiment', 'N/A')}")
    agg = metrics.get("aggregate", {})
    print(f"Mean transfer ASR: {agg.get('mean_transfer_asr', 0.0):.3f}")
    if metrics.get("cross_architecture"):
        print(
            f"Cross-architecture transfer: "
            f"{metrics['cross_architecture'].get('mean_cross_architecture_transfer', 0.0):.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
