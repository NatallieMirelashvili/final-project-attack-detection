# agent_redteam

Controlled AutoResearch-style red-teaming framework for LLM agent systems. This implementation runs fully end-to-end using a deterministic `MockAdapter` with synthetic canary secrets—no external LLM APIs or agent frameworks required.

## Integration modes (mock / synthetic fallback / real)

| Adapter | Default mode | Config | Requires install |
|---------|--------------|--------|------------------|
| `mock` | Deterministic local simulation | `adapter_type: mock` | No |
| `agentdojo` | Mock via `agentdojo_mock_mode: true` | `adapter_config.agentdojo_mock_mode` | No (mock); Yes (real) |
| `langgraph_synthetic` | Deterministic graph fallback | `adapter_type: langgraph_synthetic` | No; uses LangGraph if installed |
| `autogen_synthetic` | Deterministic conversation fallback | `adapter_type: autogen_synthetic` | No; style-compatible LLM path only |
| `crewai_synthetic` | Deterministic crew fallback | `adapter_type: crewai_synthetic` | No; style-compatible LLM path only |
| `autogen_official` | Official AutoGen agent-chat runtime | `adapter_type: autogen_official` | Yes — `pip install -e ".[autogen]"` |
| `crewai_official` | Official CrewAI Agent/Task/Crew runtime | `adapter_type: crewai_official` | Yes — `pip install -e ".[crewai]"` |

All YAML configs in `configs/` default to **synthetic/fallback** modes so experiments run without external frameworks. To use real integrations:

- **AgentDojo**: install AgentDojo per official docs, set `agentdojo_mock_mode: false` in `adapter_config`.
- **LangGraph real**: install LangGraph; `langgraph_real` uses a real LangGraph graph when `integration_mode: controlled` or `llm`.
- **AutoGen / CrewAI official**: install optional extras and use `autogen_official` / `crewai_official` (aliases `autogen_real`, `crewai_real`). These **require** the official packages and **never** fall back to style-compatible pipelines.
- **AutoGen / CrewAI style-compatible**: `autogen_synthetic` / `crewai_synthetic` with `integration_mode: llm` run local style-compatible LLM pipelines (`autogen_llm_workflow.py`, `crewai_llm_workflow.py`). These are **not** official-framework experiments.

Transfer experiments load **best variants** from source `best_variants.jsonl` and re-run those exact attack definitions on target adapters.

## Safety

- Uses only synthetic canary secrets (e.g. `CANARY_CLIENT_ID_042`)
- All attacks are simulated in a local mock benchmark environment
- No real credentials, users, or production systems are targeted
- No external data exfiltration

## Setup

```bash
cd code
pip install -e ".[dev]"
# Optional official framework integrations:
pip install -e ".[dev,autogen,crewai]"
```

## Run tests

```bash
pytest
```

## Run experiments

```bash
python -m agent_redteam.run_experiment --config configs/mock_leakage.yaml
python -m agent_redteam.run_experiment --config configs/mock_degradation.yaml
python -m agent_redteam.run_transfer --config configs/transfer_mock_to_mock.yaml
python -m agent_redteam.summarize_results --results-dir results/
```

### Local live LLM experiments with Ollama

Real-system adapters support **`integration_mode: llm`** with either deterministic mock agents (`llm_mode: mock`) or a **free local Ollama backend** (`llm_mode: live`, `llm_provider: ollama`).

