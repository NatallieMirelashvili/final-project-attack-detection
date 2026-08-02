# Live Ollama Small-Suite — Paper-Ready Artifacts

These files are **paper-ready derived artifacts** from the live Ollama small-scale evaluation. They summarize leakage, external leakage, and degradation results across four agent systems.

## Provenance

- **Source directory:** `code/results/analysis/` (generated locally; **ignored by git** via `code/.gitignore` → `results/`).
- **Raw experiment outputs:** remain untracked under `code/results/` (runs, metrics summaries, suite logs, etc.).
- **This directory:** tracked documentation copies intended for paper writing and review.

## Evaluation scope (small-scale exploratory)

| Dimension | Setting |
|-----------|---------|
| Systems | LangGraph, AgentDojo, AutoGen official, CrewAI official (4) |
| Goals | leakage, external_leakage, degradation (3) |
| Scale per small config | 4 tasks × 6 attack variants (28 runs, 6 variants) |
| Model | `llama3.2:3b` via Ollama |
| Random seed | 42 |

Findings are **preliminary evidence in this setting**, not definitive benchmark conclusions.

## Important caveats

1. **Smoke runs** (`*_smoke.yaml`) were infrastructure validation only and are **not** included in these tables.
2. **LangGraph degradation medium** (`langgraph_real_llm_ollama_degradation_medium`) is a **pilot only** (auto-research, 12 variants); compare cautiously to small family sweeps.
3. **`summarize_results` external-leakage routing** still misroutes external_leakage into `degradation_results.csv`. Paper tables here were built from per-experiment `metrics_summary.json` / analysis CSVs, not from that summarizer output. Fix summarizer routing before relying on automated paper tables from `results/summary/`.

## Files in this directory

| File | Description |
|------|-------------|
| `paper_tables.md` | Three separated paper tables (leakage / external / degradation) |
| `paper_results_draft.md` | Results-section draft with cautious wording |
| `paper_table_values.md` | Exact values and LaTeX snippets |
| `paper_leakage_table.csv` | Leakage table (CSV) |
| `paper_external_leakage_table.csv` | External leakage table (CSV) |
| `paper_degradation_table.csv` | Degradation table (CSV) |
| `live_ollama_small_results.md` | Full comparison report |
| `live_ollama_small_metrics.csv` | Main metrics (12 small + medium pilot) |
| `degradation_family_metrics.csv` | Per-family degradation breakdown |
| `medium_promotion_recommendations.md` | Medium-scale promotion priorities |

## Regenerating artifacts locally

From `code/` (requires completed experiments under `results/`):

```bash
python scripts/compile_small_report.py
python scripts/build_paper_tables.py
python scripts/qa_paper_artifacts.py
```

After regeneration, copy updated files from `results/analysis/` into this directory if you want tracked docs to match the latest local run.
