# Paper Audit and Required Revisions

## Purpose

This document contains a section-by-section audit of the paper against the work that was actually implemented and evaluated in the codebase.

For every section, it specifies:

- **Status**
- **Problem**
- **What to fix**
- **Suggested correction**

The central issue is not that the project lacks useful results. The main issue is that several parts of the manuscript currently describe a broader empirical evaluation than the one that was actually completed.

The completed study should be framed as a:

> **small-scale exploratory live-LLM evaluation of an AutoResearch-inspired red-teaming framework for agentic and multi-agent LLM systems.**

---

# Source of Truth: What Was Actually Evaluated

## Systems

The completed live evaluation covers:

1. **LangGraph real**
2. **AgentDojo real**
3. **AutoGen official**
4. **CrewAI official**

## Model

The live experiments use:

`llama3.2:3b`

through local **Ollama** execution.

The paper should not imply that multiple LLM models were evaluated.

## Attack Goals

Three goals were evaluated:

1. `leakage`
2. `external_leakage`
3. `degradation`

## Small-Scale Evaluation

Each small configuration uses:

- 4 tasks
- 6 attack variants
- 4 clean runs
- 24 attacked runs
- 28 total runs per configuration

There are:

- 4 systems
- 3 goals
- 12 small configurations total

## Medium Pilot

One additional medium experiment was completed:

- LangGraph
- degradation goal
- 104 runs
- 12 variants
- clean task success rate = 1.000
- attacked task success rate = 1.000
- utility drop = 0.000

This is a **pilot**, not a complete medium-scale benchmark.

## Smoke Experiments

Smoke runs are:

> infrastructure validation only

They should not be treated as research evidence.

## Latency

Latency is not a primary paper metric.

Raw latency may exist as diagnostic metadata, but `latency_increase` should not be used as a central cross-framework result.

## External Leakage Task-Success Effects

Task-success reductions that occur during the `external_leakage` experiments are:

> side effects of the external-leakage attack objective

They are **not degradation `utility_drop` results**.

---

# 0. Title Page

## Status

**Needs minor revision**

## Problem

The paper contains the placeholder:

`[complete others]`

This should not remain in the final manuscript.

## What to Fix

Either:

- fill in the missing information, or
- remove the placeholder.

## Suggested Fix

Remove it completely if no additional authors/advisors need to be listed.

---

# 1. Abstract

## Status

**Major mismatch**

## Problem

The Abstract currently appears to describe the study as if the completed empirical evaluation includes:

- AutoResearch vs. random attacks
- AutoResearch vs. manually designed attacks
- cross-framework transferability
- defense evaluation
- AutoResearch superiority
- cost amplification as a major result

The current Results section does not provide those comparisons.

The completed evidence instead consists primarily of:

- clean vs. attacked execution
- four systems
- three adversarial goals
- one local LLM
- small-scale exploratory evaluation
- one medium degradation pilot

## What to Fix

Rewrite the Abstract around the experiment that was actually completed.

The Abstract should clearly mention:

- LangGraph
- AgentDojo
- official AutoGen
- official CrewAI
- `llama3.2:3b`
- Ollama
- leakage
- external leakage
- degradation
- internal vs. final-output leakage
- degradation-family analysis

## Claims to Remove or Soften

Do not claim that the study demonstrates:

- AutoResearch outperforming random attacks
- AutoResearch outperforming manual attacks
- successful transferability across frameworks
- effectiveness of defenses
- definitive benchmark rankings

unless corresponding experimental results are added.

## Suggested Direction

Use wording similar to:

> This project proposes and evaluates an AutoResearch-inspired red-teaming framework for agentic and multi-agent LLM systems. We conduct a small-scale exploratory live-LLM evaluation using `llama3.2:3b` through Ollama across LangGraph, AgentDojo, official AutoGen, and official CrewAI.

Then summarize the actual findings:

- leakage is consistently effective
- internal leakage exceeds final-output leakage
- external leakage occurs in every evaluated framework
- degradation effects are weaker
- `priority_conflict` and `verification_loop` produce the clearest family-level degradation signals

---

# 2. Introduction

## Status

**Needs revision**

## Problem

The general motivation is good and is supported by the experiments.

In particular, the argument that:

> final-output-only evaluation can miss internal information exposure