Install and start [Ollama](https://ollama.com/), then pull the default small model:

```bash
ollama pull llama3.2:3b
```

Verify it responds:

```bash
ollama run llama3.2:3b
```

Optional lighter fallback if `llama3.2:3b` is too slow:

```bash
ollama pull llama3.2:1b
```

Set `llm_model: llama3.2:1b` in the YAML `adapter_config` section.

Run smoke experiments (2 tasks × 2 iterations):

```bash
cd code
python -m agent_redteam.llm.ollama_preflight
python -m agent_redteam.run_experiment --config configs/langgraph_real_llm_ollama_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/langgraph_real_llm_ollama_external_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/langgraph_real_llm_ollama_degradation_smoke.yaml
python -m agent_redteam.run_experiment --config configs/agentdojo_real_llm_ollama_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/agentdojo_real_llm_ollama_external_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/agentdojo_real_llm_ollama_degradation_smoke.yaml
python -m agent_redteam.run_experiment --config configs/autogen_official_llm_ollama_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/autogen_official_llm_ollama_external_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/autogen_official_llm_ollama_degradation_smoke.yaml
python -m agent_redteam.run_experiment --config configs/crewai_official_llm_ollama_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/crewai_official_llm_ollama_external_leakage_smoke.yaml
python -m agent_redteam.run_experiment --config configs/crewai_official_llm_ollama_degradation_smoke.yaml
python -m agent_redteam.summarize_results --results-dir results/
```

Canonical medium Ollama configs (`*_ollama_*_medium.yaml`) use `num_tasks: 8` and `num_iterations: 12` — run only after smoke succeeds and runtime is acceptable.

Example `adapter_config` for Ollama live mode:

```yaml
adapter_config:
  integration_mode: llm
  llm_mode: live
  llm_provider: ollama
  llm_model: llama3.2:3b
  ollama_base_url: http://localhost:11434
  temperature: 0.0
```

**LLM-backed systems** (shared `agent_runner` + mock or Ollama):

| System | Adapter | Mock configs | Ollama smoke configs |
|--------|---------|--------------|----------------------|
| LangGraph real | `langgraph_real` | `langgraph_real_llm_*_medium.yaml` | `langgraph_real_llm_ollama_*_smoke.yaml` |
| AgentDojo real | `agentdojo_real` | `agentdojo_real_llm_*_medium.yaml` | `agentdojo_real_llm_ollama_*_smoke.yaml` |
| AutoGen-style (local) | `autogen_synthetic` | `autogen_llm_*_medium.yaml` | `autogen_llm_ollama_*_smoke.yaml` |
| CrewAI-style (local) | `crewai_synthetic` | `crewai_llm_*_medium.yaml` | `crewai_llm_ollama_*_smoke.yaml` |
| AutoGen official | `autogen_official` | `autogen_official_llm_*_medium.yaml` | `autogen_official_llm_ollama_*_smoke.yaml` |
| CrewAI official | `crewai_official` | `crewai_official_llm_*_medium.yaml` | `crewai_official_llm_ollama_*_smoke.yaml` |

Set `integration_mode: llm` and `llm_mode: mock` for deterministic offline runs, or `llm_mode: live` with `llm_provider: ollama` for local Llama inference.

**Important:** Style-compatible AutoGen/CrewAI configs (`autogen_llm_*`, `crewai_llm_*`) mimic framework architecture locally. Only `autogen_official` and `crewai_official` use official framework runtimes (`RoundRobinGroupChat`, `crew.kickoff()`).

## Project structure

```
agent_redteam/
  adapters/       # Agent system adapters (MockAdapter)
  attacks/          # Attack generators and mutation
  defenses/         # Defense configs and filters
  evaluation/       # Leakage, performance, transfer metrics
  experiments/      # Experiment and transfer runners
  data/             # Synthetic tasks and canaries
  logging_utils/    # JSONL helpers
configs/            # YAML experiment configs
tests/              # Pytest suite
```

## Outputs

Each experiment writes to `results/<experiment_name>/`:

- `runs.jsonl` — all run records
- `variants.jsonl` — attack variants and scores per iteration
- `metrics_summary.json` — aggregated metrics
- `trace_samples.jsonl` — sample traces
- `best_variants.jsonl` — top-scoring variants
- `leakage_results.csv` or `degradation_results.csv`

Summarizer creates `results/summary/` with combined CSVs.

## Defenses

| ID | Name | Effect |
|----|------|--------|
| D0 | no_defense | Baseline |
| D1 | prompt_defense | Lowers leakage probability in adapter |
| D2 | guard_agent | Redacts final output |
| D3 | memory_or_inter_agent_redaction | Redacts internal messages and memory |
| D4 | tool_output_filtering | Redacts tool outputs |

## Attack generators

- `random` — random variant each iteration
- `manual_baseline` — fixed baseline variants
- `auto_research` — heuristic search with mutation of high-scoring variants

## Step 2: AgentDojo and LangGraph Synthetic Integration

Adapters:

- `AgentDojoAdapter` — AgentDojo benchmark integration (`agentdojo_mock_mode: true` runs without AgentDojo installed)
- `LangGraphSyntheticAdapter` — multi-agent workflow (Planner → Retriever → Worker → Reviewer) with deterministic fallback when LangGraph is not installed

```bash
cd code
pip install -e ".[dev]"
pytest

python -m agent_redteam.run_experiment --config configs/langgraph_synthetic_leakage.yaml
python -m agent_redteam.run_experiment --config configs/langgraph_synthetic_degradation.yaml
python -m agent_redteam.run_experiment --config configs/agentdojo_leakage.yaml
python -m agent_redteam.run_experiment --config configs/agentdojo_degradation.yaml

python -m agent_redteam.run_transfer --config configs/transfer_agentdojo_to_langgraph.yaml
python -m agent_redteam.run_transfer --config configs/transfer_langgraph_to_agentdojo.yaml
```

To switch AgentDojo configs to real mode, install AgentDojo per official instructions and set `agentdojo_mock_mode: false` in the YAML `adapter_config` section.

## Step 3: AutoGen, CrewAI, and Cross-Framework Transfer

Adapters:

- `AutoGenSyntheticAdapter` — coordinator / retriever / worker / reviewer conversation flow
- `CrewAISyntheticAdapter` — role-based crew workflow with task delegation

Both use deterministic fallbacks when AutoGen or CrewAI are not installed.

```bash
cd code
pip install -e ".[dev]"
pytest

python -m agent_redteam.run_experiment --config configs/autogen_synthetic_leakage.yaml
python -m agent_redteam.run_experiment --config configs/autogen_synthetic_degradation.yaml

python -m agent_redteam.run_experiment --config configs/crewai_synthetic_leakage.yaml
python -m agent_redteam.run_experiment --config configs/crewai_synthetic_degradation.yaml

python -m agent_redteam.run_transfer --config configs/transfer_agentdojo_to_autogen.yaml
python -m agent_redteam.run_transfer --config configs/transfer_agentdojo_to_crewai.yaml
python -m agent_redteam.run_transfer --config configs/transfer_langgraph_to_autogen.yaml
python -m agent_redteam.run_transfer --config configs/transfer_langgraph_to_crewai.yaml
python -m agent_redteam.run_transfer --config configs/transfer_cross_framework_matrix.yaml

python -m agent_redteam.summarize_results --results-dir results/
```

Paper-ready tables are written to `results/summary/` including `paper_tables.md` and CSV tables for leakage, degradation, defense tradeoffs, transferability, and best variants.

## Step 4: Calibration and Research-Ready Experiments

Synthetic adapters support YAML-configurable calibration via `calibration_profile` (`easy`, `medium`, `hard`, or `legacy`) and optional overrides:

- `attack_success_base_rate`, `stealth_bonus`, `defense_strength_multiplier`
- `channel_sensitivity`, `target_agent_sensitivity`
- `degradation_base_rate`, `noise_level`, `transfer_difficulty_penalty`

Profiles produce more realistic ASR spread than the default `legacy` aggressive simulation.

```bash
cd code
pip install -e ".[dev]"
pytest

python -m agent_redteam.run_experiment --config configs/langgraph_synthetic_leakage_medium.yaml
python -m agent_redteam.run_experiment --config configs/langgraph_synthetic_leakage_hard.yaml
python -m agent_redteam.run_transfer --config configs/cross_framework_medium_matrix.yaml
python -m agent_redteam.run_transfer --config configs/cross_framework_hard_matrix.yaml
python -m agent_redteam.summarize_results --results-dir results/
```

Attack comparison configs: `langgraph_attack_compare_{random,manual,auto}.yaml`, `agentdojo_attack_compare_{random,manual,auto}.yaml`

Defense comparison configs: `langgraph_defense_*.yaml`

Summary tables include `table_attack_comparison.csv`, `table_difficulty_comparison.csv`, and `table_defense_comparison.csv`.
