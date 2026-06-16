"""CLI entry point for summarizing experiment results."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from agent_redteam.paper_tables import generate_paper_tables


def _load_metrics(exp_dir: Path) -> Dict[str, Any]:
    path = exp_dir / "metrics_summary.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _append_rows(
    rows: List[Dict[str, Any]],
    experiment_name: str,
    metrics: Dict[str, Any],
    category: str,
) -> None:
    if category == "leakage":
        leakage = metrics.get("leakage", {})
        for key, val in leakage.items():
            if key == "channel_breakdown":
                for ch, ch_val in val.items():
                    rows.append({
                        "experiment": experiment_name,
                        "metric": f"channel_{ch}",
                        "value": ch_val,
                    })
            else:
                rows.append({
                    "experiment": experiment_name,
                    "metric": key,
                    "value": val,
                })
    elif category == "degradation":
        perf = metrics.get("performance", {})
        for key, val in perf.items():
            rows.append({
                "experiment": experiment_name,
                "metric": key,
                "value": val,
            })
    elif category == "transfer":
        for tr in metrics.get("transfer_results", []):
            rows.append({
                "experiment": experiment_name,
                "variant_id": tr.get("variant_id"),
                "transfer_asr": tr.get("transfer_asr"),
                "generalization_gap": tr.get("generalization_gap"),
                "source_metric": tr.get("source_metric"),
                "target_metric": tr.get("target_metric"),
            })
    elif category == "defense":
        rows.append({
            "experiment": experiment_name,
            "defense": metrics.get("defense", "unknown"),
            "goal": metrics.get("goal", "unknown"),
        })


def summarize(results_dir: str | Path) -> Path:
    results_path = Path(results_dir)
    summary_path = results_path / "summary"
    summary_path.mkdir(parents=True, exist_ok=True)

    leakage_rows: List[Dict[str, Any]] = []
    degradation_rows: List[Dict[str, Any]] = []
    transfer_rows: List[Dict[str, Any]] = []
    defense_rows: List[Dict[str, Any]] = []

    for exp_dir in sorted(results_path.iterdir()):
        if not exp_dir.is_dir() or exp_dir.name == "summary":
            continue
        metrics = _load_metrics(exp_dir)
        if not metrics:
            continue

        goal = metrics.get("goal", "")
        exp_name = metrics.get("experiment_name", exp_dir.name)

        if "transfer_results" in metrics:
            _append_rows(transfer_rows, exp_name, metrics, "transfer")
        elif goal == "leakage":
            _append_rows(leakage_rows, exp_name, metrics, "leakage")
        elif goal == "degradation" or "performance" in metrics:
            _append_rows(degradation_rows, exp_name, metrics, "degradation")

        _append_rows(defense_rows, exp_name, metrics, "defense")

    if leakage_rows:
        with (summary_path / "leakage_results.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["experiment", "metric", "value"])
            writer.writeheader()
            writer.writerows(leakage_rows)

    if degradation_rows:
        with (summary_path / "degradation_results.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["experiment", "metric", "value"])
            writer.writeheader()
            writer.writerows(degradation_rows)

    if transfer_rows:
        with (summary_path / "transfer_results.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "experiment",
                    "variant_id",
                    "transfer_asr",
                    "generalization_gap",
                    "source_metric",
                    "target_metric",
                ],
            )
            writer.writeheader()
            writer.writerows(transfer_rows)

    if defense_rows:
        with (summary_path / "defense_results.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["experiment", "defense", "goal"])
            writer.writeheader()
            writer.writerows(defense_rows)

    generate_paper_tables(results_path, summary_path)

    return summary_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize experiment results")
    parser.add_argument("--results-dir", required=True, help="Path to results directory")
    args = parser.parse_args(argv)

    summary_path = summarize(args.results_dir)
    print(f"Summary written to {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
