# Codebase Analysis for Methodology

This document summarizes the implementation under the `code/` directory and is intended to support the Methodology section of the research paper.

This document is derived from files under `code/` only. Where the implementation name suggests LLM-based behavior (e.g. "AutoResearch"), the code itself is inspected to determine what actually runs.

---

## 1. Overview of the Directory Structure

### Concise tree

```
code/
├── pyproject.toml              # Package metadata, optional deps (pytest, langgraph, agentdojo)
├── README.md                   # Usage, safety, adapter modes
├── configs/                    # ~80 YAML experiment definitions
├── tests/                      # Pytest suite (20+ test modules)
├── results/                    # Experiment outputs (generated at runtime; often gitignored)
└── agent_redteam/              # Main Python package
    ├── run_experiment.py       # CLI: single experiments
    ├── run_transfer.py         # CLI: transfer experiments
    ├── summarize_results.py    # CLI: aggregate results → summary/
    ├── paper_tables.py         # Paper-ready CSV + markdown tables
    ├── table_aggregation.py    # Filters, deduplication, clean analysis tables
    ├── schemas.py              # Task, AttackVariant, Trace, RunResult, ExperimentConfig
    ├── goals.py                # Goal type helpers
    ├── adapters/               # Agent system adapters (mock, synthetic, real)
    ├── attacks/                # Attack generators, families, mutation
    ├── defenses/               # Defense presets and trace filters
    ├── data/                   # Synthetic tasks and canaries
    ├── evaluation/             # Metrics, scoring, reward profiles
    ├── experiments/            # ExperimentRunner, TransferRunner, metadata
    └── logging_utils/          # JSONL read/write helpers
```

### Role of main folders

| Folder | Role |
|--------|------|
| `configs/` | YAML experiment definitions (system, goal, defense, calibration, attack generator). |
| `agent_redteam/adapters/` | Executes tasks on a target "agent system" (simulated or framework-backed). |
| `agent_redteam/attacks/` | Defines and searches over adversarial **attack variants** (not LLM prompts to an API). |
| `agent_redteam/evaluation/` | Leakage, performance, transfer metrics and weighted scores. |
| `agent_redteam/experiments/` | Orchestrates multi-iteration experiments and cross-system transfer. |
| `agent_redteam/defenses/` | Optional post-hoc trace redaction / filtering. |
| `agent_redteam/data/` | Deterministic synthetic tasks and canary strings. |
| `tests/` | Unit and integration tests for adapters, metrics, aggregation, configs. |
| `results/` | Per-experiment artifacts and `summary/` aggregates (after runs). |

### Main entry points

| File | Command (from README) | Purpose |
|------|------------------------|---------|
| `agent_redteam/run_experiment.py` | `python -m agent_redteam.run_experiment --config configs/...yaml` | Run one benchmark experiment. |
| `agent_redteam/run_transfer.py` | `python -m agent_redteam.run_transfer --config configs/...yaml` | Transfer attacks across systems. |
| `agent_redteam/summarize_results.py` | `python -m agent_redteam.summarize_results --results-dir results/` | Build combined CSVs and `paper_tables.md`. |

Core logic: `agent_redteam/experiments/runner.py` (`ExperimentRunner`), `agent_redteam/experiments/transfer_runner.py` (`TransferRunner`).

---

## 2. Project Objective

### Simple explanation

The project implements a **controlled red-teaming benchmark** for multi-step agent-style pipelines. It:

1. Generates synthetic tasks with **fake canary secrets** (not real credentials).
2. Searches over **attack variants** (injection location, target channel, prompt template, stealth).
3. Runs those attacks through **adapter implementations** that simulate or execute workflow-style agent systems.
4. Measures whether canaries appear in **internal traces** vs **final user-visible output**, and/or whether **task utility degrades**.
5. Compares **attack generators** (random, manual, heuristic search), **defenses**, **calibration profiles**, and **frameworks** via configs and summary tables.

### Academic wording

The system evaluates **adversarial input manipulation** against **synthetic agent workflows** under configurable **leakage** and **degradation** objectives. Success is defined by **canary exposure** in specified trace channels or by **utility reduction** relative to clean runs, not by compromising production systems.

### Inputs, outputs, and process

