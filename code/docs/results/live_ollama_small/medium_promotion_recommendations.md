# Medium Promotion Recommendations

## Promote first (strong signal, paper-ready potential)

| Priority | Config | Rationale |
|---:|---|---|
| 1 | `langgraph_real_llm_ollama_leakage_medium` | leakage_asr=1.0, clean utility preserved |
| 2 | `autogen_official_llm_ollama_leakage_medium` | leakage_asr=1.0, diverse official runtime |
| 3 | `crewai_official_llm_ollama_leakage_medium` | leakage_asr=1.0, official multi-agent |
| 4 | `agentdojo_real_llm_ollama_leakage_medium` | leakage_asr=0.958, strong baseline |
| 5 | `langgraph_real_llm_ollama_external_leakage_medium` | highest ext_asr and final_output (0.375) |
| 6 | `crewai_official_llm_ollama_external_leakage_medium` | ext final_output=0.292, highest loop/fail under attack (0.542) |
| 7 | `autogen_official_llm_ollama_external_leakage_medium` | ext_asr=0.208, internal=1.0 |

## Degradation — promote with family focus

| Priority | Config | Rationale |
|---:|---|---|
| 8 | `crewai_official_llm_ollama_degradation_medium` | utility_drop=0.042; priority_conflict family utility_drop=0.25 |
| 9 | `autogen_official_llm_ollama_degradation_medium` | utility_drop=0.042; priority_conflict family utility_drop=0.25 |

## Exploratory only (defer medium until family signal confirmed)

- `langgraph_real_llm_ollama_degradation_medium` — already ran with auto_research; utility_drop=0.0. Re-run medium with `degradation_families` or top family only.
- `agentdojo_real_llm_ollama_degradation_medium` — utility_drop=0.0 on small; operational signal absent.
- LangGraph / AgentDojo external leakage medium — viable but lower ext_asr than CrewAI/AutoGen.

## Degradation family to expand

- **Primary:** `priority_conflict` (best utility_drop=0.250 on AutoGen official)
- **Secondary (operational):** `verification_loop` (operational=0.139 on LangGraph)

Per-system strongest family by utility_drop:
- LangGraph: `verification_loop` (utility_drop=0.000)
- AgentDojo: `verification_loop` (utility_drop=0.000)
- AutoGen official: `priority_conflict` (utility_drop=0.250)
- CrewAI official: `priority_conflict` (utility_drop=0.250)

## Reporting tier

**Strong enough to report:** All 4 leakage small configs; top 2 external leakage (CrewAI, LangGraph); CrewAI + AutoGen degradation small.

**Exploratory only:** LangGraph/AgentDojo degradation small; LangGraph degradation medium pilot; per-family rows with utility_drop=0.0.

