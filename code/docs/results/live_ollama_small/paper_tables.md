# Paper Tables — Live Ollama Small Suite

Small-scale exploratory evaluation (4 tasks, 6 attack variants per config, `llama3.2:3b` via Ollama). Values rounded to three decimals for display.

## Table A: Leakage

| System | Leakage ASR | Internal leakage | Final-output leakage | Clean task SR | Attacked task SR |
|---|---:|---:|---:|---:|---:|
| LangGraph | 1.000 | 1.000 | 0.375 | 1.000 | 1.000 |
| AgentDojo | 0.958 | 0.958 | 0.083 | 1.000 | 1.000 |
| AutoGen official | 1.000 | 1.000 | 0.458 | 1.000 | 0.958 |
| CrewAI official | 1.000 | 1.000 | 0.292 | 1.000 | 0.917 |

## Table B: External leakage

Task-success changes under external-leakage attacks (clean SR minus attacked SR) are a **task success side effect**, not primary degradation utility drop.

| System | External leakage ASR | Internal leakage | Final-output leakage | Clean task SR | Attacked task SR |
|---|---:|---:|---:|---:|---:|
| LangGraph | 0.375 | 0.667 | 0.375 | 1.000 | 0.792 |
| AgentDojo | 0.167 | 0.958 | 0.167 | 1.000 | 1.000 |
| AutoGen official | 0.208 | 1.000 | 0.208 | 1.000 | 0.750 |
| CrewAI official | 0.292 | 0.917 | 0.292 | 0.750 | 0.458 |

## Table C: Degradation

| System | Clean task SR | Attacked task SR | Utility drop | Operational degradation | Strongest family (utility drop) | Strongest family (operational) |
|---|---:|---:|---:|---:|---|---|
| LangGraph | 1.000 | 1.000 | 0.000 | 0.019 | verification_loop | verification_loop |
| AgentDojo | 1.000 | 1.000 | 0.000 | 0.000 | verification_loop | verification_loop |
| AutoGen official | 1.000 | 0.958 | 0.042 | 0.021 | priority_conflict | priority_conflict |
| CrewAI official | 1.000 | 0.958 | 0.042 | 0.010 | priority_conflict | priority_conflict |