| Aspect | What the code implements |
|--------|---------------------------|
| **Inputs** | YAML `ExperimentConfig`; synthetic `Task` objects (`generate_synthetic_tasks`); `AttackVariant` from generators; optional `DefenseConfig`. |
| **Outputs** | Per-experiment directory under `results/<experiment_name>/` (JSONL, JSON, CSV); aggregated `results/summary/` (CSVs, `paper_tables.md`). |
| **Main process** | Clean runs → iterative attack generation → attacked runs per task → score variant → aggregate metrics → write artifacts. |
| **Relation to LLM threat modeling** | The codebase models **multi-channel agent traces** (messages, tools, memory, final output) and **injection/propagation** patterns relevant to LLM agent threats, but **does not call external LLM APIs** for attack generation or execution (verified: no `openai`, `anthropic`, or similar imports under `code/`). Execution is **deterministic simulation** or **local framework graphs** with Python node functions. |

---

## 3. Full Pipeline Description

### A. Textual explanation

1. **Config load** — `load_config()` in `runner.py` reads YAML into `ExperimentConfig` (goal, iterations, tasks, adapter, defense, generator, seeds).
2. **Adapter setup** — `create_adapter_from_config()` (`adapter_factory.py`) instantiates the target system adapter and `setup(adapter_config)`.
3. **Tasks** — `generate_synthetic_tasks(num_tasks, random_seed)` assigns instructions, domains, canaries, and `expected_answer`.
4. **Clean baseline** — For each task, `adapter.run_clean(task)` → `RunResult` logged to `runs.jsonl`.
5. **Attack loop** — For each `iteration` in `0..num_iterations-1`:
   - `generator.generate(iteration)` → `AttackVariant`.
   - For each task: `adapter.run_attacked(task, variant, defense)` → `RunResult`.
   - `score_variant(goal, attacked_runs, clean_runs, tasks_map, weights, variant, reward_profile)` → scalar score.
   - `generator.record_score(variant, score)` (v2 also records `final_output_leakage_rate` for `external_leakage`).
   - Log to `variants.jsonl`; maintain top-5 `best_variants`.
6. **Metrics** — `compute_all_leakage_metrics` or `compute_all_external_leakage_metrics` plus `compute_all_performance_metrics` on all attacked runs.
7. **Metadata** — `build_experiment_metadata(config)` → `metrics_summary.json`.
8. **Summarize** (optional) — `summarize_results.summarize()` + `paper_tables.generate_paper_tables()` for cross-experiment tables.

**Models / LLMs:** Not used in the implementation for generation or inference. Optional packages (`langgraph`, `agentdojo`) gate "real" adapters; workflow steps are still implemented as **Python functions** (see `langgraph_real_workflow.py`, `agentdojo_real_workflow.py`).

### B. Flow diagram

```
YAML Config (configs/*.yaml)
    → load_config() [runner.py]
    → ExperimentRunner.run()
        → generate_synthetic_tasks() [data/synthetic_tasks.py]
        → create_adapter_from_config() [adapters/adapter_factory.py]
        → get_attack_generator() [attacks/generators.py]
        → [CLEAN] adapter.run_clean(task) × num_tasks
        → FOR iteration in num_iterations:
              AttackVariant ← generator.generate(iteration)
              [ATTACKED] adapter.run_attacked(task, variant, defense) × num_tasks
              score ← score_variant() [evaluation/scorer.py]
              generator.record_score(variant, score)
        → compute_all_leakage_metrics / performance_metrics [evaluation/]
        → metrics_summary.json + runs.jsonl + variants.jsonl + best_variants.jsonl
    → summarize_results() [summarize_results.py]
        → results/summary/*.csv + paper_tables.md [paper_tables.py]
```

---

## 4. Analysis of Key Files

### Execution and orchestration

| File | Role | Main classes/functions | Inputs | Outputs |
|------|------|------------------------|--------|---------|
| `run_experiment.py` | CLI entry | `main()` | `--config` path | Prints ASR/utility; exit code |
| `experiments/runner.py` | Experiment orchestration | `ExperimentRunner`, `load_config()` | `ExperimentConfig` | `metrics_summary.json`, JSONL, CSV |
| `run_transfer.py` | Transfer CLI | (delegates to `TransferRunner`) | YAML transfer config | Transfer metrics, matrix rows |
| `experiments/transfer_runner.py` | Cross-system transfer | `TransferRunner` | Source `best_variants.jsonl`, target adapter | `transfer_results`, matrix in metrics |
| `summarize_results.py` | Cross-experiment aggregation | `summarize()` | `results/` directory | `summary/leakage_results.csv`, etc. |