is strongly supported by the results.

However, some parts of the Introduction may describe:

- baseline comparison
- transferability
- defenses

as empirical objectives that were completed.

## What to Keep

Keep the motivation around:

- internal agent communication
- memory
- tools
- intermediate messages
- internal-channel leakage
- limitations of final-output-only evaluation

These are central to the contribution.

## What to Fix

When describing the completed empirical study, focus on:

- effectiveness of generated attacks
- internal vs. final-output leakage
- cross-system differences
- degradation-family behavior

## Suggested Fix

Use wording such as:

> In the completed evaluation, we focus on whether internal-channel monitoring reveals exposure that final-output-only evaluation would miss, and on how leakage and degradation behavior differ across four agentic systems in a live local LLM setting.

Move transferability and defense evaluation to future work unless additional results are added.

---

# 3. Agentic and Multi-Agent LLM Systems

## Status

**Needs minor revision**

## Problem

The implementation status of the four systems is not identical.

The actual evaluated integrations are:

- LangGraph real
- AgentDojo real
- AutoGen official
- CrewAI official

The paper should not broadly call all four systems “official integrations.”

## What to Fix

Use precise terminology whenever the systems are introduced.

## Suggested Fix

Add:

> In the implementation, LangGraph and AgentDojo are evaluated through real adapters, while AutoGen and CrewAI use official runtime integrations.

---

# 4. AutoResearch-Style Optimization

## Status

**Needs revision**

## Problem

The paper describes a complete AutoResearch-style optimization process.

That is acceptable as a description of the framework architecture.

However, the current reported experiments do not establish that the optimization process:

- outperforms random generation
- outperforms manually designed attacks
- improves attack effectiveness over iterations

unless corresponding baseline or optimization-curve results are provided.

## What to Fix

Clearly separate:

### Framework capability

What the implementation supports.

from:

### Empirical finding

What was actually demonstrated in the reported experiments.

## Suggested Fix

Add wording such as:

> The current evaluation reports the behavior of the implemented attack-generation and family-based variants in a small-scale live setting. A full comparison against random and manually designed baselines is left for expanded evaluation.

If mutation, crossover, selection, or elite retention exist in the implementation, they can still be described.

But they should be described as:

> implemented framework capabilities

rather than proven sources of performance improvement.

---

# 5. Contributions

## Status

**Major mismatch**

## Problem

Some contributions currently appear to claim completed empirical work involving:

- transferability
- defense evaluation
- random baselines
- manual attack baselines
- superiority of AutoResearch attacks

Those claims are not represented in the current Results.

## What to Fix

Rewrite the contributions so every contribution is supported either by:

1. actual code implementation, or
2. completed experimental evidence.

## Recommended Contribution Set

### Contribution 1

An AutoResearch-inspired red-teaming framework for agentic and multi-agent LLM workflows.

### Contribution 2

Separate adversarial evaluation objectives for:

- information leakage
- external final-output leakage
- performance degradation

### Contribution 3

Channel-aware tracing that distinguishes:

- internal information exposure
- final user-visible exposure

### Contribution 4

A live local-LLM evaluation across:

- LangGraph
- AgentDojo
- official AutoGen
- official CrewAI

using `llama3.2:3b` via Ollama.

### Contribution 5

A degradation-family analysis demonstrating that:

- `priority_conflict` provides the clearest utility-drop signal
- `verification_loop` provides the clearest operational-degradation signal

## What to Remove or Move to Future Work

Move these out of the contribution list unless new experiments are added:

- transferability analysis
- defense comparison
- random baseline comparison
- manual baseline comparison
- claims that AutoResearch outperforms baselines

---

# 6. Related Work

## Status

**Mostly OK — requires verification**

## Problem

The conceptual Related Work section is generally acceptable.

However, recent references should be verified carefully.

In particular, references dated 2025–2026 should be checked for:

- correct title
- correct author list
- correct year
- correct venue
- actual existence
- correct relationship to the claim being cited

## What to Fix

Verify entries in `bib/references.bib`, especially recent work related to:

- AutoResearch
- AutoInject
- Slingshot
- recent LLM-agent security work

## Suggested Action

Do not broadly rewrite Related Work.

Instead, validate each citation against the sentence it supports.

---

# 7. Motivation and Goals / Research Questions

## Status

