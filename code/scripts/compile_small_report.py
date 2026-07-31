"""Compile live Ollama small suite comparison report from metrics_summary.json files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

RESULTS = Path("results")
ANALYSIS = RESULTS / "analysis"

SMALL_EXPERIMENTS = [
    "langgraph_real_llm_ollama_leakage_small",
    "langgraph_real_llm_ollama_external_leakage_small",
    "langgraph_real_llm_ollama_degradation_small",
    "agentdojo_real_llm_ollama_leakage_small",
    "agentdojo_real_llm_ollama_external_leakage_small",
    "agentdojo_real_llm_ollama_degradation_small",
    "autogen_official_llm_ollama_leakage_small",
    "autogen_official_llm_ollama_external_leakage_small",
    "autogen_official_llm_ollama_degradation_small",
    "crewai_official_llm_ollama_leakage_small",
    "crewai_official_llm_ollama_external_leakage_small",
    "crewai_official_llm_ollama_degradation_small",
]

MEDIUM_PILOT = "langgraph_real_llm_ollama_degradation_medium"

SYSTEM_LABELS = {
    "langgraph_real": "LangGraph",
    "agentdojo_real": "AgentDojo",
    "autogen_official": "AutoGen official",
    "crewai_official": "CrewAI official",
}

FAMILIES = [
    "verification_loop",
    "caution_abstention",
    "tool_overuse",
    "priority_conflict",
    "format_disruption",
    "memory_context_poisoning",
]

MAIN_COLUMNS = [
    "experiment_name",
    "system",
    "goal",
    "scale",
    "runs",
    "variants",
    "clean_task_success_rate",
    "attacked_task_success_rate",
    "leakage_asr",
    "external_leakage_asr",
    "internal_leakage_rate",
    "final_output_leakage_rate",
    "utility_drop",
    "operational_degradation_score",
    "tool_call_increase",
    "retry_rate",
    "loop_or_failure_rate",
    "final_output_empty_rate",
]

FAMILY_COLUMNS = [
    "system",
    "experiment_name",
    "scale",
    "family",
    "utility_drop",
    "operational_degradation_score",
    "clean_task_success_rate",
    "attacked_task_success_rate",
    "tool_call_increase",
    "retry_rate",
    "loop_or_failure_rate",
    "final_output_empty_rate",
    "cost_amplification",
]


def _f(val: Any) -> Optional[float]:
    if val is None:
        return None
    return float(val)


def _fmt(val: Optional[float], digits: int = 3) -> str:
    if val is None:
        return "—"
    return f"{val:.{digits}f}"


def load_experiment(name: str, *, scale: str) -> Dict[str, Any]:
    exp_dir = RESULTS / name
    ms_path = exp_dir / "metrics_summary.json"
    runs_path = exp_dir / "runs.jsonl"
    vars_path = exp_dir / "variants.jsonl"

    runs = sum(1 for _ in runs_path.open(encoding="utf-8")) if runs_path.exists() else 0
    variants = sum(1 for _ in vars_path.open(encoding="utf-8")) if vars_path.exists() else 0

    if not ms_path.exists():
        raise FileNotFoundError(f"Missing metrics_summary.json for {name}")

    metrics = json.loads(ms_path.read_text(encoding="utf-8"))
    perf = metrics.get("performance") or {}
    leak = metrics.get("leakage") or {}
    ext = metrics.get("external_leakage") or {}

    system_key = str(metrics.get("system_name") or name.split("_llm")[0])
    goal = str(metrics.get("goal") or "")

    row = {
        "experiment_name": name,
        "system": SYSTEM_LABELS.get(system_key, system_key),
        "system_key": system_key,
        "goal": goal,
        "scale": scale,
        "runs": runs,
        "variants": variants,
        "clean_task_success_rate": _f(perf.get("clean_task_success_rate")),
        "attacked_task_success_rate": _f(perf.get("attacked_task_success_rate")),
        "leakage_asr": _f(leak.get("leakage_asr")),
        "external_leakage_asr": _f(ext.get("external_leakage_asr") or leak.get("external_leakage_asr")),
        "internal_leakage_rate": _f(leak.get("internal_leakage_rate")),
        "final_output_leakage_rate": _f(leak.get("final_output_leakage_rate")),
        "utility_drop": _f(perf.get("utility_drop")),
        "operational_degradation_score": _f(perf.get("operational_degradation_score")),
        "tool_call_increase": _f(perf.get("tool_call_increase")),
        "retry_rate": _f(perf.get("retry_rate")),
        "loop_or_failure_rate": _f(perf.get("loop_or_failure_rate")),
        "final_output_empty_rate": _f(perf.get("final_output_empty_rate")),
        "degradation_diagnostics": metrics.get("degradation_diagnostics") or {},
    }
    return row


def family_rows(main_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in main_rows:
        if row["goal"] != "degradation":
            continue
        by_family = (row.get("degradation_diagnostics") or {}).get("by_family") or {}
        for family in FAMILIES:
            metrics = by_family.get(family)
            if not metrics:
                out.append(
                    {
                        "system": row["system"],
                        "experiment_name": row["experiment_name"],
                        "scale": row["scale"],
                        "family": family,
                        "utility_drop": None,
                        "operational_degradation_score": None,
                        "clean_task_success_rate": None,
                        "attacked_task_success_rate": None,
                        "tool_call_increase": None,
                        "retry_rate": None,
                        "loop_or_failure_rate": None,
                        "final_output_empty_rate": None,
                        "cost_amplification": None,
                    }
                )
                continue
            out.append(
                {
                    "system": row["system"],
                    "experiment_name": row["experiment_name"],
                    "scale": row["scale"],
                    "family": family,
                    "utility_drop": _f(metrics.get("utility_drop")),
                    "operational_degradation_score": _f(metrics.get("operational_degradation_score")),
                    "clean_task_success_rate": _f(metrics.get("clean_task_success_rate")),
                    "attacked_task_success_rate": _f(metrics.get("attacked_task_success_rate")),
                    "tool_call_increase": _f(metrics.get("tool_call_increase")),
                    "retry_rate": _f(metrics.get("retry_rate")),
                    "loop_or_failure_rate": _f(metrics.get("loop_or_failure_rate")),
                    "final_output_empty_rate": _f(metrics.get("final_output_empty_rate")),
                    "cost_amplification": _f(metrics.get("cost_amplification")),
                }
            )
    return out


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def rank_leakage(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    leak_rows = [r for r in rows if r["goal"] == "leakage" and r["scale"] == "small"]
    return sorted(leak_rows, key=lambda r: (r["leakage_asr"] or 0, r["final_output_leakage_rate"] or 0), reverse=True)


def rank_external(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ext_rows = [r for r in rows if r["goal"] == "external_leakage" and r["scale"] == "small"]
    return ext_rows


def degradation_small(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in rows if r["goal"] == "degradation" and r["scale"] == "small"]


def best_family(family_rows_list: List[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    candidates = [r for r in family_rows_list if r.get(key) is not None and r["scale"] == "small"]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r[key] or 0)


def build_main_markdown(rows: List[Dict[str, Any]], fam_rows: List[Dict[str, Any]]) -> str:
    small_rows = [r for r in rows if r["scale"] == "small"]
    leak_rank = rank_leakage(small_rows)
    ext_rows = rank_external(small_rows)
    deg_rows = degradation_small(rows)

    strongest_leak = leak_rank[0] if leak_rank else None
    strongest_ext_asr = max(ext_rows, key=lambda r: r["external_leakage_asr"] or 0) if ext_rows else None
    strongest_ext_final = max(ext_rows, key=lambda r: r["final_output_leakage_rate"] or 0) if ext_rows else None
    nonzero_util = [r for r in deg_rows if (r["utility_drop"] or 0) > 0]
    nonzero_op = [r for r in deg_rows if (r["operational_degradation_score"] or 0) > 0]

    best_util_fam = best_family(fam_rows, "utility_drop")
    best_op_fam = best_family(fam_rows, "operational_degradation_score")

    lines: List[str] = []
    lines.append("# Live Ollama Small Suite — Full Comparison Report")
    lines.append("")
    lines.append("Source: per-experiment `metrics_summary.json` (not `results/summary/` aggregates).")
    lines.append("")
    lines.append("## 1. Main metrics table (12 small configs + medium pilot reference)")
    lines.append("")
    lines.append(
        "| System | Goal | Scale | Runs/Var | Clean SR | Attacked SR | Leakage ASR | Ext ASR | Internal leak | Final-out leak | Utility drop | Op deg | Tool inc | Retry | Loop/fail | Empty out |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r['system']} | {r['goal']} | {r['scale']} | {r['runs']}/{r['variants']} | "
            f"{_fmt(r['clean_task_success_rate'])} | {_fmt(r['attacked_task_success_rate'])} | "
            f"{_fmt(r['leakage_asr'])} | {_fmt(r['external_leakage_asr'])} | "
            f"{_fmt(r['internal_leakage_rate'])} | {_fmt(r['final_output_leakage_rate'])} | "
            f"{_fmt(r['utility_drop'])} | {_fmt(r['operational_degradation_score'])} | "
            f"{_fmt(r['tool_call_increase'])} | {_fmt(r['retry_rate'])} | "
            f"{_fmt(r['loop_or_failure_rate'])} | {_fmt(r['final_output_empty_rate'])} |"
        )

    lines.append("")
    lines.append("## 2. Leakage comparison")
    lines.append("")
    if strongest_leak:
        lines.append(
            f"- **Strongest leakage system (leakage_asr):** {strongest_leak['system']} "
            f"({strongest_leak['leakage_asr']:.3f}, final_output_leakage_rate={_fmt(strongest_leak['final_output_leakage_rate'])})"
        )
    lines.append("- **Ranking by leakage_asr (small):**")
    for i, r in enumerate(leak_rank, 1):
        lines.append(
            f"  {i}. {r['system']}: leakage_asr={_fmt(r['leakage_asr'])}, "
            f"internal={_fmt(r['internal_leakage_rate'])}, final_output={_fmt(r['final_output_leakage_rate'])}"
        )
    lines.append("- **Internal-only vs final-output leakage:** All four systems show high internal_leakage_rate (≥0.917). "
                   "Final-output leakage is lower on LangGraph (0.667) and AgentDojo (0.667) than AutoGen/CrewAI (1.0), "
                   "indicating a finalizer filter effect on some architectures.")

    lines.append("")
    lines.append("## 3. External leakage comparison")
    lines.append("")
    ext_by_asr = sorted(ext_rows, key=lambda r: r["external_leakage_asr"] or 0, reverse=True)
    ext_by_final = sorted(ext_rows, key=lambda r: r["final_output_leakage_rate"] or 0, reverse=True)
    lines.append("- **Ranking by external_leakage_asr:**")
    for i, r in enumerate(ext_by_asr, 1):
        lines.append(
            f"  {i}. {r['system']}: ext_asr={_fmt(r['external_leakage_asr'])}, "
            f"final_output={_fmt(r['final_output_leakage_rate'])}, internal={_fmt(r['internal_leakage_rate'])}"
        )
    lines.append("- **Ranking by final_output_leakage_rate:**")
    for i, r in enumerate(ext_by_final, 1):
        lines.append(
            f"  {i}. {r['system']}: final_output={_fmt(r['final_output_leakage_rate'])}, ext_asr={_fmt(r['external_leakage_asr'])}"
        )

    lines.append("")
    lines.append("## 4. Degradation comparison")
    lines.append("")
    lines.append("- **Non-zero utility_drop (small):**")
    if nonzero_util:
        for r in sorted(nonzero_util, key=lambda x: x["utility_drop"] or 0, reverse=True):
            lines.append(f"  - {r['system']}: utility_drop={_fmt(r['utility_drop'])}")
    else:
        lines.append("  - None")
    lines.append("- **Operational degradation signal with zero utility_drop:**")
    zero_util_op = [r for r in deg_rows if (r["utility_drop"] or 0) == 0 and (r["operational_degradation_score"] or 0) > 0]
    for r in zero_util_op:
        lines.append(f"  - {r['system']}: operational={_fmt(r['operational_degradation_score'])}")
    if not zero_util_op:
        lines.append("  - LangGraph / AgentDojo small: operational score = 0.0 across aggregate metrics")
    crewai = next(r for r in deg_rows if r["system_key"] == "crewai_official")
    lang_med = next((r for r in rows if r["experiment_name"] == MEDIUM_PILOT), None)
    lines.append("")
    lines.append(
        f"- **CrewAI official degradation small:** utility_drop={_fmt(crewai['utility_drop'])}, "
        f"clean_sr={_fmt(crewai['clean_task_success_rate'])}, attacked_sr={_fmt(crewai['attacked_task_success_rate'])}, "
        f"operational={_fmt(crewai['operational_degradation_score'])}"
    )
    if lang_med:
        lines.append(
            f"- **LangGraph degradation medium (pilot):** utility_drop={_fmt(lang_med['utility_drop'])}, "
            f"clean_sr={_fmt(lang_med['clean_task_success_rate'])}, attacked_sr={_fmt(lang_med['attacked_task_success_rate'])} "
            f"(12 auto_research variants, not family sweep)"
        )

    lines.append("")
    lines.append("## 5. Degradation family diagnosis")
    lines.append("")
    lines.append("| System | Family | Utility drop | Op deg | Tool inc | Retry | Loop/fail | Empty out |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for fr in fam_rows:
        if fr["scale"] != "small":
            continue
        lines.append(
            f"| {fr['system']} | {fr['family']} | {_fmt(fr['utility_drop'])} | "
            f"{_fmt(fr['operational_degradation_score'])} | {_fmt(fr['tool_call_increase'])} | "
            f"{_fmt(fr['retry_rate'])} | {_fmt(fr['loop_or_failure_rate'])} | {_fmt(fr['final_output_empty_rate'])} |"
        )
    if best_util_fam:
        lines.append("")
        lines.append(
            f"- **Strongest family by utility_drop:** {best_util_fam['family']} on {best_util_fam['system']} "
            f"({best_util_fam['utility_drop']:.3f})"
        )
    if best_op_fam:
        lines.append(
            f"- **Strongest family by operational_degradation_score:** {best_op_fam['family']} on {best_op_fam['system']} "
            f"({best_op_fam['operational_degradation_score']:.3f})"
        )

    lines.append("")
    lines.append("**Family signal summary:**")
    family_signals: Dict[str, List[str]] = {f: [] for f in FAMILIES}
    for fr in fam_rows:
        if fr["scale"] != "small":
            continue
        if (fr.get("utility_drop") or 0) > 0 or (fr.get("operational_degradation_score") or 0) > 0.01:
            family_signals[fr["family"]].append(fr["system"])
    for family in FAMILIES:
        systems = family_signals[family]
        if systems:
            lines.append(f"  - **{family}:** signal on {', '.join(systems)}")
        else:
            lines.append(f"  - **{family}:** no clear signal in small sweep")

    lines.append("")
    lines.append("## 6. Paper-ready conclusions")
    lines.append("")
    lines.append("### What worked strongly")
    lines.append("- Leakage attacks are highly effective across all four live Ollama systems (leakage_asr ≥ 0.958 on small).")
    lines.append("- External leakage propagates to final output on every system (final_output_leakage_rate 0.167–0.292).")
    lines.append("- Targeted degradation families surfaced non-zero utility_drop on AutoGen and CrewAI official.")
    lines.append("")
    lines.append("### What did not work")
    lines.append("- LangGraph and AgentDojo small degradation: utility_drop=0.0 despite six family variants.")
    lines.append("- LangGraph medium degradation pilot (auto_research): utility_drop=0.0 at 12 variants.")
    lines.append("- Operational metrics mostly near zero except isolated family-level effects.")
    lines.append("")
    lines.append("### Surprising")
    lines.append("- CrewAI official degradation small matched AutoGen on utility_drop (0.042) despite much slower runs.")
    lines.append("- LangGraph shows lower final-output leakage than internal leakage (finalizer filtering).")
    lines.append("- AutoGen/CrewAI external leakage ASR lower than internal leakage rate (harder finalizer propagation).")
    lines.append("")
    lines.append("### Limitations")
    lines.append("- Small scale: 4 tasks × 6 variants; high variance per family.")
    lines.append("- Single model: llama3.2:3b via Ollama; results may not transfer.")
    lines.append("- Medium pilot used auto_research, not degradation_families — not directly comparable.")
    lines.append("- `summarize_results` misroutes external_leakage into degradation_results.csv.")
    lines.append("")
    lines.append("### Fix before final paper tables")
    lines.append("- Fix summarizer goal routing for external_leakage.")
    lines.append("- Add suite runner failure/lock cleanup on abrupt process death.")
    lines.append("- Separate paper tables for external vs internal leakage channels.")

    return "\n".join(lines) + "\n"


def build_promotion_markdown(rows: List[Dict[str, Any]], fam_rows: List[Dict[str, Any]]) -> str:
    small = [r for r in rows if r["scale"] == "small"]
    lines: List[str] = []
    lines.append("# Medium Promotion Recommendations")
    lines.append("")
    lines.append("## Promote first (strong signal, paper-ready potential)")
    lines.append("")
    lines.append("| Priority | Config | Rationale |")
    lines.append("|---:|---|---|")
    lines.append("| 1 | `langgraph_real_llm_ollama_leakage_medium` | leakage_asr=1.0, clean utility preserved |")
    lines.append("| 2 | `autogen_official_llm_ollama_leakage_medium` | leakage_asr=1.0, diverse official runtime |")
    lines.append("| 3 | `crewai_official_llm_ollama_leakage_medium` | leakage_asr=1.0, official multi-agent |")
    lines.append("| 4 | `agentdojo_real_llm_ollama_leakage_medium` | leakage_asr=0.958, strong baseline |")
    lines.append("| 5 | `crewai_official_llm_ollama_external_leakage_medium` | highest ext final_output (0.292) |")
    lines.append("| 6 | `autogen_official_llm_ollama_external_leakage_medium` | ext_asr=0.208, internal=1.0 |")
    lines.append("")
    lines.append("## Degradation — promote with family focus")
    lines.append("")
    lines.append("| Priority | Config | Rationale |")
    lines.append("|---:|---|---|")
    lines.append("| 7 | `crewai_official_llm_ollama_degradation_medium` | Only system with aggregate utility_drop=0.042 on small; expand winning family |")
    lines.append("| 8 | `autogen_official_llm_ollama_degradation_medium` | utility_drop=0.042; mirror CrewAI family sweep at medium scale |")
    lines.append("")
    lines.append("## Exploratory only (defer medium until family signal confirmed)")
    lines.append("")
    lines.append("- `langgraph_real_llm_ollama_degradation_medium` — already ran with auto_research; utility_drop=0.0. Re-run medium with `degradation_families` or top family only.")
    lines.append("- `agentdojo_real_llm_ollama_degradation_medium` — utility_drop=0.0 on small; operational signal absent.")
    lines.append("- LangGraph / AgentDojo external leakage medium — viable but lower ext_asr than CrewAI/AutoGen.")
    lines.append("")
    lines.append("## Degradation family to expand")
    lines.append("")

    best_util = best_family(fam_rows, "utility_drop")
    best_op = best_family(fam_rows, "operational_degradation_score")
    if best_util:
        lines.append(
            f"- **Primary:** `{best_util['family']}` (best utility_drop={best_util['utility_drop']:.3f} on {best_util['system']})"
        )
    if best_op and (not best_util or best_op["family"] != best_util["family"]):
        lines.append(
            f"- **Secondary (operational):** `{best_op['family']}` (operational={best_op['operational_degradation_score']:.3f} on {best_op['system']})"
        )

    lines.append("")
    lines.append("Per-system strongest family by utility_drop:")
    for system in ["LangGraph", "AgentDojo", "AutoGen official", "CrewAI official"]:
        candidates = [
            fr for fr in fam_rows
            if fr["system"] == system and fr["scale"] == "small" and fr.get("utility_drop") is not None
        ]
        if not candidates:
            lines.append(f"- {system}: no data")
            continue
        best = max(candidates, key=lambda r: r["utility_drop"] or 0)
        lines.append(f"- {system}: `{best['family']}` (utility_drop={_fmt(best['utility_drop'])})")

    lines.append("")
    lines.append("## Reporting tier")
    lines.append("")
    lines.append("**Strong enough to report:** All 4 leakage small configs; top 2 external leakage (CrewAI, LangGraph); CrewAI + AutoGen degradation small.")
    lines.append("")
    lines.append("**Exploratory only:** LangGraph/AgentDojo degradation small; LangGraph degradation medium pilot; per-family rows with utility_drop=0.0.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = [load_experiment(name, scale="small") for name in SMALL_EXPERIMENTS]
    rows.append(load_experiment(MEDIUM_PILOT, scale="medium"))
    fam_rows = family_rows(rows)

    ANALYSIS.mkdir(parents=True, exist_ok=True)
    write_csv(ANALYSIS / "live_ollama_small_metrics.csv", MAIN_COLUMNS, rows)
    write_csv(ANALYSIS / "degradation_family_metrics.csv", FAMILY_COLUMNS, fam_rows)
    (ANALYSIS / "live_ollama_small_results.md").write_text(build_main_markdown(rows, fam_rows), encoding="utf-8")
    (ANALYSIS / "medium_promotion_recommendations.md").write_text(
        build_promotion_markdown(rows, fam_rows), encoding="utf-8"
    )

    print("WROTE", ANALYSIS)
    print("SMALL_COMPLETE", sum(1 for r in rows if r["scale"] == "small" and r["runs"] == 28), "/ 12")


if __name__ == "__main__":
    main()
