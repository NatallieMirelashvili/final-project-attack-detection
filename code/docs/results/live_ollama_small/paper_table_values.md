# Paper Table Values (exact, for LaTeX)

Source: `live_ollama_small_metrics.csv`, `degradation_family_metrics.csv`.

## Table A — Leakage

### LangGraph
- leakage_asr = 1.0
- internal_leakage_rate = 1.0
- final_output_leakage_rate = 0.375
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 1.0

### AgentDojo
- leakage_asr = 0.9583333333333334
- internal_leakage_rate = 0.9583333333333334
- final_output_leakage_rate = 0.08333333333333333
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 1.0

### AutoGen official
- leakage_asr = 1.0
- internal_leakage_rate = 1.0
- final_output_leakage_rate = 0.4583333333333333
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 0.9583333333333334

### CrewAI official
- leakage_asr = 1.0
- internal_leakage_rate = 1.0
- final_output_leakage_rate = 0.2916666666666667
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 0.9166666666666666

## Table B — External leakage

### LangGraph
- external_leakage_asr = 0.375
- internal_leakage_rate = 0.6666666666666666
- final_output_leakage_rate = 0.375
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 0.7916666666666666
- task_success_side_effect (not degradation) = 0.20833333333333337

### AgentDojo
- external_leakage_asr = 0.16666666666666666
- internal_leakage_rate = 0.9583333333333334
- final_output_leakage_rate = 0.16666666666666666
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 1.0
- task_success_side_effect (not degradation) = 0.0

### AutoGen official
- external_leakage_asr = 0.20833333333333334
- internal_leakage_rate = 1.0
- final_output_leakage_rate = 0.20833333333333334
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 0.75
- task_success_side_effect (not degradation) = 0.25

### CrewAI official
- external_leakage_asr = 0.2916666666666667
- internal_leakage_rate = 0.9166666666666666
- final_output_leakage_rate = 0.2916666666666667
- clean_task_success_rate = 0.75
- attacked_task_success_rate = 0.4583333333333333
- task_success_side_effect (not degradation) = 0.2916666666666667

## Table C — Degradation (small)

### LangGraph
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 1.0
- utility_drop = 0.0
- operational_degradation_score = 0.018518518518518504
- strongest_family_by_utility_drop = verification_loop
- strongest_family_by_operational_score = verification_loop

### AgentDojo
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 1.0
- utility_drop = 0.0
- operational_degradation_score = 0.0
- strongest_family_by_utility_drop = verification_loop
- strongest_family_by_operational_score = verification_loop

### AutoGen official
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 0.9583333333333334
- utility_drop = 0.04166666666666663
- operational_degradation_score = 0.020826190701376895
- strongest_family_by_utility_drop = priority_conflict
- strongest_family_by_operational_score = priority_conflict

### CrewAI official
- clean_task_success_rate = 1.0
- attacked_task_success_rate = 0.9583333333333334
- utility_drop = 0.04166666666666663
- operational_degradation_score = 0.010416666666666666
- strongest_family_by_utility_drop = priority_conflict
- strongest_family_by_operational_score = priority_conflict

## Degradation family values (small, per system)

### LangGraph
- verification_loop:
  - utility_drop = 0.0
  - operational_degradation_score = 0.1388888888888889
- caution_abstention:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- tool_overuse:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- priority_conflict:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- format_disruption:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- memory_context_poisoning:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0

### AgentDojo
- verification_loop:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- caution_abstention:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- tool_overuse:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- priority_conflict:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- format_disruption:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- memory_context_poisoning:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0

### AutoGen official
- verification_loop:
  - utility_drop = 0.0
  - operational_degradation_score = 0.039325656728063735
- caution_abstention:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0022876126072872618
- tool_overuse:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- priority_conflict:
  - utility_drop = 0.25
  - operational_degradation_score = 0.08870291774052444
- format_disruption:
  - utility_drop = 0.0
  - operational_degradation_score = 0.00745513441940748
- memory_context_poisoning:
  - utility_drop = 0.0
  - operational_degradation_score = 0.004337597238313675

### CrewAI official
- verification_loop:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- caution_abstention:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- tool_overuse:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- priority_conflict:
  - utility_drop = 0.25
  - operational_degradation_score = 0.0625
- format_disruption:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0
- memory_context_poisoning:
  - utility_drop = 0.0
  - operational_degradation_score = 0.0

## Medium pilot — LangGraph degradation

- clean_task_success_rate = 1.0
- attacked_task_success_rate = 1.0
- utility_drop = 0.0
- tool_call_increase = 0.019607843137254832

## LaTeX row snippets (rounded to 3 decimals)

```latex
% Leakage
LangGraph & 1.000 & 1.000 & 0.375 & 1.000 & 1.000 \\
AgentDojo & 0.958 & 0.958 & 0.083 & 1.000 & 1.000 \\
AutoGen official & 1.000 & 1.000 & 0.458 & 1.000 & 0.958 \\
CrewAI official & 1.000 & 1.000 & 0.292 & 1.000 & 0.917 \\
% External leakage
LangGraph & 0.375 & 0.667 & 0.375 & 1.000 & 0.792 \\
% task success side effect (not in table): 0.208
AgentDojo & 0.167 & 0.958 & 0.167 & 1.000 & 1.000 \\
% task success side effect (not in table): 0.000
AutoGen official & 0.208 & 1.000 & 0.208 & 1.000 & 0.750 \\
% task success side effect (not in table): 0.250
CrewAI official & 0.292 & 0.917 & 0.292 & 0.750 & 0.458 \\
% task success side effect (not in table): 0.292
% Degradation
LangGraph & 1.000 & 1.000 & 0.000 & 0.019 & verification_loop & verification_loop \\
AgentDojo & 1.000 & 1.000 & 0.000 & 0.000 & verification_loop & verification_loop \\
AutoGen official & 1.000 & 0.958 & 0.042 & 0.021 & priority_conflict & priority_conflict \\
CrewAI official & 1.000 & 0.958 & 0.042 & 0.010 & priority_conflict & priority_conflict \\
```