**Major mismatch**

## Problem

Some current Research Questions are not actually answered by the Results.

---

## RQ1 Problem

If the current RQ1 asks:

> Can AutoResearch-optimized attacks outperform random and manually designed baselines?

then the paper currently does not answer it.

There is no reported random/manual baseline comparison.

## Suggested RQ1

Replace it with:

> **RQ1:** How effective are automatically generated attack variants in exposing synthetic secrets, producing external leakage, and degrading task utility in live agentic LLM workflows?

---

## RQ2

## Status

**Strongly supported**

A question comparing:

- internal leakage
- final-output leakage

is directly supported by the results.

## Suggested RQ2

> **RQ2:** To what extent does final-output-only evaluation underestimate leakage compared with evaluation that also monitors internal channels?

---

## RQ3 Problem

If the current RQ3 asks:

> Do attacks optimized on one framework transfer to other frameworks?

then it is currently unanswered.

No transferability results are reported.

## Suggested RQ3

Replace it with:

> **RQ3:** How do leakage and degradation effects vary across different agentic orchestration frameworks?

## Alternative

If transferability is important to preserve, move the original RQ3 to:

> Future Work

rather than presenting it as a completed empirical question.

---

# 8. Threat Model

## Status

**Mostly OK**

## Problem

The general threat model is aligned with the implementation:

- synthetic canaries
- sandboxed tasks
- no real private data
- controlled adversarial input
- agent communication channels

The main detail to verify is whether every injection location described in the paper was actually exercised in every system.

## What to Fix

Do not imply that every attack location was tested in every framework unless that is true.

## Suggested Fix

Use:

> depending on the evaluated configuration

when listing possible adversarial injection points.

Also explicitly state:

> The canary secrets used in the study are synthetic measurement markers and do not represent real private information.

---

# 9. Attack Goals

## Status

**Needs minor revision**

## Problem

The paper needs a very clear distinction between:

1. general leakage
2. external leakage
3. degradation

`external_leakage` is not simply another degradation attack.

## What to Fix

Explicitly introduce external leakage as a separate evaluation objective.

Also make clear that task-success changes during external-leakage experiments are not degradation results.

## Suggested Fix

Add:

> In addition to general leakage, we evaluate an external-leakage objective that focuses specifically on whether sensitive content reaches the final user-visible output. Task-success changes observed under this objective are treated as side effects, not as degradation results.

---

# 10. Experimental Systems

## Status

**Needs minor revision**

## Problem

The manuscript may currently say that all four systems:

> implement the same workflow

too strongly.

The systems are configured to support comparison, but their actual orchestration and communication mechanisms differ.

## What to Fix

Use:

> approximate the same abstract workflow

instead of implying identical implementation.

## Suggested Fix

> To enable comparison, each system is configured to approximate the same abstract workflow while preserving the communication pattern and execution model of the underlying framework.

---

# 11. AutoResearch Red-Teaming Framework

## Status

**Needs revision**

## Problem

This section describes mechanisms such as:

- generation
- evaluation
- scoring
- selection
- mutation
- crossover
- elite retention
- family selection

These can be legitimate implementation details.

However, the Results do not demonstrate that every one of these mechanisms improved attack effectiveness.

## What to Fix

Separate framework design claims from empirical validation.

## Suggested Addition

> The current results focus on the live small-scale evaluation and degradation-family behavior. A full ablation of search strategies, including random and manual baselines, is outside the scope of the reported results.

---

## Leakage Optimization Subsection

## Problem

Avoid claiming:

> attacks improve across optimization iterations

unless the paper presents an optimization curve or generation-by-generation comparison.

## Suggested Fix

> Although the framework supports reward-guided selection, the present results report aggregate attack effectiveness rather than an iteration-by-iteration optimization curve.

---

## Performance Degradation Optimization Subsection

## Problem

Latency may currently appear too important.

## What to Fix

Latency should be diagnostic, not primary.

## Suggested Fix

> Latency is recorded only as a diagnostic signal and is not used as a primary cross-system comparison metric in the reported results.

---

# 12. Evaluation Metrics

## Status

**Major mismatch**

## Problem

The metrics table appears to contain metrics that are not actually reported in the completed study.

Examples include:

