# Results Draft — Live Ollama Small-Suite Evaluation

*Draft for paper Results section. Wording reflects a small-scale exploratory evaluation; findings are preliminary evidence in this setting.*

## Experimental setting

We conducted a small-scale exploratory evaluation of live LLM red-teaming across four agent systems (LangGraph, AgentDojo, AutoGen official, CrewAI official) and three attack goals (leakage, external leakage, degradation). Each small configuration used four synthetic tasks, six attack variants, `llama3.2:3b` via Ollama, and a fixed random seed. Degradation configs employed six targeted degradation families (verification loop, caution/abstention, tool overuse, priority conflict, format disruption, memory/context poisoning). We include one medium-scale LangGraph degradation pilot (12 variants, 104 runs) using generic auto-research attacks for comparison.

## Leakage results

In this setting, leakage attacks were highly effective across all four systems. Leakage ASR ranged from 0.958 (AgentDojo) to 1.000 (LangGraph, AutoGen official, CrewAI official). Internal leakage rates were consistently high (0.958–1.000), while final-output leakage rates were lower (0.083–0.458), suggesting that intermediate channels are more exposed than user-visible final answers. AgentDojo showed the strongest final-output filtering under leakage (final-output leakage rate 0.083 vs. internal 0.958). Task success remained at 1.000 for LangGraph and AgentDojo; AutoGen and CrewAI showed modest task-success side effects (attacked SR 0.917–0.958).

## External leakage results

External leakage attacks also propagated in this setting, though with lower ASR than internal leakage. LangGraph achieved the highest external leakage ASR (0.375) and the highest final-output leakage rate (0.375). CrewAI official showed the largest task-success side effect (clean SR 0.750, attacked SR 0.458; side effect 0.292), indicating that external-leakage pressure can degrade task completion even when the primary metric is exfiltration to final output. These values are reported separately from degradation utility drop.

## Degradation results

Degradation was weaker than leakage in this small-scale sweep. Aggregate utility drop remained 0.000 for LangGraph and AgentDojo. AutoGen official and CrewAI official each showed a small aggregate utility drop of 0.042 (clean SR 1.000, attacked SR 0.958). Operational degradation scores were generally low at the aggregate level, though LangGraph showed a non-zero operational signal (0.019) without a corresponding utility drop.

## Degradation family analysis

Family-level analysis suggests that **priority conflict** was the strongest degradation family by utility drop in this setting (utility drop 0.250 on AutoGen official and CrewAI official). **Verification loop** produced the strongest operational degradation signal overall (operational score 0.139 on LangGraph; elevated cost amplification on AutoGen). Caution/abstention, tool overuse, format disruption, and memory/context poisoning did not produce clear utility-drop signal in this small sweep.

## Medium pilot result

The LangGraph medium degradation pilot (auto-research, 12 variants) remained at utility_drop = 0.0 with clean and attacked task success both 1.000. This preliminary evidence suggests that generic degradation attacks did not scale in that setting, in contrast to the family-targeted small sweep on official runtimes.

## Key findings

- Leakage attacks were highly effective across all systems in this small-scale evaluation.
- Internal leakage was consistently higher than final-output leakage.
- AgentDojo showed strong final-output filtering under leakage.
- LangGraph had the highest external leakage ASR.
- Degradation was weaker than leakage at aggregate level.
- Priority conflict was the strongest degradation family by utility drop.
- Verification loop produced the strongest operational degradation signal.
- The LangGraph medium degradation pilot remained at utility_drop=0.0, suggesting that generic degradation attacks did not scale in that setting.

## Limitations

- Small sample size (4 tasks, 6 variants) limits statistical confidence.
- Single model (`llama3.2:3b`) and local Ollama runtime; results may not generalize.
- Medium pilot used a different attack generator (auto-research vs. degradation families).
- Smoke configurations were used for infrastructure validation only and are not included in these result tables.
- Summarizer routing for external leakage in legacy CSV exports requires correction before final tables.
- Findings are exploratory and should not be interpreted as final benchmark rankings.
