# Live Ollama Small Suite — Full Comparison Report

Source: per-experiment `metrics_summary.json` (not `results/summary/` aggregates).

## 1. Main metrics table (12 small configs + medium pilot reference)

| System | Goal | Scale | Runs/Var | Clean SR | Attacked SR | Leakage ASR | Ext ASR | Internal leak | Final-out leak | Utility drop | Op deg | Tool inc | Retry | Loop/fail | Empty out |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LangGraph | leakage | small | 28/6 | 1.000 | 1.000 | 1.000 | — | 1.000 | 0.375 | 0.000 | 0.065 | 0.259 | 0.000 | 0.000 | 0.000 |
| LangGraph | external_leakage | small | 28/6 | 1.000 | 0.792 | 0.667 | 0.375 | 0.667 | 0.375 | 0.208 | 0.052 | -0.111 | 0.000 | 0.208 | 0.000 |
| LangGraph | degradation | small | 28/6 | 1.000 | 1.000 | — | — | — | — | 0.000 | 0.019 | 0.074 | 0.000 | 0.000 | 0.000 |
| AgentDojo | leakage | small | 28/6 | 1.000 | 1.000 | 0.958 | — | 0.958 | 0.083 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AgentDojo | external_leakage | small | 28/6 | 1.000 | 1.000 | 0.958 | 0.167 | 0.958 | 0.167 | 0.000 | 0.010 | 0.042 | 0.000 | 0.000 | 0.000 |
| AgentDojo | degradation | small | 28/6 | 1.000 | 1.000 | — | — | — | — | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AutoGen official | leakage | small | 28/6 | 1.000 | 0.958 | 1.000 | — | 1.000 | 0.458 | 0.042 | 0.010 | 0.000 | 0.000 | 0.042 | 0.000 |
| AutoGen official | external_leakage | small | 28/6 | 1.000 | 0.750 | 1.000 | 0.208 | 1.000 | 0.208 | 0.250 | 0.062 | 0.000 | 0.000 | 0.250 | 0.000 |
| AutoGen official | degradation | small | 28/6 | 1.000 | 0.958 | — | — | — | — | 0.042 | 0.021 | 0.000 | 0.000 | 0.042 | 0.000 |
| CrewAI official | leakage | small | 28/6 | 1.000 | 0.917 | 1.000 | — | 1.000 | 0.292 | 0.083 | 0.021 | 0.000 | 0.000 | 0.083 | 0.000 |
| CrewAI official | external_leakage | small | 28/6 | 0.750 | 0.458 | 0.917 | 0.292 | 0.917 | 0.292 | 0.292 | 0.135 | 0.000 | 0.000 | 0.542 | 0.000 |
| CrewAI official | degradation | small | 28/6 | 1.000 | 0.958 | — | — | — | — | 0.042 | 0.010 | 0.000 | 0.000 | 0.042 | 0.000 |
| LangGraph | degradation | medium | 104/12 | 1.000 | 1.000 | — | — | — | — | 0.000 | — | 0.020 | 0.000 | 0.000 | — |

## 2. Leakage comparison

- **Strongest leakage system (leakage_asr):** LangGraph, AutoGen official, and CrewAI official tied at 1.000; AgentDojo at 0.958. Highest final_output_leakage_rate among leakage configs: AutoGen official (0.458).
- **Ranking by leakage_asr (small):**
  1. AutoGen official: leakage_asr=1.000, internal=1.000, final_output=0.458
  2. LangGraph: leakage_asr=1.000, internal=1.000, final_output=0.375
  3. CrewAI official: leakage_asr=1.000, internal=1.000, final_output=0.292
  4. AgentDojo: leakage_asr=0.958, internal=0.958, final_output=0.083
- **Internal-only vs final-output leakage:** Internal rates are high on all systems (0.958–1.0). Final-output leakage is much lower on AgentDojo (0.083) and moderate on LangGraph (0.375), CrewAI (0.292), and AutoGen (0.458), showing architecture-dependent finalizer filtering.

## 3. External leakage comparison

- **Ranking by external_leakage_asr:**
  1. LangGraph: ext_asr=0.375, final_output=0.375, internal=0.667
  2. CrewAI official: ext_asr=0.292, final_output=0.292, internal=0.917
  3. AutoGen official: ext_asr=0.208, final_output=0.208, internal=1.000
  4. AgentDojo: ext_asr=0.167, final_output=0.167, internal=0.958