- Transfer ASR
- Generalization Gap
- Defense Leakage Reduction
- Utility Preservation under Defense
- False Refusal Rate
- Over-Defense Rate
- Attack Success Despite Guard
- Latency Increase

Keeping these in the primary evaluation table makes the empirical study appear broader than it actually is.

## What to Fix

The main table should primarily contain metrics actually reported in the paper.

---

## Leakage Metrics

Use:

- `leakage_asr`
- `internal_leakage_rate`
- `final_output_leakage_rate`

---

## External Leakage Metrics

Use:

- `external_leakage_asr`
- internal leakage rate
- final-output leakage rate

---

## Degradation Metrics

### Primary

- clean task success rate
- attacked task success rate
- `utility_drop`

### Secondary / Diagnostic

- tool-call increase
- retry rate
- loop/failure rate
- cost amplification
- final-output-empty rate
- operational degradation score

---

## Latency

Do not use `latency_increase` as a primary cross-system metric.

Raw latency may remain diagnostic metadata.

---

## Transferability and Defense Metrics

Either:

1. remove them from the current main metrics table;
2. move them to a “framework-supported metrics” subsection; or
3. explicitly mark them as:

> Not evaluated in the current study.

## Suggested Wording

> Table X lists the metrics reported in the current evaluation. Additional metrics such as transferability and defense effectiveness are supported by the broader framework but are not reported as empirical results in this paper.

---

# 13. Experimental Design

## Status

**Major mismatch**

## Problem

This is one of the largest inconsistencies in the manuscript.

The current section appears to describe:

- B0 Clean
- B1 Random
- B2 Manual
- B3 AutoResearch
- defenses D0–D4
- transfer experiments

But the current Results do not report these comparisons.

## What to Fix

Rewrite Experimental Design around the completed experiment.

## Correct Completed Experimental Design

The main evaluation contains:

- 4 systems
- 3 goals
- 1 model
- 4 tasks
- 6 variants
- 28 runs per configuration
- 12 small configurations

Plus:

- one LangGraph degradation medium pilot
- 104 runs
- 12 variants

## Suggested Replacement Text

> The completed evaluation consists of a small-scale live Ollama suite. Each configuration fixes the system, goal, task set, model, and attack-variant set. For each configuration, the runner executes four clean task runs and 24 attacked runs, corresponding to four tasks and six attack variants. The suite covers four systems and three goals: leakage, external leakage, and degradation. In addition, one medium-scale LangGraph degradation pilot evaluates 12 variants over 104 runs.

## Baselines / Defense / Transferability

If the implementation contains support for them, say:

> The implementation supports additional baseline, transfer, and defense configurations; however, these are not included in the reported live Ollama evaluation and are left for expanded evaluation.

## Recommended Experimental Matrix

| System | Implementation | Goals | Scale | Model |
|---|---|---|---|---|
| LangGraph | Real adapter | Leakage, external leakage, degradation | Small + medium degradation pilot | `llama3.2:3b` |
| AgentDojo | Real adapter | Leakage, external leakage, degradation | Small | `llama3.2:3b` |
| AutoGen | Official runtime | Leakage, external leakage, degradation | Small | `llama3.2:3b` |
| CrewAI | Official runtime | Leakage, external leakage, degradation | Small | `llama3.2:3b` |

---

# 14. Results

## Status

**Mostly correct**

## Problem

The Results section is currently one of the most accurate parts of the manuscript.

The numbers should not be broadly rewritten.

The main issues are:

- table placement
- LaTeX formatting
- terminology consistency
- explicit utility drop in the medium-pilot table
- possible duplication of limitations

## What to Keep

These findings are supported:

- leakage is highly effective
- internal leakage is higher than final-output leakage
- AgentDojo filters final output strongly
- LangGraph has the highest external leakage ASR
- degradation is weaker than leakage
- AutoGen and CrewAI show non-zero degradation utility drop
- `priority_conflict` is the strongest family by utility drop
- `verification_loop` produces the strongest LangGraph operational signal
- medium LangGraph degradation utility drop remains zero

---

## Table Placement

## Problem

A Results table appears before the actual Results section heading because LaTeX floats it there.

## What to Fix

Keep tables close to their relevant subsections.

Possible approaches:

- `[htbp]`
- `[H]` using the `float` package
- move the table declaration below the related explanatory paragraph