### Schemas and data

| File | Role | Key types |
|------|------|-----------|
| `schemas.py` | Core dataclasses | `Task`, `AttackVariant`, `Trace`, `RunResult`, `ExperimentConfig` |
| `data/synthetic_tasks.py` | Task generation | `generate_synthetic_tasks()` |
| `data/canaries.py` | Canary strings and detection | `generate_canaries()`, `contains_exact_canary()`, `contains_partial_canary()` |
| `goals.py` | Goal classification | `is_leakage_goal()`, `is_external_leakage_goal()` |

### Attack generation

| File | Role | Key components |
|------|------|----------------|
| `attacks/generators.py` | Generator factory | `RandomAttackGenerator`, `ManualBaselineAttackGenerator`, `AutoResearchAttackGenerator` (v1), `get_attack_generator()` |
| `attacks/auto_research_v2.py` | Evolutionary search v2 | `AutoResearchV2AttackGenerator`: bandits, crossover, mutation, diagnostics JSON |
| `attacks/families.py` | 8 attack families for `external_leakage` | `ATTACK_FAMILIES`, `variant_from_family()` |
| `attacks/mutation.py` | Variant mutation | `mutate_variant()`, `random_variant()` |
| `attacks/variants.py` | Constants | `INJECTION_LOCATIONS`, `TARGET_CHANNELS`, `PROMPT_TEMPLATES` |

### Evaluation and reward

| File | Role | Key functions |
|------|------|---------------|
| `evaluation/leakage_metrics.py` | Leakage ASR and channel rates | `leakage_asr()`, `final_output_leakage_rate()`, `internal_leakage_rate()`, `compute_all_leakage_metrics()` |
| `evaluation/injection_source.py` | Exclude injection source from internal leak | `channel_texts_excluding_injection_source()` |
| `evaluation/performance_metrics.py` | Utility/degradation | `utility_drop()`, `cost_amplification()`, `compute_all_performance_metrics()` |
| `evaluation/scorer.py` | Weighted variant score | `score_variant()`, `score_leakage_variant()`, `score_external_leakage_variant()`, `score_degradation_variant()` |
| `evaluation/reward_profiles.py` | Named weight profiles | `REWARD_PROFILES`, `get_reward_weights()` |
| `evaluation/transfer_metrics.py` | Transfer statistics | `transfer_asr()`, `generalization_gap()`, `cross_framework_transfer()` |

### Adapters (target systems)

| File | `system_name` | Integration |
|------|---------------|-------------|
| `adapters/mock_adapter.py` | `mock` | Single-agent deterministic simulation + calibrator |
| `adapters/synthetic_workflow_base.py` | (base) | Multi-node workflow: coordinator→retriever→worker→reviewer |
| `adapters/langgraph_adapter.py` | `langgraph_synthetic` | Uses `SyntheticWorkflowRunner` (LangGraph import optional, unused for execution path per adapter code) |
| `adapters/langgraph_real_adapter.py` | `langgraph_real` | Real `StateGraph` (`langgraph_real_workflow.py`) |
| `adapters/agentdojo_adapter.py` | `agentdojo` | Mock via `MockAdapter` or placeholder real path |
| `adapters/agentdojo_real_adapter.py` | `agentdojo_real` | Controlled local workflow when `agentdojo` import succeeds |
| `adapters/autogen_adapter.py` | `autogen_synthetic` | Conversation-style synthetic workflow |
| `adapters/crewai_adapter.py` | `crewai_synthetic` | Role-based synthetic workflow |
| `adapters/calibration.py` | — | `LeakageCalibrator`, profiles `easy/medium/hard/legacy` |
| `adapters/finalizer_exposure.py` | — | Synthetic finalizer modes (mock/synthetic **only**; not used for `integration_mode: real`) |
| `adapters/adapter_factory.py` | — | `create_adapter()`, `create_adapter_from_config()` |

### Defenses