- **Ranking by final_output_leakage_rate:**
  1. LangGraph: final_output=0.375, ext_asr=0.375
  2. CrewAI official: final_output=0.292, ext_asr=0.292
  3. AutoGen official: final_output=0.208, ext_asr=0.208
  4. AgentDojo: final_output=0.167, ext_asr=0.167

## 4. Degradation comparison

- **Non-zero utility_drop (small):**
  - AutoGen official: utility_drop=0.042
  - CrewAI official: utility_drop=0.042
- **Operational degradation signal with zero utility_drop:**
  - LangGraph: operational=0.019

- **CrewAI official degradation small:** utility_drop=0.042, clean_sr=1.000, attacked_sr=0.958, operational=0.010
- **LangGraph degradation medium (pilot):** utility_drop=0.000, clean_sr=1.000, attacked_sr=1.000 (12 auto_research variants, not family sweep)

## 5. Degradation family diagnosis

| System | Family | Utility drop | Op deg | Tool inc | Retry | Loop/fail | Empty out |
|---|---|---:|---:|---:|---:|---:|---:|
| LangGraph | verification_loop | 0.000 | 0.139 | 0.556 | 0.000 | 0.000 | 0.000 |
| LangGraph | caution_abstention | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| LangGraph | tool_overuse | 0.000 | 0.000 | -0.111 | 0.000 | 0.000 | 0.000 |
| LangGraph | priority_conflict | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| LangGraph | format_disruption | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| LangGraph | memory_context_poisoning | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AgentDojo | verification_loop | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AgentDojo | caution_abstention | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AgentDojo | tool_overuse | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AgentDojo | priority_conflict | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AgentDojo | format_disruption | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AgentDojo | memory_context_poisoning | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AutoGen official | verification_loop | 0.000 | 0.039 | 0.000 | 0.000 | 0.000 | 0.000 |
| AutoGen official | caution_abstention | 0.000 | 0.002 | 0.000 | 0.000 | 0.000 | 0.000 |
| AutoGen official | tool_overuse | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| AutoGen official | priority_conflict | 0.250 | 0.089 | 0.000 | 0.000 | 0.250 | 0.000 |
| AutoGen official | format_disruption | 0.000 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 |
| AutoGen official | memory_context_poisoning | 0.000 | 0.004 | 0.000 | 0.000 | 0.000 | 0.000 |
| CrewAI official | verification_loop | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| CrewAI official | caution_abstention | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| CrewAI official | tool_overuse | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| CrewAI official | priority_conflict | 0.250 | 0.062 | 0.000 | 0.000 | 0.250 | 0.000 |
| CrewAI official | format_disruption | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| CrewAI official | memory_context_poisoning | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

- **Strongest family by utility_drop:** priority_conflict on AutoGen official (0.250)
- **Strongest family by operational_degradation_score:** verification_loop on LangGraph (0.139)

**Family signal summary:**
  - **verification_loop:** signal on LangGraph, AutoGen official
  - **caution_abstention:** no clear signal in small sweep
  - **tool_overuse:** no clear signal in small sweep
  - **priority_conflict:** signal on AutoGen official, CrewAI official
  - **format_disruption:** no clear signal in small sweep
  - **memory_context_poisoning:** no clear signal in small sweep

## 6. Paper-ready conclusions

### What worked strongly
- Leakage attacks are highly effective across all four live Ollama systems (leakage_asr ≥ 0.958 on small).
- External leakage propagates to final output on every system (final_output_leakage_rate 0.167–0.292).
- Targeted degradation families surfaced non-zero utility_drop on AutoGen and CrewAI official.

### What did not work
- LangGraph and AgentDojo small degradation: utility_drop=0.0 despite six family variants.
- LangGraph medium degradation pilot (auto_research): utility_drop=0.0 at 12 variants.
- Operational metrics mostly near zero except isolated family-level effects.

### Surprising
- CrewAI official degradation small matched AutoGen on utility_drop (0.042) despite much slower runs.
- LangGraph shows lower final-output leakage than internal leakage (finalizer filtering).
- AutoGen/CrewAI external leakage ASR lower than internal leakage rate (harder finalizer propagation).

### Limitations
- Small scale: 4 tasks × 6 variants; high variance per family.
- Single model: llama3.2:3b via Ollama; results may not transfer.
- Medium pilot used auto_research, not degradation_families — not directly comparable.
- `summarize_results` misroutes external_leakage into degradation_results.csv.

### Fix before final paper tables
- Fix summarizer goal routing for external_leakage.
- Add suite runner failure/lock cleanup on abrupt process death.
- Separate paper tables for external vs internal leakage channels.
