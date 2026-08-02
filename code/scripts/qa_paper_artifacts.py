"""QA validation for paper-ready artifacts against source CSVs."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "results" / "analysis"

METRICS = ANALYSIS / "live_ollama_small_metrics.csv"
FAMILY = ANALYSIS / "degradation_family_metrics.csv"

PAPER_MD = ANALYSIS / "paper_tables.md"
DRAFT_MD = ANALYSIS / "paper_results_draft.md"
VALUES_MD = ANALYSIS / "paper_table_values.md"
LEAK_CSV = ANALYSIS / "paper_leakage_table.csv"
EXT_CSV = ANALYSIS / "paper_external_leakage_table.csv"
DEG_CSV = ANALYSIS / "paper_degradation_table.csv"

TOL = 1e-9
errors: List[str] = []
warnings: List[str] = []


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


def check_close(a: Optional[float], b: Optional[float], label: str) -> None:
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


def main() -> int:
    metrics = load_csv(METRICS)
    families = load_csv(FAMILY)
    small = [r for r in metrics if r["scale"] == "small"]

    leak_src = {r["system"]: r for r in small if r["goal"] == "leakage"}
    ext_src = {r["system"]: r for r in small if r["goal"] == "external_leakage"}
    deg_src = {r["system"]: r for r in small if r["goal"] == "degradation"}

    # CSV checks
    for row in load_csv(LEAK_CSV):
        s = row["system"]
        src = leak_src[s]
        check_close(fval(row["leakage_asr"]), fval(src["leakage_asr"]), f"leak csv {s} leakage_asr")
        check_close(fval(row["internal_leakage_rate"]), fval(src["internal_leakage_rate"]), f"leak csv {s} internal")
        check_close(fval(row["final_output_leakage_rate"]), fval(src["final_output_leakage_rate"]), f"leak csv {s} final")
        check_close(fval(row["clean_task_success_rate"]), fval(src["clean_task_success_rate"]), f"leak csv {s} clean")
        check_close(fval(row["attacked_task_success_rate"]), fval(src["attacked_task_success_rate"]), f"leak csv {s} attacked")

    for row in load_csv(EXT_CSV):
        s = row["system"]
        src = ext_src[s]
        for col in [
            "external_leakage_asr",
            "internal_leakage_rate",
            "final_output_leakage_rate",
            "clean_task_success_rate",
            "attacked_task_success_rate",
        ]:
            check_close(fval(row[col]), fval(src[col]), f"ext csv {s} {col}")
        if "utility_drop" in row:
            errors.append(f"ext csv {s}: utility_drop column must not appear")

    for row in load_csv(DEG_CSV):
        s = row["system"]
        src = deg_src[s]
        check_close(fval(row["utility_drop"]), fval(src["utility_drop"]), f"deg csv {s} utility_drop")
        check_close(
            fval(row["operational_degradation_score"]),
            fval(src["operational_degradation_score"]),
            f"deg csv {s} operational",
        )
        check_close(fval(row["clean_task_success_rate"]), fval(src["clean_task_success_rate"]), f"deg csv {s} clean")
        check_close(
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

    # Markdown table rounded checks
    md = PAPER_MD.read_text(encoding="utf-8")
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

    if "utility drop" in md.lower() and "Table B" in md:
        b_section = md.split("## Table B")[1].split("## Table C")[0].lower()
        if "utility_drop" in b_section or "| utility drop |" in b_section:
            errors.append("Table B mentions utility drop as column")

    # Wording checks
    draft = DRAFT_MD.read_text(encoding="utf-8").lower()
    required_phrases = [
        "small-scale exploratory evaluation",
        "preliminary evidence",
        "in this setting",
        "suggests",
    ]
    for phrase in required_phrases:
        if phrase not in draft:
            warnings.append(f"draft missing phrase: {phrase}")

    forbidden = ["conclusively proves", "definitively demonstrates", "establishes a new benchmark"]
    for phrase in forbidden:
        if phrase in draft:
            errors.append(f"draft contains forbidden claim: {phrase}")

    caveats = [
        "4 tasks",
        "6 variant",
        "llama3.2:3b",
        "summarizer",
        "pilot",
    ]
    for c in caveats:
        if c not in draft:
            warnings.append(f"draft missing caveat keyword: {c}")

    if "smoke" not in draft:
        warnings.append("draft missing smoke-results infrastructure caveat")

    values = VALUES_MD.read_text(encoding="utf-8")
    if "task_success_side_effect (not degradation)" not in values:
        errors.append("paper_table_values missing side-effect label")

    print("ERRORS", len(errors))
    for e in errors:
        print("  ERROR:", e)
    print("WARNINGS", len(warnings))
    for w in warnings:
        print("  WARN:", w)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