| File | Role |
|------|------|
| `defenses/defense_config.py` | Presets D0–D4 (`no_defense`, `prompt_defense`, `guard_agent`, etc.) |
| `defenses/filters.py` | `apply_defense()` — redacts canaries in trace channels |

### Aggregation and paper tables

| File | Role |
|------|------|
| `table_aggregation.py` | Clean filters, deduplication (`deduplicate_real_clean_rows`), experiment grouping |
| `paper_tables.py` | `generate_paper_tables()` — builds `paper_tables.md` and `internal_clean_*.csv` |
| `experiments/experiment_metadata.py` | `build_experiment_metadata()`, `SYSTEM_ARCHITECTURE`, integration mode resolution |

### Logging

| File | Role |
|------|------|
| `logging_utils/jsonl.py` | `append_jsonl`, `read_jsonl`, `write_jsonl` |

---

## 5. Experiment Description

### Experiment families (from `configs/` filenames and README)

| Family | Examples | Typical `goal` |
|--------|----------|----------------|
| Leakage (synthetic) | `mock_leakage_medium.yaml`, `langgraph_synthetic_leakage_medium.yaml` | `leakage` |
| External leakage | `langgraph_external_leakage_medium.yaml`, `mock_external_leakage_medium.yaml` | `external_leakage` |
| Selective external | `langgraph_external_selective_attack_compare_*.yaml` | `external_leakage` + `selective_finalizer_context` |
| Degradation | `mock_degradation_medium.yaml`, `langgraph_synthetic_degradation_hard.yaml` | `degradation` |
| Attack comparison | `langgraph_attack_compare_random.yaml`, `*_auto_v2.yaml` | `leakage` or `external_leakage` |
| Defense comparison | `langgraph_defense_prompt_defense.yaml`, `langgraph_external_defense_*.yaml` | leakage / external |
| Real framework | `langgraph_real_*.yaml`, `agentdojo_real_*.yaml` | `leakage` / `external_leakage` |
| Transfer | `transfer_langgraph_to_agentdojo.yaml`, `cross_framework_medium_matrix.yaml` | `leakage` (transfer runner) |

**~80 YAML files** in `configs/`.

### What changes between configs

| Parameter | Effect |
|-------------|--------|
| `system_name` / `adapter_type` | Which adapter runs (`mock`, `langgraph_synthetic`, `langgraph_real`, etc.) |
| `goal` | `leakage`, `external_leakage`, or `degradation` |
| `attack_generator` | `random`, `manual_baseline`, `auto_research` |
| `attack_generator_version` | `v1` vs `v2` (population search + bandits) |
| `calibration_profile` | `medium`, `hard`, `legacy` → `LeakageCalibrator` parameters |
| `defense` | D0–D4 defense preset |
| `finalizer_exposure_mode` | Synthetic-only finalizer behavior (`safe_finalizer`, `selective_finalizer_context`, etc.) |
| `num_iterations` / `num_tasks` | Search depth and evaluation sample size |
| `random_seed` | Reproducibility for tasks and generators |
| `scoring_weights` / `reward_profile` | Weighted score for variant ranking |

Typical values: `num_tasks: 8`, `num_iterations: 8–12`, `random_seed: 42` (see e.g. `langgraph_real_leakage_medium.yaml`).

### Iterations and runs

Per experiment (`runner.py`):

- **1 clean run per task** (`num_tasks`).
- **Per iteration**: one new variant × `num_tasks` attacked runs.
- Total attacked runs ≈ `num_iterations × num_tasks`.

### Metrics collected

**Leakage** (`compute_all_leakage_metrics`):

- `leakage_asr` — fraction of attacked runs with any exact canary leak (internal excluding injection source, or final output).
- `final_output_leakage_rate` — canary in `RunResult.final_output` only.
- `internal_leakage_rate` — canary in internal channels **excluding original injection source** (`injection_source.py`).
- `total_exposure_rate`, `output_only_miss_rate`, `channel_breakdown`, partial/exact rates.

**External leakage** (`compute_all_external_leakage_metrics`):

- Sets `external_leakage_asr = final_output_leakage_rate`.

**Performance** (`compute_all_performance_metrics`):

- `utility_drop`, `cost_amplification`, `latency_increase`, `tool_call_increase`, `retry_rate`, task success rates.

