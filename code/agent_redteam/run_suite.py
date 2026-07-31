"""CLI entry point for sequential experiment suite runs."""

from __future__ import annotations

from agent_redteam.adapters.official_runtime import configure_official_runtime_env

configure_official_runtime_env()

import argparse
import sys
from pathlib import Path

from agent_redteam.experiments.suite_runner import SuiteRunner, load_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a sequential experiment suite")
    parser.add_argument(
        "--suite",
        required=True,
        help="Path to suite YAML file (e.g. configs/suites/live_ollama_medium_core.yaml)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete each experiment result directory before running",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue to the next config if one fails",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the suite on the first failed config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate suite configs and print the run plan without executing experiments",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Start even if a suite lockfile already exists",
    )
    args = parser.parse_args(argv)

    suite_path = Path(args.suite)
    suite = load_suite(suite_path)

    continue_on_error: bool | None = None
    if args.stop_on_error:
        continue_on_error = False
    elif args.continue_on_error:
        continue_on_error = True

    runner = SuiteRunner(
        suite,
        suite_file=suite_path,
        fresh=args.fresh,
        continue_on_error=continue_on_error,
        dry_run=args.dry_run,
        force=args.force,
    )

    try:
        result = runner.run()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if result.dry_run:
        print(f"Dry run OK: {len(suite.configs)} config(s) in suite '{suite.suite_name}'")
        return 0

    failed = [r for r in result.records if not r.success]
    print(f"Suite '{suite.suite_name}' finished.")
    print(f"Suite artifacts: {result.suite_dir}")
    print(f"Completed: {len(result.records) - len(failed)}/{len(result.records)}")
    if result.summarize_completed:
        print("Summarize: completed")
    elif suite.summarize_at_end:
        print(f"Summarize: failed ({result.summarize_error or 'no successful runs'})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
