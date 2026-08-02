"""Build paper-ready tables from completed small-suite analysis CSVs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ANALYSIS = Path("results/analysis")
METRICS_CSV = ANALYSIS / "live_ollama_small_metrics.csv"
FAMILY_CSV = ANALYSIS / "degradation_family_metrics.csv"


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _f(val: str) -> Optional[float]:
    if val is None or val == "":
        return None
    return float(val)


def _fmt3(val: Optional[float]) -> str:
    if val is None:
        return "---"
    return f"{val:.3f}"


def _fmt_exact(val: Optional[float]) -> str:
    if val is None:
        return "---"
    return repr(val)


def _best_family(
    families: List[Dict[str, str]], system: str, key: str
) -> Tuple[str, Optional[float]]:
    candidates = [
        r
        for r in families
        if r["system"] == system and r["scale"] == "small" and r.get(key, "") != ""
    ]
    if not candidates:
        return "---", None
    best = max(candidates, key=lambda r: _f(r[key]) or 0.0)
    return best["family"], _f(best[key])


def build_tables() -> None:
    rows = _load_csv(METRICS_CSV)
    families = _load_csv(FAMILY_CSV)
    small = [r for r in rows if r["scale"] == "small"]

    leakage = [r for r in small if r["goal"] == "leakage"]
    external = [r for r in small if r["goal"] == "external_leakage"]
    degradation = [r for r in small if r["goal"] == "degradation"]
    medium = next((r for r in rows if r["experiment_name"] == "langgraph_real_llm_ollama_degradation_medium"), None)

    # --- CSV tables ---
    leak_cols = [
        "system",
        "leakage_asr",
        "internal_leakage_rate",
        "final_output_leakage_rate",
        "clean_task_success_rate",
        "attacked_task_success_rate",
    ]
    ext_cols = [
        "system",
        "external_leakage_asr",
        "internal_leakage_rate",
        "final_output_leakage_rate",
        "clean_task_success_rate",
        "attacked_task_success_rate",
    ]
    deg_cols = [
        "system",
        "clean_task_success_rate",
        "attacked_task_success_rate",
        "utility_drop",
        "operational_degradation_score",
        "strongest_family_by_utility_drop",
        "strongest_family_by_operational_score",
    ]

    leak_rows: List[Dict[str, Any]] = []
    for r in leakage:
        leak_rows.append(
            {
                "system": r["system"],
                "leakage_asr": _f(r["leakage_asr"]),
                "internal_leakage_rate": _f(r["internal_leakage_rate"]),
                "final_output_leakage_rate": _f(r["final_output_leakage_rate"]),
                "clean_task_success_rate": _f(r["clean_task_success_rate"]),
                "attacked_task_success_rate": _f(r["attacked_task_success_rate"]),
            }
        )

    ext_rows: List[Dict[str, Any]] = []
    for r in external:
        clean = _f(r["clean_task_success_rate"])
        attacked = _f(r["attacked_task_success_rate"])
        ext_rows.append(
            {
                "system": r["system"],
                "external_leakage_asr": _f(r["external_leakage_asr"]),
                "internal_leakage_rate": _f(r["internal_leakage_rate"]),
                "final_output_leakage_rate": _f(r["final_output_leakage_rate"]),
                "clean_task_success_rate": clean,
                "attacked_task_success_rate": attacked,
            }
        )

    deg_rows: List[Dict[str, Any]] = []
    for r in degradation:
        fam_util, _ = _best_family(families, r["system"], "utility_drop")
        fam_op, _ = _best_family(families, r["system"], "operational_degradation_score")
        deg_rows.append(
            {
                "system": r["system"],
                "clean_task_success_rate": _f(r["clean_task_success_rate"]),
                "attacked_task_success_rate": _f(r["attacked_task_success_rate"]),
                "utility_drop": _f(r["utility_drop"]),
                "operational_degradation_score": _f(r["operational_degradation_score"]),
                "strongest_family_by_utility_drop": fam_util,
                "strongest_family_by_operational_score": fam_op,
            }
        )

    def write_table_csv(path: Path, fieldnames: List[str], data: List[Dict[str, Any]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({k: row[k] for k in fieldnames})

    write_table_csv(ANALYSIS / "paper_leakage_table.csv", leak_cols, leak_rows)
    write_table_csv(ANALYSIS / "paper_external_leakage_table.csv", ext_cols, ext_rows)
    write_table_csv(ANALYSIS / "paper_degradation_table.csv", deg_cols, deg_rows)

    # --- paper_tables.md ---
    md: List[str] = []
    md.append("# Paper Tables — Live Ollama Small Suite")
    md.append("")
    md.append(
        "Small-scale exploratory evaluation (4 tasks, 6 attack variants per config, "
        "`llama3.2:3b` via Ollama). Values rounded to three decimals for display."
    )
    md.append("")
    md.append("## Table A: Leakage")
    md.append("")
    md.append(
        "| System | Leakage ASR | Internal leakage | Final-output leakage | Clean task SR | Attacked task SR |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    for r in leak_rows:
        md.append(
            f"| {r['system']} | {_fmt3(r['leakage_asr'])} | {_fmt3(r['internal_leakage_rate'])} | "
            f"{_fmt3(r['final_output_leakage_rate'])} | {_fmt3(r['clean_task_success_rate'])} | "
            f"{_fmt3(r['attacked_task_success_rate'])} |"
        )

    md.append("")
    md.append("## Table B: External leakage")
    md.append("")
    md.append(
        "Task-success changes under external-leakage attacks (clean SR minus attacked SR) are a "
        "**task success side effect**, not primary degradation utility drop."
    )
    md.append("")
    md.append(
        "| System | External leakage ASR | Internal leakage | Final-output leakage | Clean task SR | Attacked task SR |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    for r in ext_rows:
        md.append(
            f"| {r['system']} | {_fmt3(r['external_leakage_asr'])} | {_fmt3(r['internal_leakage_rate'])} | "
            f"{_fmt3(r['final_output_leakage_rate'])} | {_fmt3(r['clean_task_success_rate'])} | "
            f"{_fmt3(r['attacked_task_success_rate'])} |"
        )

    md.append("")
    md.append("## Table C: Degradation")
    md.append("")
    md.append(
        "| System | Clean task SR | Attacked task SR | Utility drop | Operational degradation | "
        "Strongest family (utility drop) | Strongest family (operational) |"
    )
    md.append("|---|---:|---:|---:|---:|---|---|")
    for r in deg_rows:
        md.append(
            f"| {r['system']} | {_fmt3(r['clean_task_success_rate'])} | {_fmt3(r['attacked_task_success_rate'])} | "
            f"{_fmt3(r['utility_drop'])} | {_fmt3(r['operational_degradation_score'])} | "
            f"{r['strongest_family_by_utility_drop']} | {r['strongest_family_by_operational_score']} |"
        )

    (ANALYSIS / "paper_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # --- paper_table_values.md (exact values for LaTeX) ---
    lv: List[str] = []
    lv.append("# Paper Table Values (exact, for LaTeX)")
    lv.append("")
    lv.append("Source: `live_ollama_small_metrics.csv`, `degradation_family_metrics.csv`.")
    lv.append("")

    lv.append("## Table A — Leakage")
    lv.append("")
    for r in leak_rows:
        lv.append(f"### {r['system']}")
        lv.append(f"- leakage_asr = {_fmt_exact(r['leakage_asr'])}")
        lv.append(f"- internal_leakage_rate = {_fmt_exact(r['internal_leakage_rate'])}")
        lv.append(f"- final_output_leakage_rate = {_fmt_exact(r['final_output_leakage_rate'])}")
        lv.append(f"- clean_task_success_rate = {_fmt_exact(r['clean_task_success_rate'])}")
        lv.append(f"- attacked_task_success_rate = {_fmt_exact(r['attacked_task_success_rate'])}")
        lv.append("")

    lv.append("## Table B — External leakage")
    lv.append("")
    for r in ext_rows:
        lv.append(f"### {r['system']}")
        lv.append(f"- external_leakage_asr = {_fmt_exact(r['external_leakage_asr'])}")
        lv.append(f"- internal_leakage_rate = {_fmt_exact(r['internal_leakage_rate'])}")
        lv.append(f"- final_output_leakage_rate = {_fmt_exact(r['final_output_leakage_rate'])}")
        lv.append(f"- clean_task_success_rate = {_fmt_exact(r['clean_task_success_rate'])}")
        lv.append(f"- attacked_task_success_rate = {_fmt_exact(r['attacked_task_success_rate'])}")
        side = None
        if r["clean_task_success_rate"] is not None and r["attacked_task_success_rate"] is not None:
            side = r["clean_task_success_rate"] - r["attacked_task_success_rate"]
        lv.append(f"- task_success_side_effect (not degradation) = {_fmt_exact(side)}")
        lv.append("")

    lv.append("## Table C — Degradation (small)")
    lv.append("")
    for r in deg_rows:
        lv.append(f"### {r['system']}")
        lv.append(f"- clean_task_success_rate = {_fmt_exact(r['clean_task_success_rate'])}")
        lv.append(f"- attacked_task_success_rate = {_fmt_exact(r['attacked_task_success_rate'])}")
        lv.append(f"- utility_drop = {_fmt_exact(r['utility_drop'])}")
        lv.append(f"- operational_degradation_score = {_fmt_exact(r['operational_degradation_score'])}")
        lv.append(f"- strongest_family_by_utility_drop = {r['strongest_family_by_utility_drop']}")
        lv.append(f"- strongest_family_by_operational_score = {r['strongest_family_by_operational_score']}")
        lv.append("")

    lv.append("## Degradation family values (small, per system)")
    lv.append("")
    for system in ["LangGraph", "AgentDojo", "AutoGen official", "CrewAI official"]:
        lv.append(f"### {system}")
        for fam in [
            "verification_loop",
            "caution_abstention",
            "tool_overuse",
            "priority_conflict",
            "format_disruption",
            "memory_context_poisoning",
        ]:
            row = next(
                (
                    r
                    for r in families
                    if r["system"] == system and r["scale"] == "small" and r["family"] == fam
                ),
                None,
            )
            if not row or row.get("utility_drop", "") == "":
                continue
            lv.append(f"- {fam}:")
            lv.append(f"  - utility_drop = {_fmt_exact(_f(row['utility_drop']))}")
            lv.append(f"  - operational_degradation_score = {_fmt_exact(_f(row['operational_degradation_score']))}")
        lv.append("")

    if medium:
        lv.append("## Medium pilot — LangGraph degradation")
        lv.append("")
        lv.append(f"- clean_task_success_rate = {_fmt_exact(_f(medium['clean_task_success_rate']))}")
        lv.append(f"- attacked_task_success_rate = {_fmt_exact(_f(medium['attacked_task_success_rate']))}")
        lv.append(f"- utility_drop = {_fmt_exact(_f(medium['utility_drop']))}")
        lv.append(f"- tool_call_increase = {_fmt_exact(_f(medium['tool_call_increase']))}")
        lv.append("")

    lv.append("## LaTeX row snippets (rounded to 3 decimals)")
    lv.append("")
    lv.append("```latex")
    lv.append("% Leakage")
    for r in leak_rows:
        lv.append(
            f"{r['system']} & {_fmt3(r['leakage_asr'])} & {_fmt3(r['internal_leakage_rate'])} & "
            f"{_fmt3(r['final_output_leakage_rate'])} & {_fmt3(r['clean_task_success_rate'])} & "
            f"{_fmt3(r['attacked_task_success_rate'])} \\\\"
        )
    lv.append("% External leakage")
    for r in ext_rows:
        side = (r["clean_task_success_rate"] - r["attacked_task_success_rate"]) if r["clean_task_success_rate"] is not None else None
        lv.append(
            f"{r['system']} & {_fmt3(r['external_leakage_asr'])} & {_fmt3(r['internal_leakage_rate'])} & "
            f"{_fmt3(r['final_output_leakage_rate'])} & {_fmt3(r['clean_task_success_rate'])} & "
            f"{_fmt3(r['attacked_task_success_rate'])} \\\\"
        )
        lv.append(f"% task success side effect (not in table): {_fmt3(side)}")
    lv.append("% Degradation")
    for r in deg_rows:
        lv.append(
            f"{r['system']} & {_fmt3(r['clean_task_success_rate'])} & {_fmt3(r['attacked_task_success_rate'])} & "
            f"{_fmt3(r['utility_drop'])} & {_fmt3(r['operational_degradation_score'])} & "
            f"{r['strongest_family_by_utility_drop']} & {r['strongest_family_by_operational_score']} \\\\"
        )
    lv.append("```")
    lv.append("")

    (ANALYSIS / "paper_table_values.md").write_text("\n".join(lv) + "\n", encoding="utf-8")

    # --- paper_results_draft.md ---
    draft = _build_results_draft(leak_rows, ext_rows, deg_rows, families, medium)
    (ANALYSIS / "paper_results_draft.md").write_text(draft, encoding="utf-8")


def _build_results_draft(
    leak_rows: List[Dict[str, Any]],
    ext_rows: List[Dict[str, Any]],
    deg_rows: List[Dict[str, Any]],
    families: List[Dict[str, str]],
    medium: Optional[Dict[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Results Draft — Live Ollama Small-Suite Evaluation")
    lines.append("")
    lines.append(
        "*Draft for paper Results section. Wording reflects a small-scale exploratory evaluation; "
        "findings are preliminary evidence in this setting.*"
    )
    lines.append("")
    lines.append("## Experimental setting")
    lines.append("")
    lines.append(
        "We conducted a small-scale exploratory evaluation of live LLM red-teaming across four "
        "agent systems (LangGraph, AgentDojo, AutoGen official, CrewAI official) and three attack "
        "goals (leakage, external leakage, degradation). Each small configuration used four synthetic "
        "tasks, six attack variants, `llama3.2:3b` via Ollama, and a fixed random seed. Degradation "
        "configs employed six targeted degradation families (verification loop, caution/abstention, "
        "tool overuse, priority conflict, format disruption, memory/context poisoning). We include one "
        "medium-scale LangGraph degradation pilot (12 variants, 104 runs) using generic auto-research "
        "attacks for comparison."
    )
    lines.append("")
    lines.append("## Leakage results")
    lines.append("")
    lines.append(
        "In this setting, leakage attacks were highly effective across all four systems. "
        "Leakage ASR ranged from 0.958 (AgentDojo) to 1.000 (LangGraph, AutoGen official, CrewAI official). "
        "Internal leakage rates were consistently high (0.958–1.000), while final-output leakage rates "
        "were lower (0.083–0.458), suggesting that intermediate channels are more exposed than user-visible "
        "final answers. AgentDojo showed the strongest final-output filtering under leakage "
        "(final-output leakage rate 0.083 vs. internal 0.958). Task success remained at 1.000 for "
        "LangGraph and AgentDojo; AutoGen and CrewAI showed modest task-success side effects "
        "(attacked SR 0.917–0.958)."
    )
    lines.append("")
    lines.append("## External leakage results")
    lines.append("")
    lines.append(
        "External leakage attacks also propagated in this setting, though with lower ASR than internal "
        "leakage. LangGraph achieved the highest external leakage ASR (0.375) and the highest "
        "final-output leakage rate (0.375). CrewAI official showed the largest task-success side effect "
        "(clean SR 0.750, attacked SR 0.458; side effect 0.292), indicating that external-leakage "
        "pressure can degrade task completion even when the primary metric is exfiltration to final output. "
        "These values are reported separately from degradation utility drop."
    )
    lines.append("")
    lines.append("## Degradation results")
    lines.append("")
    lines.append(
        "Degradation was weaker than leakage in this small-scale sweep. Aggregate utility drop remained "
        "0.000 for LangGraph and AgentDojo. AutoGen official and CrewAI official each showed a small "
        "aggregate utility drop of 0.042 (clean SR 1.000, attacked SR 0.958). Operational degradation "
        "scores were generally low at the aggregate level, though LangGraph showed a non-zero operational "
        "signal (0.019) without a corresponding utility drop."
    )
    lines.append("")
    lines.append("## Degradation family analysis")
    lines.append("")
    lines.append(
        "Family-level analysis suggests that **priority conflict** was the strongest degradation family "
        "by utility drop in this setting (utility drop 0.250 on AutoGen official and CrewAI official). "
        "**Verification loop** produced the strongest operational degradation signal overall "
        "(operational score 0.139 on LangGraph; elevated cost amplification on AutoGen). "
        "Caution/abstention, tool overuse, format disruption, and memory/context poisoning did not "
        "produce clear utility-drop signal in this small sweep."
    )
    lines.append("")
    lines.append("## Medium pilot result")
    lines.append("")
    if medium:
        lines.append(
            f"The LangGraph medium degradation pilot (auto-research, 12 variants) remained at "
            f"utility_drop = {_fmt_exact(_f(medium['utility_drop']))} with clean and attacked task success "
            f"both 1.000. This preliminary evidence suggests that generic degradation attacks did not "
            f"scale in that setting, in contrast to the family-targeted small sweep on official runtimes."
        )
    lines.append("")
    lines.append("## Key findings")
    lines.append("")
    lines.append("- Leakage attacks were highly effective across all systems in this small-scale evaluation.")
    lines.append("- Internal leakage was consistently higher than final-output leakage.")
    lines.append("- AgentDojo showed strong final-output filtering under leakage.")
    lines.append("- LangGraph had the highest external leakage ASR.")
    lines.append("- Degradation was weaker than leakage at aggregate level.")
    lines.append("- Priority conflict was the strongest degradation family by utility drop.")
    lines.append("- Verification loop produced the strongest operational degradation signal.")
    lines.append(
        "- The LangGraph medium degradation pilot remained at utility_drop=0.0, suggesting that "
        "generic degradation attacks did not scale in that setting."
    )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- Small sample size (4 tasks, 6 variants) limits statistical confidence.")
    lines.append("- Single model (`llama3.2:3b`) and local Ollama runtime; results may not generalize.")
    lines.append("- Medium pilot used a different attack generator (auto-research vs. degradation families).")
    lines.append("- Smoke configurations were used for infrastructure validation only and are not included in these result tables.")
    lines.append("- Summarizer routing for external leakage in legacy CSV exports requires correction before final tables.")
    lines.append("- Findings are exploratory and should not be interpreted as final benchmark rankings.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    build_tables()
    print("Paper artifacts written to", ANALYSIS)