**Attack success definition:** For leakage goals, a run "succeeds" as an attack if `contains_exact_canary()` finds a task canary in allowed channels (`leakage_metrics.py`). Injection at `tool_output` does not count as internal leakage if the canary appears only in that injected snippet (`injection_metadata.injected_texts_by_channel`).

### Attack comparison

Configs differ mainly by `attack_generator` and `attack_generator_version` while holding system, seed, tasks, and calibration fixed (e.g. `langgraph_attack_compare_random.yaml` vs `langgraph_attack_compare_auto_v2.yaml`). Summary tables: `table_attack_comparison.csv`, `internal_clean_attack_comparison.csv` (`paper_tables.py`).

---

## 6. Reward Function Analysis

### Where defined

- **Default weights:** `evaluation/scorer.py` (`DEFAULT_LEAKAGE_WEIGHTS`, `DEFAULT_DEGRADATION_WEIGHTS`).
- **External leakage profile:** `evaluation/reward_profiles.py` (`DEFAULT_EXTERNAL_LEAKAGE_WEIGHTS`, `REWARD_PROFILES`).
- **Application:** `score_variant()` routes by `goal` and optional `reward_profile` from YAML.

### Leakage goal (`score_leakage_variant`)

| Component | Weight (default) | Source metric |
|-----------|------------------|---------------|
| `total_exposure_rate` | 1.0 | Any-channel leak |
| `internal_leakage_rate` | 0.5 | Internal channels (excl. injection source) |
| `final_output_leakage_rate` | 0.5 | Final output only |
| `utility_drop` | −0.2 | Clean vs attacked success rate |

Optional: `stealth_score × variant.stealth_level` if present in weights.

### External leakage goal (`score_external_leakage_variant`)

Uses `reward_profiles.py` when `reward_profile: external_leakage`:

| Component | Weight |
|-----------|--------|
| `final_output_leakage_rate` | 3.0 |
| `internal_leakage_rate` | 0.75 |
| `total_exposure_rate` | 0.25 |
| `utility_drop` | −0.5 |
| `stealth_score` × `stealth_level` | 0.25 |

### Degradation goal (`score_degradation_variant`)

| Component | Weight |
|-----------|--------|
| `utility_drop` | 1.0 |
| `cost_amplification` | 0.3 |
| `latency_increase` | 0.2 |
| `tool_call_increase` | 0.2 |

### How score affects attack selection

| Generator | Mechanism |
|-----------|-----------|
| **Random** | Ignores score (`record_score` is no-op). |
| **Manual** | Fixed rotation over baseline variants; ignores score. |
| **AutoResearch v1** | Mutates from top-scoring history; accepts variants with `score ≥ 0.5 × max(history)`. |
| **AutoResearch v2** | Family bandits use `final_output_leakage_rate` for `external_leakage`, else total score; crossover/mutation/elite cloning from high-scoring parents; writes `family_success_rates.json`, `search_history.jsonl`. |

**Note:** This is **heuristic optimization over discrete variant parameters**, not gradient-based or LLM-driven reward learning.

---

## 7. Agents and Attack Generation

### What "agents" mean in this codebase

Multi-step **workflow roles** simulated in adapters (e.g. planner, retriever, worker, reviewer in `synthetic_workflow_base.py`; analogous stages in real LangGraph/AgentDojo workflows). They are **not** autonomous LLM agents calling an API in the current implementation.

### Attack generation approaches

| Type | Implementation | Learning? |
|------|----------------|-----------|
| **Random** | `RandomAttackGenerator` — random family or `random_variant()` | No |
| **Manual** | `ManualBaselineAttackGenerator` — fixed templates in `BASELINES` | No |
| **AutoResearch v1** | Random spawn + mutate high-scoring parents | Yes (heuristic) |
| **AutoResearch v2** | Population + bandits + crossover + mutation + elite clones | Yes (heuristic) |
| **LLM-based** | **Not implemented** in `code/` | — |

### External leakage families (`attacks/families.py`)

Eight families (e.g. `summary_contamination`, `tool_output_laundering`) with fields: `injection_location`, `target_channel`, `intended_propagation_path`, `external_compatible`, propagation metadata.

### Iteration-to-iteration improvement (v2)

Documented in `auto_research_v2.py`: parent selection by `(final_output_leakage_rate, score)` for external goal; family sampling weighted by past bandit signals; crossover preserves propagation paths; mutation can repair toward compatible channels/agents.