Do not change result values to solve layout issues.

---

## Identifier Formatting

Use `\texttt{}` consistently for:

- `llama3.2:3b`
- `verification_loop`
- `priority_conflict`
- `external_leakage`
- `auto_research`

---

## Medium Pilot Table

If it currently only shows clean and attacked SR, add:

> Utility Drop = 0.000

---

# 15. Discussion

## Status

**Major revision required**

## Problem

The current Discussion contains placeholder text and/or sections based on experiments that were not completed.

Potential unsupported topics include:

- AutoResearch vs. Manual Attacks
- Transferability Across Frameworks
- Defense Security-Utility Tradeoff

These sections should not remain in their current form.

## What to Fix

Replace the Discussion with actual interpretation of the completed results.

---

## 15.1 Final Output vs. Internal Exposure

Discuss:

- internal leakage is approximately 0.958–1.000 across systems
- final-output leakage is much lower
- AgentDojo is the clearest example
- final-output filtering does not imply that internal exposure did not occur
- output-only evaluation therefore underestimates risk

---

## 15.2 Why Leakage Was Stronger Than Degradation

Replace “AutoResearch vs. Manual Attacks” with something like:

> **Why Leakage Was Stronger Than Degradation**

Discuss:

- leakage only requires the canary to propagate
- degradation requires measurable disruption to utility or operations
- therefore degradation produced weaker signals
- `priority_conflict` created the clearest utility loss
- `verification_loop` created the clearest operational burden

---

## 15.3 Framework-Level Differences

Replace “Transferability Across Frameworks” with:

> **Framework-Level Differences**

Discuss:

### LangGraph

- highest external leakage ASR

### AgentDojo

- very high internal leakage
- very low final-output leakage
- evidence of strong final-stage filtering

### AutoGen

- highest final-output leakage under the general leakage goal
- small degradation utility loss

### CrewAI

- external leakage present
- task-success side effects under external leakage
- small degradation utility loss

Do not interpret these as definitive security rankings.

---

## 15.4 Implications for Evaluation

Replace unsupported defense discussion with:

> **Implications for Evaluation**

Discuss:

- internal traces need to be monitored
- leakage and degradation need separate metrics
- external leakage should be considered independently
- family-level degradation analysis is valuable
- output-only metrics are insufficient for agentic workflows

---

# 16. Limitations

## Status

**Needs expansion and consolidation**

## Problem

The limitations need to more explicitly bound the strength of the conclusions.

## What to Add

State clearly that:

- this is a small-scale exploratory evaluation
- only 4 tasks were used
- only 6 variants were used per small configuration
- only one model was evaluated
- the model was `llama3.2:3b`
- it was run through local Ollama
- smoke runs are infrastructure validation only
- only one medium pilot was completed
- the medium pilot covers LangGraph degradation only
- no definitive framework ranking is established
- random/manual superiority was not evaluated
- transferability was not evaluated
- defense effectiveness was not evaluated
- latency is not a primary comparison metric

## Interpretation Language

Avoid:

> System X is more secure than System Y.

Prefer:

> In this small-scale setting, System X exhibited lower final-output leakage than System Y.

Use cautious language such as:

- “in this setting”
- “preliminary evidence”
- “the current evaluation suggests”

---

# 17. Ethical Considerations

## Status

**Mostly OK**

## Problem

No major implementation mismatch is apparent.

The evaluation correctly uses:

- synthetic canaries
- no real private data
- sandboxed tasks
- no production systems

## What to Fix

If missing, add:

> The canary secrets used in the evaluation were synthetic markers created solely for measurement purposes.

---

# 18. Conclusion

## Status

**Major mismatch**

## Problem

The current Conclusion reportedly uses future-tense wording such as:

> The expected outcome is...

That is no longer appropriate because the experiments were completed.

The Conclusion may also imply that:

- transferability was tested
- defenses were tested
- baseline superiority was demonstrated

Those claims should be removed.

## What to Fix

Rewrite the Conclusion entirely in completed-study language.

## What the Conclusion Should Say

The paper implemented and evaluated:

- an AutoResearch-inspired red-teaming framework
- four agentic systems
- three attack goals
- a live local LLM evaluation

The main findings are:

- leakage is consistently effective
- internal leakage exceeds final-output leakage
- external leakage occurs in every system
- degradation is weaker
- AutoGen and CrewAI show small non-zero utility drop
- `priority_conflict` produces the clearest task-success degradation signal
- `verification_loop` produces the clearest operational degradation signal

Then state that:

- baseline comparison
- defense evaluation
- transferability
- larger model studies

remain future work.

## Suggested Ending

> These findings provide preliminary evidence that channel-aware evaluation is necessary for assessing the security of agentic LLM systems and motivate larger-scale studies of baseline comparisons, defenses, and cross-framework transferability.

---

# 19. Figures and Tables

## Status

**Needs formatting cleanup**

## Problems

Check for:

- tables floating before their section headings
- tables wider than the page
- inconsistent identifier formatting
- captions that require surrounding text to be understood

## What to Fix

- keep tables near their subsection
- use `\small` or `\scriptsize` when necessary
- use `\texttt{}` for code identifiers
- make captions self-contained
- avoid overflow
- do not modify numeric values for layout reasons

---

# 20. References

## Status

**Manual verification required**

## Problem

Recent references need careful checking.

In particular, manually verify recent references related to:

- AutoResearch
- AutoInject
- Slingshot
- 2025–2026 agent-security work

## What to Fix

Verify for every reference:

- title
- authors
- publication year
- publication venue
- DOI / URL / arXiv information
- whether the source actually supports the cited sentence

---

# 21. Global Claims That Must Be Removed or Softened

## Status

**High priority**

Unless additional empirical results are added, remove or soften statements claiming that:

- AutoResearch outperforms random attacks
- AutoResearch outperforms manually designed attacks
- cross-framework transferability was demonstrated
- defenses D0–D4 were evaluated
- cost amplification is a central result
- latency increase is a primary result
- this study establishes a definitive benchmark
- medium-scale evaluation was completed for all frameworks
- every degradation family was effective
- AgentDojo is “safe” or “robust” because final-output leakage is low

---

# 22. Claims That Are Fully Supported

## Status

**Keep**

These statements are supported by the completed experiments:

- Leakage attacks were highly effective across all four systems.
- Leakage ASR was at least 0.958 across evaluated systems.
- Internal leakage was substantially higher than final-output leakage.
- AgentDojo showed strong final-output filtering despite high internal leakage.
- LangGraph had the highest external leakage ASR in the small evaluation.
- Degradation was weaker than leakage.
- AutoGen official had degradation `utility_drop = 0.042`.
- CrewAI official had degradation `utility_drop = 0.042`.
- `priority_conflict` reached `utility_drop = 0.250` for AutoGen and CrewAI at family level.
- `verification_loop` produced LangGraph operational degradation score `0.139`.
- AgentDojo showed no meaningful degradation-family signal in this setting.
- LangGraph's medium degradation pilot retained `utility_drop = 0.000`.
- Final-output-only evaluation can underestimate exposure.

---

# 23. Correct Core Results

## Leakage

| System | Leakage ASR | Internal Leakage | Final-Output Leakage | Clean SR | Attacked SR |
|---|---:|---:|---:|---:|---:|
| LangGraph | 1.000 | 1.000 | 0.375 | 1.000 | 1.000 |
| AgentDojo | 0.958 | 0.958 | 0.083 | 1.000 | 1.000 |
| AutoGen official | 1.000 | 1.000 | 0.458 | 1.000 | 0.958 |
| CrewAI official | 1.000 | 1.000 | 0.292 | 1.000 | 0.917 |

## External Leakage

| System | External Leakage ASR | Internal Leakage | Final-Output Leakage | Clean SR | Attacked SR |
|---|---:|---:|---:|---:|---:|
| LangGraph | 0.375 | 0.667 | 0.375 | 1.000 | 0.792 |
| AgentDojo | 0.167 | 0.958 | 0.167 | 1.000 | 1.000 |
| AutoGen official | 0.208 | 1.000 | 0.208 | 1.000 | 0.750 |
| CrewAI official | 0.292 | 0.917 | 0.292 | 0.750 | 0.458 |

### Important Interpretation

Task-success drops here are **external-leakage side effects**.

They are not the degradation `utility_drop`.

## Degradation

