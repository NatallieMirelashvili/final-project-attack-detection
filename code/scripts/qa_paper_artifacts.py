"""QA validation for paper-ready artifacts against source analysis CSVs."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "results" / "analysis"
DEFAULT_PAPER_DIR = ROOT / "docs" / "results" / "live_ollama_small"

TOL = 1e-9

SOURCE_MISSING_MSG = """\
Source analysis directory not found: {path}

Raw experiment outputs and generated analysis files live under code/results/, which is
ignored by git. Regenerate locally before running QA:

  python scripts/compile_small_report.py
  python scripts/build_paper_tables.py

Then copy updated artifacts into docs/results/live_ollama_small/ if needed.
"""


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate paper-ready docs against local analysis CSVs."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory with live_ollama_small_metrics.csv and degradation_family_metrics.csv "
        "(default: results/analysis)",
    )
    parser.add_argument(
        "--paper-dir",
        type=Path,
        default=DEFAULT_PAPER_DIR,
        help="Directory with paper-ready markdown/CSV artifacts "
        "(default: docs/results/live_ollama_small)",
    )
    return parser.parse_args(argv)


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fval(val: str) -> Optional[float]:
    if val is None or val == "":
        return None
    return float(val)


def round3(val: Optional[float]) -> str:
    if val is None:
        return "---"
    return f"{val:.3f}"


def best_family(system: str, key: str, families: List[Dict[str, str]]) -> str:
    cands = [
        r for r in families if r["system"] == system and r["scale"] == "small" and r.get(key, "")
    ]
    if not cands:
        return "---"
    return max(cands, key=lambda r: fval(r[key]) or 0.0)["family"]


def check_close(
    errors: List[str],
    a: Optional[float],
    b: Optional[float],
    label: str,
) -> None:
    if a is None and b is None:
        return
    if a is None or b is None:
        errors.append(f"{label}: mismatch None vs value ({a} vs {b})")
        return
    if abs(a - b) > TOL:
        errors.append(f"{label}: {a} != {b}")


def parse_md_table_rows(md: str, section: str) -> List[List[str]]:
    lines = md.splitlines()
    in_section = False
    rows: List[List[str]] = []
    for line in lines:
        if line.startswith("## ") and section in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells[0] not in ("System",):
                rows.append(cells)
    return rows


def resolve_dir(path: Path, label: str) -> Path:
    resolved = path if path.is_absolute() else (ROOT / path)
    if not resolved.is_dir():
        if label == "source":
            print(SOURCE_MISSING_MSG.format(path=resolved), file=sys.stderr)
            sys.exit(2)
        print(f"Paper artifacts directory not found: {resolved}", file=sys.stderr)
        sys.exit(2)
    return resolved


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        print(f"Missing required {label}: {path}", file=sys.stderr)
        sys.exit(2)
    return path


def validate(source_dir: Path, paper_dir: Path) -> int:
    errors: List[str] = []
    warnings: List[str] = []

    metrics_path = require_file(
        source_dir / "live_ollama_small_metrics.csv", "source metrics CSV"
    )
    family_path = require_file(
        source_dir / "degradation_family_metrics.csv", "source family metrics CSV"
    )

    paper_md = require_file(paper_dir / "paper_tables.md", "paper tables markdown")
    draft_md = require_file(paper_dir / "paper_results_draft.md", "results draft markdown")
    values_md = require_file(paper_dir / "paper_table_values.md", "paper table values markdown")
    leak_csv = require_file(paper_dir / "paper_leakage_table.csv", "leakage table CSV")
    ext_csv = require_file(paper_dir / "paper_external_leakage_table.csv", "external leakage CSV")
    deg_csv = require_file(paper_dir / "paper_degradation_table.csv", "degradation table CSV")

    metrics = load_csv(metrics_path)
    families = load_csv(family_path)
    small = [r for r in metrics if r["scale"] == "small"]

    leak_src = {r["system"]: r for r in small if r["goal"] == "leakage"}
    ext_src = {r["system"]: r for r in small if r["goal"] == "external_leakage"}
    deg_src = {r["system"]: r for r in small if r["goal"] == "degradation"}

    for row in load_csv(leak_csv):
        s = row["system"]
        src = leak_src[s]
        check_close(errors, fval(row["leakage_asr"]), fval(src["leakage_asr"]), f"leak csv {s} leakage_asr")
        check_close(
            errors,
            fval(row["internal_leakage_rate"]),
            fval(src["internal_leakage_rate"]),
            f"leak csv {s} internal",
        )
        check_close(
            errors,
            fval(row["final_output_leakage_rate"]),
            fval(src["final_output_leakage_rate"]),
            f"leak csv {s} final",
        )
        check_close(
            errors,
            fval(row["clean_task_success_rate"]),
            fval(src["clean_task_success_rate"]),
            f"leak csv {s} clean",
        )
        check_close(
            errors,
            fval(row["attacked_task_success_rate"]),
            fval(src["attacked_task_success_rate"]),
            f"leak csv {s} attacked",
        )

    for row in load_csv(ext_csv):
        s = row["system"]
        src = ext_src[s]
        for col in [
            "external_leakage_asr",
            "internal_leakage_rate",
            "final_output_leakage_rate",
            "clean_task_success_rate",
            "attacked_task_success_rate",
        ]:
            check_close(errors, fval(row[col]), fval(src[col]), f"ext csv {s} {col}")
        if "utility_drop" in row:
            errors.append(f"ext csv {s}: utility_drop column must not appear")

    for row in load_csv(deg_csv):
        s = row["system"]
        src = deg_src[s]
        check_close(errors, fval(row["utility_drop"]), fval(src["utility_drop"]), f"deg csv {s} utility_drop")
        check_close(
            errors,
            fval(row["operational_degradation_score"]),
            fval(src["operational_degradation_score"]),
            f"deg csv {s} operational",
        )
        check_close(
            errors,
            fval(row["clean_task_success_rate"]),
            fval(src["clean_task_success_rate"]),
            f"deg csv {s} clean",
        )
        check_close(
            errors,
            fval(row["attacked_task_success_rate"]),
            fval(src["attacked_task_success_rate"]),
            f"deg csv {s} attacked",
        )
        if row["strongest_family_by_utility_drop"] != best_family(s, "utility_drop", families):
            errors.append(f"deg csv {s}: strongest util family mismatch")
        if row["strongest_family_by_operational_score"] != best_family(
            s, "operational_degradation_score", families
        ):
            errors.append(f"deg csv {s}: strongest op family mismatch")

    md = paper_md.read_text(encoding="utf-8")
    for cells in parse_md_table_rows(md, "Table A"):
        s = cells[0]
        src = leak_src[s]
        expected = [
            round3(fval(src["leakage_asr"])),
            round3(fval(src["internal_leakage_rate"])),
            round3(fval(src["final_output_leakage_rate"])),
            round3(fval(src["clean_task_success_rate"])),
            round3(fval(src["attacked_task_success_rate"])),
        ]
        if cells[1:] != expected:
            errors.append(f"paper_tables A {s}: {cells[1:]} != {expected}")

    for cells in parse_md_table_rows(md, "Table B"):
        s = cells[0]
        src = ext_src[s]
        expected = [
            round3(fval(src["external_leakage_asr"])),
            round3(fval(src["internal_leakage_rate"])),
            round3(fval(src["final_output_leakage_rate"])),
            round3(fval(src["clean_task_success_rate"])),
            round3(fval(src["attacked_task_success_rate"])),
        ]
        if cells[1:] != expected:
            errors.append(f"paper_tables B {s}: {cells[1:]} != {expected}")

    for cells in parse_md_table_rows(md, "Table C"):
        s = cells[0]
        src = deg_src[s]
        expected = [
            round3(fval(src["clean_task_success_rate"])),
            round3(fval(src["attacked_task_success_rate"])),
            round3(fval(src["utility_drop"])),
            round3(fval(src["operational_degradation_score"])),
            best_family(s, "utility_drop", families),
            best_family(s, "operational_degradation_score", families),
        ]
        if cells[1:] != expected:
            errors.append(f"paper_tables C {s}: {cells[1:]} != {expected}")

    if "Table B" in md:
        b_section = md.split("## Table B")[1].split("## Table C")[0].lower()
        if "utility_drop" in b_section or "| utility drop |" in b_section:
            errors.append("Table B mentions utility drop as column")

    draft = draft_md.read_text(encoding="utf-8").lower()
    for phrase in [
        "small-scale exploratory evaluation",
        "preliminary evidence",
        "in this setting",
        "suggests",
    ]:
        if phrase not in draft:
            warnings.append(f"draft missing phrase: {phrase}")

    for phrase in ["conclusively proves", "definitively demonstrates", "establishes a new benchmark"]:
        if phrase in draft:
            errors.append(f"draft contains forbidden claim: {phrase}")

    for caveat in ["4 tasks", "6 variant", "llama3.2:3b", "summarizer", "pilot"]:
        if caveat not in draft:
            warnings.append(f"draft missing caveat keyword: {caveat}")

    if "smoke" not in draft:
        warnings.append("draft missing smoke-results infrastructure caveat")

    values = values_md.read_text(encoding="utf-8")
    if "task_success_side_effect (not degradation)" not in values:
        errors.append("paper_table_values missing side-effect label")

    print(f"Source dir: {source_dir}")
    print(f"Paper dir:  {paper_dir}")
    print("ERRORS", len(errors))
    for error in errors:
        print("  ERROR:", error)
    print("WARNINGS", len(warnings))
    for warning in warnings:
        print("  WARN:", warning)

    if errors:
        return 1
    if warnings:
        print("QA PASSED with warnings")
        return 0
    print("QA PASSED")
    return 0


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    source_dir = resolve_dir(args.source_dir, "source")
    paper_dir = resolve_dir(args.paper_dir, "paper")
    return validate(source_dir, paper_dir)


if __name__ == "__main__":
    sys.exit(main())