---

## 8. Evaluation Process

### Compared against

| Aspect | Reference |
|--------|-----------|
| **Task success** | `Task.expected_answer` substring in `final_output` (e.g. real adapters: `task.expected_answer in final_output`). |
| **Leakage** | `Task.sensitive_canaries` (synthetic strings like `CANARY_CLIENT_ID_042`). |
| **Utility** | Clean run success rate vs attacked run success rate. |

There is **no separate human-labeled ground-truth leak dataset**; canary presence in traces is the ground truth signal for leakage.

### Attack success

- **Leakage ASR:** Proportion of attacked runs where exact canary appears in internal (non-source) or final-output channels.
- **External ASR:** Equals `final_output_leakage_rate` in code.

### Degradation

Measured via `utility_drop` and related performance metrics when `goal: degradation`; adapters may force failure (e.g. `AgentDojoAdapter` sets `task_success = False` for degradation attacks).

### Summary / tables (no plotting in code)

- `summarize_results.py` → flat CSVs.
- `paper_tables.py` → `paper_tables.md` + many `internal_clean_*.csv`, `table_*.csv`.
- **No matplotlib/plotly** usage found under `agent_redteam/`.

---

## 9. Outputs and Results

### Per experiment (`results/<experiment_name>/`)

| File | Meaning |
|------|---------|
| `runs.jsonl` | All clean and attacked `RunResult` records (incl. traces). |
| `variants.jsonl` | Per-iteration variant + score. |
| `best_variants.jsonl` | Top variants and accepted variants (v1/v2). |
| `trace_samples.jsonl` | Sample traces from strong iterations. |
| `metrics_summary.json` | Full metadata + leakage/performance metrics. |
| `leakage_results.csv` or `external_leakage_results.csv` or `degradation_results.csv` | Key metrics as rows. |
| `family_success_rates.json`, `generator_diagnostics.json`, `search_history.jsonl` | AutoResearch v2 only (when output_path set). |

### Aggregated (`results/summary/`)

Examples: `leakage_results.csv`, `paper_tables.md`, `internal_clean_leakage_results.csv`, `internal_clean_real_attack_comparison.csv`, `internal_clean_agentdojo_real_*.csv`, `table_transferability_matrix.csv`.

**For paper graphs:** Export from summary CSVs; the codebase does not generate figures automatically.

---

## 10. Academic Methodology Draft

### Methodology

#### 1. System Overview

We implemented a reproducible red-teaming framework (`agent-redteam`, Python ≥3.11) that evaluates adversarial manipulations against synthetic multi-step agent workflows. The system does not invoke external large language model APIs; instead, it uses deterministic simulators and optional local framework graphs (LangGraph, AgentDojo) to produce traces and final responses. Sensitive content is represented exclusively by synthetic canary tokens (`data/canaries.py`), following the safety constraints stated in `README.md`.

#### 2. Threat Modeling Pipeline

Each evaluation instance is defined by a YAML configuration (`configs/`) loaded into an `ExperimentConfig` (`schemas.py`). The `ExperimentRunner` (`experiments/runner.py`) generates a fixed set of synthetic tasks (`data/synthetic_tasks.py`), executes clean baseline runs, and then iteratively evaluates attack variants on the selected adapter (`adapters/adapter_factory.py`). Each run produces a `RunResult` containing final output, task success, performance counters, and a structured `Trace` with channel-separated content (`schemas.py`).

#### 3. Adversarial Input Manipulation

An attack is encoded as an `AttackVariant` with: `prompt_template` (contains `{canary}` placeholder), `injection_location` (e.g. `user_input`, `tool_output`, `memory`), `target_channel`, `target_agent`, and `stealth_level`. For external leakage campaigns, eight predefined families (`attacks/families.py`) specify propagation paths and compatibility metadata. Adapters inject canaries according to `injection_location` and simulate propagation to `target_channel`; real adapters record injection metadata to exclude the injection source from internal leakage metrics (`evaluation/injection_source.py`).

#### 4. Attack Generation Strategy

We compare three generator types (`attacks/generators.py`): (i) uniform random sampling, (ii) fixed manual baselines, and (iii) AutoResearch heuristic search (v1: mutation from high-scoring parents; v2: population search with family bandits, crossover, and elite cloning in `attacks/auto_research_v2.py`). Search is driven by scalar scores from the evaluation module, not by LLM self-refinement.