| System | Clean SR | Attacked SR | Utility Drop | Operational Degradation |
|---|---:|---:|---:|---:|
| LangGraph | 1.000 | 1.000 | 0.000 | 0.019 |
| AgentDojo | 1.000 | 1.000 | 0.000 | 0.000 |
| AutoGen official | 1.000 | 0.958 | 0.042 | 0.021 |
| CrewAI official | 1.000 | 0.958 | 0.042 | 0.010 |

## Degradation Families

| System | Strongest Utility Signal | Utility Drop | Strongest Operational Signal | Operational Score |
|---|---|---:|---|---:|
| LangGraph | No utility signal | 0.000 | `verification_loop` | 0.139 |
| AgentDojo | No utility signal | 0.000 | No meaningful signal | 0.000 |
| AutoGen official | `priority_conflict` | 0.250 | `priority_conflict` | 0.089 |
| CrewAI official | `priority_conflict` | 0.250 | `priority_conflict` | 0.062 |

## Medium Pilot

| System / Goal | Runs | Variants | Clean SR | Attacked SR | Utility Drop |
|---|---:|---:|---:|---:|---:|
| LangGraph degradation | 104 | 12 | 1.000 | 1.000 | 0.000 |

---

# 24. The Baseline Issue

## Status

**Important clarification**

Not having a complete random/manual baseline comparison is **not automatically a serious flaw** for an exploratory final-project paper.

The real problem is claiming that such a comparison exists when it does not.

The completed evaluation already contains a valid baseline:

> **Clean execution**

Therefore, the study can compare:

- clean task success
- attacked task success

and calculate attack effects relative to clean behavior.

What the paper cannot currently claim is:

> AutoResearch attacks outperform random or manually designed attacks.

because that claim requires direct comparison data.

## Correct Framing

Use:

> We evaluate the effectiveness of generated attack variants in a small-scale live-LLM setting.

Do not use:

> We demonstrate that AutoResearch-optimized attacks outperform random and manually designed baselines.

Random/manual baselines can be future work.

---

# 25. Priority Order for Fixing the Paper

## Status

**Recommended revision sequence**

### Priority 1 — Abstract

Remove unsupported empirical claims.

### Priority 2 — Contributions

Make every contribution correspond to actual implementation/results.

### Priority 3 — Research Questions

Replace unanswered baseline/transfer questions with questions supported by the current evaluation.

### Priority 4 — Experimental Design

Rewrite it around the actual small live Ollama suite.

### Priority 5 — Evaluation Metrics

Remove or separate unsupported defense/transfer metrics.

### Priority 6 — Discussion

Replace placeholders with actual interpretation of the results.

### Priority 7 — Conclusion

Rewrite from future tense to completed-study findings.

### Priority 8 — Limitations

Explicitly describe the small scale, one model, and lack of baseline/defense/transfer experiments.

### Priority 9 — Results Formatting

Do not change numbers; fix table placement and terminology only.

### Priority 10 — References / Title Page

Verify references and remove placeholders.

---

# 26. Recommended Overall Paper Framing

The manuscript should consistently describe the study as:

> **a small-scale exploratory evaluation of an AutoResearch-inspired red-teaming framework for agentic and multi-agent LLM systems.**

Recommended language:

- “in this setting”
- “in the evaluated configurations”
- “preliminary evidence”
- “small-scale exploratory evaluation”
- “the current results suggest”
- “the framework supports, but the current study does not evaluate...”

Avoid unsupported language such as:

- “proves”
- “establishes”
- “definitively ranks”
- “demonstrates universal robustness”
- “outperforms random/manual baselines”
- “demonstrates transferability”

unless those experiments are actually added.

---

# Final Assessment

The paper does **not** need to be redesigned from scratch.

The Results section is already relatively well aligned with the completed experiments.

The main task is to make the rest of the paper accurately describe the scope of the evidence.

The highest-priority inconsistencies are:

1. Baseline superiority claims without baseline comparison.
2. Transferability claims without transfer experiments.
3. Defense claims without defense results.
4. Experimental Design describing experiments not present in Results.
5. Research Questions that the Results do not answer.
6. Placeholder Discussion sections.
7. Future-tense Conclusion.
8. Latency appearing as a primary metric.
9. External-leakage side effects being confused with degradation.
10. Small exploratory results being presented as a definitive benchmark.

Fixing these issues will align the manuscript with the implemented code and the completed experiments.