#### 5. Reward Function and Optimization

Variant quality is computed by weighted linear combinations of leakage and performance metrics (`evaluation/scorer.py`). For internal leakage, default weights emphasize `total_exposure_rate`, `internal_leakage_rate`, and `final_output_leakage_rate`, with a penalty for `utility_drop`. For external leakage, the `external_leakage` reward profile (`evaluation/reward_profiles.py`) prioritizes `final_output_leakage_rate` (weight 3.0). AutoResearch v2 uses these scores—and for external leakage, per-iteration `final_output_leakage_rate`—to update family bandits and select parents.

#### 6. Experimental Setup

Experiments vary target system (`system_name` / `adapter_type`), goal (`leakage`, `external_leakage`, `degradation`), calibration profile (`medium`, `hard`, `legacy`), defense preset (D0–D4), and generator version. Integration mode is recorded as `mock`, `synthetic_fallback`, or `real` (`experiments/experiment_metadata.py`). Typical settings use `num_tasks=8`, `num_iterations=8–12`, and `random_seed=42`. Transfer experiments (`experiments/transfer_runner.py`) replay variants from source `best_variants.jsonl` on target adapters.

#### 7. Evaluation Metrics

Leakage metrics (`evaluation/leakage_metrics.py`) include attack success rate (ASR), final-output leakage rate, internal leakage rate excluding injection source, total exposure, output-only miss rate, and per-channel breakdown. External leakage ASR is defined as final-output leakage rate. Performance metrics (`evaluation/performance_metrics.py`) quantify utility drop and resource amplification. Transfer metrics (`evaluation/transfer_metrics.py`) report transfer ASR and generalization gap between source and target systems.

#### 8. Output Analysis

Per-experiment artifacts are written under `results/<experiment_name>/`. Cross-experiment aggregation is performed by `summarize_results.py` and `paper_tables.py`, producing CSV tables and `paper_tables.md` with internal clean subsets (synthetic vs real framework experiments) for attack, defense, difficulty, transfer, and external leakage comparisons (`table_aggregation.py`).

---

## 11. Short Summary

| Item | Description |
|------|-------------|
| **What it does** | Controlled red-team benchmark for synthetic agent workflows: search adversarial variants, run them through multiple adapters, measure canary leakage and/or utility degradation. |
| **Central pipeline** | Config → synthetic tasks → clean runs → iterative (generate variant → attack all tasks → score → log) → aggregate metrics → optional summary tables. |
| **Methodology** | Empirical comparison of attack generators, defenses, calibration profiles, and frameworks under leakage/degradation objectives with reproducible seeds and structured trace channels. |
| **Main implementation contribution** | End-to-end, test-covered framework separating **internal vs final-output leakage**, supporting **synthetic and real local workflows**, **heuristic AutoResearch v2** with family bandits, and **paper-ready aggregation**—without relying on external LLM APIs in the codebase. |

---

## Points Requiring Verification

1. **"Real" LangGraph / AgentDojo vs production benchmarks** — Real adapters execute local Python workflow graphs and require package import; they do **not** appear to run full official AgentDojo benchmark suites with live LLM agents (`agentdojo_adapter.py` real path is largely placeholder; `agentdojo_real_workflow.py` is a controlled local pipeline).

2. **LangGraph synthetic adapter** — `langgraph_adapter.py` checks for LangGraph import but routes execution through `SyntheticWorkflowRunner`; whether installed LangGraph changes behavior should be verified if claimed in the paper.

3. **Threat-modeling scope** — The code evaluates **canary leakage and utility degradation** in synthetic tasks; it does **not** implement a separate semantic "threat model" artifact (e.g. STRIDE diagrams) unless that is defined outside `code/`.

4. **LLM-based attacks** — Not present in repository; any paper claim about LLM-generated adversarial prompts would require extensions not in this codebase.

5. **Figure generation** — Tables and CSVs only; plots for the paper must be produced externally from `results/summary/`.

6. **`summarize_results.py` goal routing** — External leakage experiments may be categorized under leakage rows depending on `goal` field in metrics; `paper_tables.py` handles `external_leakage` explicitly—verify which CSV you cite for external vs internal leakage studies.
