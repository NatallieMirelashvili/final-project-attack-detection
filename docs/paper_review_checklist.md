# Paper Review Checklist — Peer Feedback (2026-08-07)

Source: review by peer **Ravit**, first received as a condensed Hebrew summary
(translated and organized into the P0–P3 list below), later followed up by
[`docs/RavitsRejects.md`](RavitsRejects.md) — Ravit's own fuller, English,
section-by-section audit from a separate conversation with her LLM of choice, same
review, more detail. Original focus in both: mismatches between what the paper
*claims* (abstract, contributions, RQs, Table 1 metrics, Section 8 experimental
design) and what `sections/results.tex` actually reports (clean vs.
AutoResearch-attacked only, on four systems, no random/manual baselines, no
defenses, no transfer).

**Consistency check (this pass):** `RavitsRejects.md` was read in full and cross-checked
against this checklist and against the current `.tex` files. No contradictions were
found between the two Ravit documents — `RavitsRejects.md` is a strict superset,
covering everything already listed here plus additional sections (title page,
Experimental Systems wording, Limitations, Results table detail, references,
Ethical Considerations) that the condensed Hebrew version didn't call out
individually. New items below (§ P1–P3, marked `(Ravit, RavitsRejects.md §N)`) were
added from that superset **after independently verifying each one against the
current section files** (grep/read), not copied on trust — a few of Ravit's
general "watch list" items (e.g. "AgentDojo is safe/robust," "every degradation
family was effective," "medium-scale evaluation completed for all frameworks")
turned out **not** to be live violations in the current text; those are noted as
cautions for the rewrite rather than as open findings.

Items are grouped by priority and ordered so that fixing earlier items shrinks the
scope of later ones — e.g. once the abstract/contributions/RQs are scoped down to
what was actually run, several "missing results" items become moot rather than
requiring new experiments. Check items off as they're resolved; each item carries a
`*(Peer: "...")*` tag quoting the original Hebrew feedback, or a
`*(Ravit, RavitsRejects.md §N)*` tag for items added from the fuller audit. The one
item marked 🚩 **[NOT FROM PEER — CLAUDE-FOUND]** did not come from Ravit at all —
it's a separate mismatch found while cross-checking the paper against the codebase,
included here because it's the same class of issue.

**Framing note (Ravit, `RavitsRejects.md` §24, "The Baseline Issue"):** not having a
full random/manual/defense/transfer comparison is not itself a flaw for an
exploratory final-project paper — clean-vs-attacked execution is already a valid
baseline. The actual problem this whole checklist is about is **claiming a broader
comparison exists when it doesn't**. Keep this in mind while working through the
list: most items below are fixed by rewording/rescoping claims, not by running new
experiments.

Cross-reference: [`CLAUDE.md`](../CLAUDE.md) "Baselines, defenses, experimental
matrix" and "Research questions" sections now state explicitly what was/wasn't run —
use that as the ground truth while working through this list.

---

## P0 — Claim/result mismatches (blocking; affects credibility of the whole paper)

- [x] **Abstract overclaims.** ✅ **Resolved.** Rewrote `sections/abstract.tex`:
  removed the transferability/random/manual-baseline/defense/"outperform" claims,
  replaced the "an LLM agent proposes attack variants" line with an accurate
  heuristic-search description (this was actually a **4th, previously uncatalogued
  location** of the LLM-agent miswording — not one of the 3 already listed in the
  Claude-found item below, in `abstract.tex` not `introduction.tex` — now fixed),
  named the model/systems/scale, and replaced the vague "highly effective" framing
  with the actual leakage ASR range (0.958–1.000). Deliberately did **not** add a
  "baselines/defenses/transfer implemented but not evaluated" disclaimer sentence
  to the abstract — decided that omission already solves the overclaiming problem,
  and an abstract-level disclaimer about untested capabilities reads as inviting
  scrutiny rather than resolving it; that content belongs in Limitations (still
  open, see P1 below). *(Peer: "Abstract חזק מדי")*
  🔖 **REVISIT AT END OF WRITING PASS:** the closing sentence went through several
  rounds (a "families vs. generic search" contrast was cut for sounding
  LLM-generated and for using undefined internal jargon in an abstract) and landed
  on: *"Degradation effects were weaker than leakage effects overall, though one
  attack targeting conflicting task priorities reduced task success by 25% on two
  of the four systems."* Come back to this once the rest of the paper (especially
  Results/Discussion) is finalized — it may read differently once
  `priority_conflict` has been properly introduced elsewhere, and is worth a fresh
  look rather than treating it as permanently settled.
- [x] **Contributions list doesn't match results.** ✅ **Resolved.** Removed the
  old bullet 5 (clean/random/manual baseline + defense comparison) entirely rather
  than reframing it as future work — same reasoning as the abstract: a
  Contributions list should state what was delivered, not inventory unevaluated
  capabilities. Also trimmed bullet 4's "study whether attacks optimized on one
  framework transfer to the others" clause (no transfer results exist) down to
  "so that leakage and degradation behavior can be compared across frameworks"
  (which `results.tex` §Cross-System Comparison actually does support). Left with
  4 solid, fully-supported contributions instead of 5 with one weak/unsupported
  one. *(Peer: "Contributions לא תואמות לתוצאות")*
- [x] 🚩 **[NOT FROM PEER — CLAUDE-FOUND]** `sections/introduction.tex` misdescribed
  attack generation as an LLM agent, in **three** separate places (a 4th, in
  `abstract.tex`, was found and fixed earlier — see the Abstract item above). ✅
  **Resolved**, all 4 locations now fixed:
  (1) opening paragraph — "a heuristic search procedure generates an attack
  variant..." (also dropped an unsupported "more effectively than random or
  manually designed attacks" comparison clause in the same paragraph, and a
  "Rather than hand-crafting..." contrastive opener flagged as sounding
  LLM-generated);
  (2) §AutoResearch-Style Optimization — reworded to "replacing the LLM-agent edit
  step with a heuristic search procedure... using mutation, crossover, and
  family-based selection" (also fixed a pre-existing grammar break: "attack
  variants changes to the injected content... That increase a chosen metric" was
  never a complete sentence);
  (3) §Contributions bullet 1 — "a heuristic search procedure iteratively
  generates, evaluates, and selects attack variants."
  Verified during the fix: the "requires no gradient access... can be applied
  directly to closed, black-box agentic systems" claim in (2) survives the reword
  and is actually correct — confirmed the search code never touches model
  weights/gradients for *either* the target system *or* the attack generator
  itself (no trainable model exists at all), which is a stronger black-box
  guarantee than GRPO/CISPO can claim (they still need gradient access to the
  attacker model being fine-tuned, even against a black-box target).
  Left the *general* AutoResearch pattern description (`\cite{autoresearch}`,
  describing the outside inspiration, not this project's generator) as
  LLM-agent-driven — that one is accurate. *(Claude-found, not from peer review —
  verify before treating as confirmed feedback.)*
- [x] **RQ1 is asked but not answered.** ✅ **Resolved**, via a full 3-RQ
  restructure of `sections/research_goal.tex` rather than a narrow patch:
  - **RQ1** now reads: *"How effectively do AutoResearch-generated attacks expose
    synthetic secrets through internal channels compared with the final output,
    and what does this reveal about the risk of final-output-only evaluation?"*
    This merges the old RQ1's leakage-effectiveness half with the old RQ2's
    internal-vs-output question, on the finding (surfaced while doing this) that
    the small-scale **leakage/external-leakage** results genuinely come from
    `auto_research` v2's mutation/crossover/bandit search — so "AutoResearch" is
    an earned label there, unlike for degradation (see RQ2).
  - **RQ2** (was: output-only underestimation, now folded into RQ1) is now:
    *"How effective are the attacks generated by the framework at degrading task
    utility across agentic and multi-agent LLM systems?"* — deliberately **not**
    labeled "AutoResearch-generated," because the small-scale degradation family
    results (the `priority_conflict`/`verification_loop` numbers) come from
    `attack_generator: degradation_families`, which just cycles through 6
    hand-written templates once each with **no mutation, crossover, or score
    feedback at all** — mechanically equivalent to a human manually running 6
    pre-written attacks. Attributing that result to "AutoResearch" would have
    been a new instance of the same overclaiming pattern this checklist exists
    to catch. (Verified: the *medium-scale* degradation pilot does use real
    `auto_research` v2 search, but found nothing, 0.0 utility drop.)
  - Removed the stale commented-out alternate RQ3 (referenced defenses, no
    longer relevant).
  *(Peer: "RQ1 ... לא באמת נענות")*
- [x] **RQ3 is asked but not answered.** ✅ **Resolved** as part of the same
  restructure — **RQ3** now reads: *"How do leakage and degradation effects vary
  across different agentic and multi-agent orchestration frameworks?"*, matching
  the cross-system comparison `results.tex` §Cross-System Comparison actually
  supports, and matching the Contributions bullet 4 wording from the earlier fix.
  *(Peer: "RQ3 ... לא באמת נענות")*
- [x] **Section 8 (experimental design) reads as already executed.** ✅
  **Resolved**, via a full rewrite rather than adding a disclaimer — extensive
  back-and-forth on this one, worth recording the reasoning since it sets
  precedent for later sections:
  - Removed the B0–B3 baselines subsection, D0–D4 defenses subsection, and the
    old aspirational matrix table entirely, rather than keeping them with an
    "implemented but not evaluated" caveat — consistent with the same call made
    for the Abstract and Contributions.
  - Dropped $D$ from the formalization: went from $E=(S,G,A,D,T)$ to
    $E=(S,G,A,T)$, on the reasoning that keeping an unexplained `D` symbol next
    to three dimensions that *do* vary silently reintroduces the same overclaim
    the prose cut was removing, just moved into notation. "No defense is applied
    in any reported run" is stated as a plain fact instead.
  - Kept $T$, but reframed around *why* tasks are held constant: within a given
    scale, every system/goal is evaluated against the identical fixed,
    deterministic task set (confirmed in code — `generate_synthetic_tasks` is
    pure index arithmetic, no randomness), which is what makes the cross-system
    comparison valid. Medium-scale extends (doesn't replace) the small-scale
    tasks. Verified `T`'s *content* never varies but its *size* (`num_tasks`) is
    a real per-experiment parameter (4 vs. 8) — worth knowing if this section is
    revisited, since it's an easy place to overcorrect into "nothing about T
    varies," which isn't quite right either.
  - New matrix table (9 rows) replaces the old 4-row aspirational one, and is
    precise about attack-generation method varying **by goal within a system**,
    not just by system: leakage/external-leakage use real AutoResearch search
    (`auto_research` v2); small-scale degradation uses the non-search family
    sweep (see the 🔖 cross-cutting finding above); only the medium-scale
    degradation pilot uses real search. Collapsing this distinction would have
    reintroduced the same misattribution just fixed in RQ1/RQ2.
  - No B0/B3 labels used anywhere in the final text — decided unexplained
    baseline-letter jargon (referencing a taxonomy no longer defined anywhere in
    the paper, since B0–B3 were cut) would itself violate "don't make the reader
    know things they'd only know from being in the room." Plain English instead
    ("clean baseline," "AutoResearch search," "family sweep").
  *(Peer: "Experimental Design רחב מדי")*
  **Follow-up refinement (same session):** rebuilt the matrix table with nested
  `\multirow` rows (System/Integration merged per system, added `\usepackage{multirow}`
  to `preamble/packages.tex`) and split the earlier combined "Leakage / external
  leakage" cell into two separate rows — the table now has exactly 13 rows,
  matching the real experiment count 1:1 (verifiable against
  `live_ollama_small_metrics.csv`). Added a `Runs` column (28/104) directly in
  the table, which let the trailing paragraph drop the now-redundant run-count
  restatement and keep only genuinely new info (task/variant counts, model name).
  Compiled cleanly (`latexmk -pdf`, 25 pages, no errors).
  **Second follow-up:** added the search's combination-space size explicitly —
  verified via code that the generic recombination space (`INJECTION_LOCATIONS`
  ×`TARGET_CHANNELS`×`TARGET_AGENTS`×`PROMPT_TEMPLATES` = 6×8×5×8 = 1,920) plus
  the 8 pre-authored family seed points (which use 8 *separate* template strings,
  confirmed zero overlap with the 8 generic ones) gives 1,928 total known attack
  configurations, of which only 6 (small-scale) or 12 (medium pilot) are ever
  tried (~0.3%). This number was previously absent from the paper entirely even
  though it's the actual quantitative justification for calling this a "search"
  rather than brute force. Also spelled out the 28-run and 104-run arithmetic
  explicitly in prose (tasks + tasks×iterations), widened the table so "External
  leakage" fits on one line, and shortened "AutoResearch search" to "AutoResearch"
  throughout the table. Compiled cleanly.
  🔖 **Found but not yet applied:** this table's closing paragraph is near-verbatim
  duplicated by `results.tex`'s opening two paragraphs (same task/variant/run
  counts, same model name, same system list). Decision made: keep the detail in
  Methodology (it's positioned right under the table it explains), trim
  `results.tex`'s opening down to a one-line pointer back to Section 8 plus the
  smoke-run caveat (the one genuinely new fact in that opening) when we reach the
  Results/Discussion pass later in this checklist.

## P1 — Table/metric scope vs. what's reported

- [x] **Table 1 (evaluation metrics) lists more than is used.** ✅ **Resolved.**
  Cut Transferability and Defense categories entirely (both prose subsections and
  table rows) — never evaluated, same reasoning as Abstract/Contributions/Section 8.
  Cut standalone Cost Amplification, Latency Increase, and Tool Call Increase —
  verified in code (`performance_metrics.py`) that these three are folded into the
  single `operational_degradation_score` composite (`0.25×tool_call_increase +
  0.25×retry_rate + 0.25×loop_or_failure_rate + 0.15×cost_amplification +
  0.10×final_output_empty_rate`), which *is* what's actually in the degradation
  results table, so replaced the three standalone rows with one
  "Operational Degradation Score" row describing the real composite. Also
  confirmed (traced `_build_degradation_family_diagnostics` in `runner.py`) that
  the per-family "Family Operational Score" shown elsewhere in Results is the
  *same formula*, just computed over each family's runs instead of all attacked
  runs — noted this in the table description so the connection is explicit.
  **Cut Total Exposure Rate** — verified in code
  (`evaluation/leakage_metrics.py`) that `leakage_asr` and `total_exposure_rate`
  compute the identical formula (`_run_leaked` = `_internal_channel_leaked or
  _final_output_leaked`, same as `total_exposure_rate`'s per-run check) — not
  just redundant in this dataset, mathematically identical by construction.
  **Kept Output-Only Miss Rate**, resolving the earlier judgment call, via a
  swap: since it's algebraically derivable from already-available numbers
  (`output_only_miss_rate = leakage_asr − final_output_leakage_rate`, from
  inclusion-exclusion on internal/final-output as overlapping events — verified
  against the small-suite CSV: LangGraph 1.000−0.375=0.625, AgentDojo
  0.958−0.083=0.875, AutoGen 1.000−0.458=0.542, CrewAI 1.000−0.292=0.708), it can
  be a genuinely reported metric, not just a conceptual one.
  🔖 **Follow-up for later (results.tex pass, not yet applied):** propagate this
  same swap into `results.tex`'s actual `tab:leakage_results` table — replace the
  column redundant with Leakage ASR there (per the existing 🚩 P2 item above:
  "Leakage ASR" ≡ "Internal Leakage" in every row of that specific table) with a
  real Output-Only Miss Rate column, using the derived values above. This would
  resolve that P2 redundant-columns finding with an actual new metric instead of
  just deleting a duplicate.
  *(Peer: "Evaluation Metrics כוללת יותר מדי מטריקות")*

## P1 — Section-level consistency and completion

- [x] **`methodology.tex` §Attack Goals never defines external leakage as a goal
  at all.** ✅ **Resolved.** Added a third subsubsection, "External Leakage",
  between "Sensitive Information Leakage" and "Performance Degradation", plus a
  parallel sentence in "Sensitive Information Leakage" so the two are legible as a
  contrast rather than one being documented and the other not.
  - Confirmed via code before writing: `goal` is a flat 3-way `Literal["leakage",
    "degradation", "external_leakage"]` ([schemas.py:22](../code/agent_redteam/schemas.py#L22)),
    a fully separate, mutually-exclusive config value with its own scorer
    (`score_external_leakage_variant`, [scorer.py:47-66](../code/agent_redteam/evaluation/scorer.py#L47-L66))
    and its own `\subsection`+table in `results.tex` — decided this warrants a full
    subsubsection (not a bolded inline paragraph within Leakage) for structural
    consistency with how every other part of the paper already treats it as a
    co-equal third objective, even though the *conceptual* delta from plain
    leakage is small.
  - Caught and corrected an inaccurate claim mid-drafting: the user's first phrasing
    was that the external-leakage search "ignores internal leakage." Verified
    against `reward_profiles.py:7-13` (`DEFAULT_EXTERNAL_LEAKAGE_WEIGHTS`) this is
    false — `internal_leakage_rate` still carries weight 0.75, just roughly 4x less
    than `final_output_leakage_rate`'s 3.0. Corrected framing: "heavily biased
    toward final-output, not exclusive of internal."
  - Decided **not** to state the raw numeric weights (3.0/0.75/0.25/-0.5/0.25) in
    prose, only the ~4x ratio — for consistency with how Table 1's Operational
    Degradation Score row already describes its own 5-term composite qualitatively
    ("weighted composite") without listing its coefficients, and because these are
    unmotivated implementation defaults (no tuning/ablation argument exists for why
    3.0 vs 0.75 specifically), so stating them as precise numbers would imply a
    justification that doesn't exist. The ratio is still stated because, unlike the
    raw weights, it's the actual evidentiary backing for the "prioritizes but
    doesn't exclude" claim.
  - Verified the weights used in prose are the ones actually used in the reported
    small-suite runs, not just code defaults: `configs/langgraph_real_llm_ollama_leakage_small.yaml`
    has no `reward_profile` override (falls through to `DEFAULT_LEAKAGE_WEIGHTS`:
    `internal_leakage_rate=0.5`, `final_output_leakage_rate=0.5`, equal), while
    `configs/langgraph_real_llm_ollama_external_leakage_small.yaml` explicitly sets
    `reward_profile: external_leakage`.
  - Added the side-effect sentence per the checklist wording, matching
    `results.tex`'s own framing ("the objective of these configurations was
    leakage rather than performance degradation").
  - Updated the "Attack Goals" intro sentence from "two complementary attack
    goals" to "three attack goals."
  - Compiled cleanly (`latexmk -pdf`, 24 pages). Remaining overfull/underfull hbox
    warnings in the log (all ≤2.72pt) are in the pre-existing Section 8 matrix
    table, confirmed unrelated to this edit.
  *(Ravit, `RavitsRejects.md` §9 "Attack Goals"; related to the existing P2
  "External leakage vs. degradation" item below, but that item is about wording
  consistency once the goal exists — this one was about the goal not being
  defined at all.)*
- [x] **`sections/conclusion.tex` §Limitations is thin and not reconciled with
  `results.tex` §Limitations.** ✅ **Resolved**, via a full merge into one
  section rather than a cross-reference between two — decided during drafting
  that splitting Limitations across two sections (empirical scope in Results,
  framework/design in Conclusion) was itself an avoidable inconsistency once we
  looked at it head-on, so the user opted to consolidate instead of the
  originally-planned "point back to Results" approach.
  - Deleted `results.tex`'s `\subsection{Limitations}` (was lines 178–185,
    `\label{subsec:results_limitations}`, confirmed unreferenced elsewhere
    before removal) entirely; that content now lives in `conclusion.tex`'s
    `\section{Limitations}`, organized under five bolded lead-ins: Evaluation
    scale, Search design and budget, Detection method, Scope of comparison,
    Deployment fidelity.
  - Folded in the "6 of 1,928 combinations, only 4 of 6 feedback-informed"
    search-budget caveat under Search design and budget, per the deferred
    Section 6 item.
  - Added the explicit "not evaluated" facts (no random/manual baseline, no
    transfer, no defense comparison) under Scope of comparison — but cut a
    drafted trailing clause ("...so no claim is made that AutoResearch search
    outperforms simpler baselines or that attacks generalize across
    frameworks") after the user flagged it as redundant defensive
    meta-commentary restating what the preceding sentence already establishes.
    Agreed and cut it.
  - Rewrote the "synthetic secrets" bullet after the user correctly challenged
    its original justification ("may not transfer directly to production
    systems" — named no actual mechanism, since the attacked LLM has no notion
    of synthetic vs. real data at inference time and treats a canary like any
    other context string). Replaced with the real, narrower claim: canary
    secrets aren't protected by the access-control/output-filtering
    infrastructure a real deployment would put around genuine sensitive data,
    so measured leakage rates reflect propagation through the agent alone, not
    resistance from any surrounding production safeguards.
  - Dropped `results.tex`'s original latency and automated-summarization-CSV
    sentences from the merge — the latter read as an internal engineering TODO
    ("the pipeline should be corrected before final automated table
    generation") rather than a limitation a reader needs; flagged to the user
    as worth a separate look if it affects any number actually reported in
    `results.tex` (not yet independently verified either way).
  - Dropped the duplicate "results may vary across LLM providers and model
    versions" bullet (subsumed by the model-specific sentence under Evaluation
    scale).
  - Compiled cleanly (`latexmk -pdf`, 24 pages, no new warnings).
  *(Ravit, `RavitsRejects.md` §16 "Limitations", cross-referencing the "possible
  duplication of limitations" note in §14 "Results.")*
  🔖 **Open follow-up:** verify whether the dropped
  external-leakage/degradation-CSV-mixing note describes a real bug affecting a
  reported number in `results.tex`, or was already just a resolved/non-issue by
  the time of the small-suite run — not yet checked.
- [x] **`methodology.tex` §Experimental Systems overclaims uniform
  implementation, and never states the real-vs-official adapter split.** ✅
  **Resolved.**
  - Changed "each system setting is configured to **implement** the same
    abstract workflow" to "**approximate**." Verified the reasoning is
    code-grounded, not just Ravit's suggestion: none of the four systems'
    native execution mechanism structurally guarantees the
    planner→retriever→worker→reviewer shape. `RoundRobinGroupChat` (AutoGen
    official) just round-robins turns among agents, the pipeline ordering
    comes entirely from role assignment and prompting, not from anything in
    `RoundRobinGroupChat` itself. `Process.sequential` (CrewAI official) does
    enforce an ordered task sequence, so it's the closest of the four to
    literally realizing the pipeline. LangGraph "real" and AgentDojo "real"
    are custom Python pipelines, confirmed via
    [langgraph_real_workflow.py](../code/agent_redteam/adapters/langgraph_real_workflow.py)
    and
    [agentdojo_real_workflow.py:1](../code/agent_redteam/adapters/agentdojo_real_workflow.py#L1)
    (docstring: "Controlled AgentDojo-compatible local workflow"), not the
    `langgraph`/`agentdojo` packages' own execution engines. Considered "follow"
    as an alternative softening (raised by the user) and rejected it on the
    same reasoning used throughout this checklist: "follow" is softer in tone
    than "implement" but keeps the same implication of procedural adherence,
    it doesn't communicate that the correspondence is inexact the way
    "approximate" does.
  - Added one new paragraph right after §Experimental Systems' opening
    paragraph making the real-vs-official split explicit **before** it's used
    unexplained later (Section 8's matrix table, `results.tex`'s "official
    AutoGen"/"official CrewAI"). Verified the split precisely before writing
    it, since it is **not** simply "real = custom code, official = uses the
    real package" — `agentdojo_real_workflow.py` still requires the actual
    `agentdojo` package to be importable (`try_import_agentdojo()`, called
    from `agentdojo_real_adapter.py:45`) even though it doesn't run
    AgentDojo's own benchmark harness, so the accurate framing is "dedicated
    adapter built for this project" (real) vs. "driven directly through the
    framework's own orchestration classes" (official,
    `AssistantAgent`+`RoundRobinGroupChat` from `autogen_agentchat`;
    `Agent`/`Task`/`Crew`/`Process` from `crewai`, calling `Crew.kickoff()`).
  - Also caught and cut "defenses" from the same opening paragraph's "This
    common interface allows the same attack variants, defenses, and metrics to
    be applied across systems" — same overclaim pattern as everywhere else in
    this checklist: defenses are wired into the adapters (D0–D4 presets exist)
    but no defense was applied in any reported run, so listing "defenses"
    alongside things actually exercised in the evaluation implied it was used
    here.
  - Compiled cleanly (`latexmk -pdf`, 24 pages, no new warnings).
  *(Ravit, `RavitsRejects.md` §3 "Agentic and Multi-Agent LLM Systems" and §10
  "Experimental Systems.")*

- [x] **Discussion subsections are stubs.** ✅ **Resolved.** Rewrote entirely
  rather than just filling in the one fillable stub, once the user asked whether
  RQ2/RQ3 belonged in Discussion (they do, this is exactly where result
  interpretation should live, Conclusion is a separate, shorter wrap-up, still
  on the deferred list for its own tense fix).
  - **Final Output vs. Internal Exposure** (was fillable): real discussion
    grounded in already-reported numbers, internal leakage matched leakage ASR
    exactly in every system (0.958-1.000) while final-output leakage ranged
    0.083-0.458, giving an output-only miss rate of 0.542-0.875. Uses AgentDojo
    as the sharpest illustration: lowest final-output leakage (0.083) but
    internal leakage (0.958) nearly identical to the other three systems, so a
    final-output-only evaluator would have wrongly called it comparatively
    safe. Directly answers RQ1.
  - **Degradation Effectiveness by Attack Family** (new, replaces "AutoResearch
    vs. Manual Attacks"): surfaces a real pattern not previously stated in
    prose anywhere, the small-scale aggregate utility-drop numbers (0.000,
    0.000, 0.042, 0.042) are a poor summary because they average five
    ineffective degradation families with one substantially effective one
    (`priority_conflict`, 0.250, six times the aggregate). Also correctly
    attributes the medium-scale pilot's null result to real AutoResearch
    search not rediscovering what the fixed family sweep found directly,
    consistent with the RQ2 non-attribution rule established earlier in this
    checklist. Directly answers RQ2.
  - **Variation Across Frameworks** (new, replaces "Transferability Across
    Frameworks" and "Security-Utility Tradeoff", both undoable without
    baseline/transfer/defense data): a new cross-cutting finding, found while
    drafting this subsection, degradation only appeared on the two systems
    evaluated through official framework runtimes (AutoGen, CrewAI), not the
    two evaluated through dedicated real adapters (LangGraph, AgentDojo), an
    exact match to the real-vs-official split from Experimental Systems.
    Explicitly hedged (only two systems per side, correlational not causal)
    to avoid overclaiming a pattern from `n=2` per group. Directly answers
    RQ3.
  - Per user's explicit instruction, dropped the "Future Work" idea entirely
    rather than adding a paragraph about implemented-but-unevaluated
    capabilities (baselines, transfer, defenses), consistent with the
    cut-rather-than-caveat principle applied everywhere else in this
    checklist; that scope-boundary information already lives in Limitations.
  - Compiled cleanly (`latexmk -pdf`, no new warnings).
  *(Peer: "Discussion כרגע placeholders")*
- [x] **Conclusion is written in future tense.** ✅ **Resolved.** Rewrote in
  past tense as a summary of what was actually built, evaluated, and found:
  the framework's design (heuristic search over attack variants), the four
  systems and three objectives evaluated, the headline leakage finding
  (0.958-1.000 ASR, internal exceeding final-output leakage), and the
  headline degradation finding (weaker overall, family-dependent,
  `priority_conflict` strongest). Also cut the two overclaims in the old
  version: "measuring transferability across" the four systems (no transfer
  evaluation was run, cross-system comparison is not transferability) and
  "comparing vulnerabilities, defenses, and generalization behavior" as an
  "expected outcome" (defenses and generalization/transfer were never
  evaluated). Compiled cleanly (`latexmk -pdf`, no new warnings). *(Peer:
  "Conclusion עדיין עתידי")*

## P2 — Internal consistency

- [x] **Cost amplification is presented as an evaluated objective but never has a
  reported value.** ✅ **Resolved — mostly already fixed as a side effect of
  earlier edits, plus one new fix found while checking.**
  - Verified `cost_amplification` is genuinely computed for every degradation run
    (real nonzero values confirmed in
    `code/docs/results/live_ollama_small/degradation_family_metrics.csv`, e.g.
    AutoGen official `priority_conflict` = 0.175) and does feed into the
    `Operational Degradation Score` composite (weight 0.15) that Table 1 already
    describes and that `results.tex` already reports — so the metric was never
    actually unmeasured, just not broken out as a standalone column. `abstract.tex`
    no longer mentions cost at all (fixed earlier in the Abstract rewrite); Table 1
    no longer lists a standalone Cost Amplification row (fixed earlier in the
    Table 1 rewrite). `introduction.tex` Contributions bullet 2's "maximizing a
    weighted combination of task-utility drop and operational-cost amplification"
    is a true statement about the objective's design, not a results claim, and was
    left as-is.
  - **New fix, found while checking this item:** `methodology.tex`'s Loop B
    section claimed the degradation score "can additionally incorporate latency
    increase and tool call increase when these counters are available." Verified
    against `scorer.py`/`reward_profiles.py` that `latency` never appears in
    either file, false. The real formula
    (`DEFAULT_DEGRADATION_WEIGHTS`) has exactly three terms: `utility_drop`,
    `cost_amplification`, `tool_call_increase`. Fixed by extending the
    `Objective\_perf` equation itself to three terms
    ($\alpha \cdot \text{UtilityDrop} + \beta \cdot \text{CostAmplification} +
    \gamma \cdot \text{ToolCallIncrease}$) and stating the real implemented
    weights ($\alpha=1.0$, $\beta=0.3$, $\gamma=0.2$) directly, since
    `configs/langgraph_real_llm_ollama_degradation_medium.yaml` explicitly
    declares these same values (not just a buried code default), unlike the
    leakage/external-leakage weights case where we deliberately stated only a
    ratio, not raw numbers, because those defaults had no comparable explicit
    config-level declaration backing them.
  - Added an explicit caveat sentence right after the weights that this scoring
    function only applies when the degradation loop actually searches and scores
    variants, which for the reported results is the medium-scale LangGraph pilot
    only. The small-scale degradation results (the paper's headline
    `priority_conflict`/`verification_loop` numbers) come from the fixed family
    sweep and never invoke this score at all. Added specifically to prevent a
    reader from thinking these weights shaped the headline small-scale numbers,
    consistent with the RQ2 misattribution fix earlier in this checklist.
  - Compiled cleanly (`latexmk -pdf`, 24 pages, no new warnings).
  *(Ravit, `RavitsRejects.md` §21 "Global Claims," "cost amplification is
  a central result" — verified independently: already resolved by earlier edits,
  with one additional real inaccuracy found and fixed along the way.)*
- [x] 🚩 **[NOT FROM PEER — CLAUDE-FOUND]** Two results tables in `results.tex`
  have redundant-looking columns, for two different reasons.
  1. **`tab:external_leakage_results`: "External Leakage ASR" and "Final-output
     Leakage" identical by definition.** ✅ **Resolved**, handled separately from
     `tab:leakage_results` per the user's request, and with the opposite
     resolution (drop one column, don't keep both) since this redundancy is
     tautological (`external_leakage_asr = final_output_leakage_rate` set
     directly in code, `leakage_metrics.py:207-213`), not an empirical finding
     worth exposing the way `tab:leakage_results`'s was.
     - Dropped "Final-output Leakage," kept "External Leakage ASR" (the term
       used throughout this section's prose) and "Internal Leakage" (genuinely
       different values, 0.667-1.000, and previously never actually discussed
       in prose despite being the more interesting column).
     - Stated the definitional equivalence in both the caption ("External
       Leakage ASR is defined as the final-output leakage rate for this
       objective") and prose, so a reader doesn't need to infer it.
     - Kept `Clean SR` in this table (unlike `tab:leakage_results`, where it was
       cut) after verifying it has real variance here, CrewAI official is 0.750
       versus 1.000 for the other three systems, so it's informative here where
       it wasn't in the other table.
     - Added a new sentence discussing Internal Leakage's actual values (0.667
       on LangGraph to 1.000 on AutoGen official), noting they exceed External
       Leakage ASR in every row even though this goal's search is weighted
       roughly 4x toward final-output exposure. Attached a small-sample caveat
       after the user correctly pushed back that this pattern comes from only
       six attack variants per configuration (the same cold-start-heavy search
       budget already documented in Limitations), so it should be read as a
       preliminary observation, not a stable property of the objective, since a
       different 6-variant sample could plausibly narrow or reverse the gap.
     - Wrapped the two long headers ("External Leakage ASR," "Internal
       Leakage") onto two lines each with `\shortstack`, matching
       `tab:leakage_results`'s fix, applied proactively this time rather than
       discovered via an overfull-hbox error. Confirmed via `latexmk` no new
       overfull hbox was introduced by this table.
     - Shortened the closing Clean/Attacked SR paragraph per user request (cut
       from three sentences to two) while keeping the CrewAI baseline caveat
       and the side-effect-not-degradation framing.
  2. **`tab:leakage_results`: "Leakage ASR" and "Internal Leakage" identical in
     every row, but not by definition.** ✅ **Resolved**, via a different
     approach than originally planned: rather than dropping the redundant-looking
     "Internal Leakage" column, the user chose to **keep it deliberately**, on
     the reasoning that showing `Leakage ASR` and `Internal Leakage` as visibly
     equal numbers lets the reader verify the propagation finding directly
     (no run leaked to the final output without also leaking internally) instead
     of just trusting a prose claim.
     - Added a genuinely new `Output-Only Miss Rate` column alongside it
       (LangGraph 0.625, AgentDojo 0.875, AutoGen 0.542, CrewAI 0.708), so the
       four leakage columns (ASR, Internal, Final-output, Miss Rate) together
       fully reconstruct the internal/output overlap per system.
     - Verified before applying (per user's direct challenge) that
       `output_only_miss_rate` is a real function in the code
       ([leakage_metrics.py:153-166](../code/agent_redteam/evaluation/leakage_metrics.py#L153-L166),
       computed per-run as `has_internal_leak AND NOT has_output_leak`, not via
       subtraction), and proved algebraically that
       `leakage_asr − final_output_leakage_rate` equals this function exactly as
       a set-difference identity ($|I\cup O| - |O| = |I\setminus O|$, holds
       regardless of whether $O \subseteq I$), so deriving the table values via
       subtraction from already-reported numbers is exact, not an approximation.
       Recomputed from the raw CSV
       (`code/docs/results/live_ollama_small/live_ollama_small_metrics.csv`) to
       full float precision to confirm, not just from the paper's rounded
       3-decimal display values.
     - Caught and corrected my own inaccurate description of
       `internal_leakage_rate` mid-drafting: initially described it as "internal
       channels **only**" (i.e. exclusive of final-output leakage). The user
       caught this immediately by noting LangGraph's Internal Leakage=1.000
       couldn't be exclusive-of-output given Final-output Leakage=0.375 (would
       cap at 0.625 if exclusive). Confirmed against the code
       (`leakage_metrics.py:125-136`) the function is inclusive, counts any run
       with an internal-channel leak regardless of whether it also leaked to the
       output. Fixed the paper prose accordingly; the underlying algebra was
       unaffected since it already treated the internal-leak set as inclusive.
     - **Dropped the Clean SR column** (verified 1.000 in every row of this
       table, zero variance, no information), stating it once in prose instead.
     - Table went from 5 to 6 columns, which overflowed the page width by
       55.75pt at `\scriptsize` (confirmed via `latexmk`). Fixed by wrapping the
       three long headers ("Internal Leakage," "Final-output Leakage,"
       "Output-Only Miss Rate") onto two lines each with `\shortstack`, per the
       user's specific direction, rather than the originally-proposed
       `\tabcolsep` tightening + header-shortening combination. Verified this
       alone fully resolved the overfull hbox (confirmed via `latexmk`, the
       55.75pt warning is gone, only pre-existing unrelated warnings from other
       tables remain).
  *(Not from peer/Ravit — found while explaining the external-leakage vs.
  final-output-leakage distinction. Cross-reference the existing P2 "External
  leakage vs. degradation" consistency item above — related but distinct.)*
- [x] **Medium-pilot table doesn't show its own headline number.** ✅
  **Resolved.** Added a `Utility Drop` column (value 0.000, matching the prose
  and consistent with Clean SR = Attacked SR = 1.000) to `tab:medium_degradation_pilot`.
  Single-row table, no width issues, compiled cleanly. *(Ravit,
  `RavitsRejects.md` §14 "Results," subsection "Medium Pilot Table.")*
- [x] **"External leakage" vs. "degradation" framing must stay consistent
  paper-wide.** ✅ **Resolved — already consistent, no live violation found,
  effectively fixed as a side effect of an earlier edit.** Audited
  `introduction.tex`, `research_goal.tex`, and `methodology.tex`:
  - `introduction.tex` (lines 25, 31, 39, 107, 115): all degradation mentions
    describe the loop's general objective, never tied to a specific number or
    to external-leakage's side effects. Line 39 explicitly reinforces the
    separation ("without necessarily leaking a secret").
  - `research_goal.tex` (RQ2, RQ3): goal-level questions, not data claims,
    nothing to conflate at that level.
  - `methodology.tex`: the one place this distinction needed to be stated, the
    External Leakage subsubsection added earlier in this session, already says
    it correctly ("we treat that change as a side effect of the external
    leakage objective, not as a degradation result"). Table 1's `Utility Drop`
    row defines the metric generically, a formula definition, not a
    goal-specific results claim, so it isn't a violation either.
  No changes applied. *(Peer: "External leakage מול degradation")*
- [x] **Be careful with "AutoResearch optimized" as a strength claim.** ✅
  **Resolved.** Scanned `introduction.tex`, `methodology.tex`, and `results.tex`
  for "outperform" (zero occurrences anywhere) and for "optimiz"/iteration
  language.
  - Found and fixed one live violation: `methodology.tex`'s Loop A section
    (then lines 246-248) stated "Thus, improvement across iterations is driven
    by measured leakage behavior rather than by manually rewriting each
    attack." This asserted that iteration-over-iteration improvement actually
    *happened*, but `results.tex` only reports aggregate final-run
    effectiveness (e.g. leakage ASR 0.958-1.000), never an iteration-by-iteration
    curve, exactly the pattern Ravit flagged. Fixed by describing the
    mechanism instead of the outcome: "Candidate selection is therefore driven
    by measured leakage behavior." Also dropped the trailing "rather than by
    manually rewriting each attack" contrastive clause per user request
    (consistent with this session's recurring "Rather than X" LLM-tell rule).
  - No other violations found in `introduction.tex`, `methodology.tex`, or
    `results.tex`. Compiled cleanly (`latexmk -pdf`, no new warnings).
  - **Follow-up broader scan (user request):** re-scanned *all* of
    `sections/*.tex`, not just the three files this item originally named.
    Found one more occurrence, `conclusion.tex:10`: *"This section compares
    whether AutoResearch-optimized attacks outperform manual and random
    baselines."* Different in kind from the fixed instance though, it's a
    placeholder stub naming an unanswered comparison as its topic, not
    asserting outperformance as a finding. It's the exact "AutoResearch vs.
    Manual Attacks" Discussion subsection already identified elsewhere in this
    checklist as unfillable-honestly and deferred along with the rest of
    Discussion/Conclusion. No independent fix applied here, tracked instead
    under the deferred Discussion-stubs rewrite. `abstract.tex`,
    `research_goal.tex`, and `related_work.tex` checked clean (the latter's
    "optimization" mentions all describe other papers' methods, not this
    project's).
  *(Peer: "צריך להיזהר מהטענה 'AutoResearch optimized'"; Ravit,
  `RavitsRejects.md` §11, "Leakage Optimization Subsection.")*

## P3 — LaTeX/formatting

- [x] **Table float placement in Results.** ✅ **Resolved**, after a
  false-negative, a dead end, and an overcorrection along the way, worth
  recording all three since they inform how to handle similar issues later.
  - **False negative:** first check used only `main.aux` page-label
    cross-referencing (no PDF render/text tools available in this
    environment), which showed all tables on pages at or after their section
    start and wrongly concluded "not reproducing." The user then visually
    confirmed Table 4 (External Leakage) was still rendering directly above
    its own subsection heading, a same-page ordering issue page numbers alone
    can't detect.
  - **Dead end:** changing all five `\begin{table*}[t]` to `[H]` (the `float`
    package's exact-placement specifier, already used successfully for the
    Methodology workflow figure) silently broke all five Results tables. `H`
    does not reliably support `table*`/`figure*` (double-column floats use
    `\@dblfloat` internally, not fully covered by `float.sty`'s `H` patch).
    Confirmed across three full compile passes that caption text never
    appeared in `main.log` and no table labels were ever written to
    `main.aux`, a genuine content-loss bug that `-halt-on-error` did not catch
    since no fatal error was thrown.
  - **Overcorrection:** reverted to `[t]`, added `\usepackage{placeins}` to
    `preamble/packages.tex`, and initially inserted `\FloatBarrier` before all
    five subsections following a table. This fixed the ordering but forced
    unnecessary flushes for the four tables that were never actually confirmed
    broken, visibly bloating whitespace (page count rose from 24 to 26). Per
    user feedback, scaled back to a single `\FloatBarrier`, right before
    `\subsection{External Leakage}`, the one confirmed case.
  - **Final verified state:** rebuilt clean (`latexmk -C` then `latexmk -pdf`).
    `tab:external_leakage_results` lands on page 18, strictly after its
    "External Leakage" heading (page 17); all other table/subsection pairs
    remain correctly ordered without needing their own barrier; page count is
    back to 24 (matching pre-`\FloatBarrier` length); no new
    overfull/underfull warnings; all labels and captions render correctly.
  - Also fixed in the same pass, per the user's direct observation while
    looking at the PDF: Table 6 (`tab:degradation_family_results`) was
    overflowing off the right edge of the page (the 94.017pt overfull hbox
    previously dismissed as "pre-existing, unrelated" during the
    redundant-columns work, should have been investigated then instead).
    Fixed with the same `\shortstack` two-line-header technique used on the
    two leakage tables. Confirmed the 94pt overfull hbox is gone.
  - **Follow-up (same area, found by user):** page 16 was left almost entirely
    blank, with Results not starting until page 17. Root cause: an explicit
    `\clearpage` at the very end of `methodology.tex` (line 430, right after
    Section 8's closing paragraph), forcing a hard page break regardless of
    how much room remained. The `\begin{table}[H]` exp-matrix table (a plain
    `table`, not `table*`, so unaffected by the earlier `H`/double-column
    incompatibility) had already pushed itself to page 15 for space, leaving
    only a short 3-sentence closing paragraph alone on page 16, then
    `\clearpage` forced Results to start fresh on page 17 regardless. Removed
    the `\clearpage`. Verified via `main.aux`: Results now starts on page 16
    (was 17), page count unchanged at 24, no new overfull/underfull warnings.
  *(Peer: "Results ... צריך לשפר מיקום טבלאות")*
- [ ] **Title page has an unresolved placeholder.** Verified:
  `sections/titlepage.tex:22` literally contains `[complete others]`. Fill in the
  missing author/advisor info or remove the bracketed placeholder before
  submission. *(Ravit, `RavitsRejects.md` §0 "Title Page.")*
- [ ] **Recent (2025–2026) bibliography entries need manual verification.**
  Not independently checked in this pass (requires looking up each source, not a
  grep). Verify title, authors, year, venue, and existence for the AutoResearch,
  AutoInject (`learningtoinject2026`), and Slingshot (`verifiableagenttoagent2026`)
  entries in `bib/references.bib`, and confirm each citation actually supports the
  sentence it's attached to. *(Ravit, `RavitsRejects.md` §6 "Related Work" and §20
  "References.")*
- [x] **Minor formatting/polish, low priority.** ✅ **Resolved.**
  - (a) Added the canary-secrets sentence to §Ethical Considerations as
    planned, but also caught and fixed a second, more substantive issue while
    touching this paragraph: its closing sentence stated the goal of the work
    was "to improve the evaluation and defense of agentic and multi-agent
    systems," but no defense was actually evaluated in this report (D0-D4
    implemented but not run, per the Limitations/Scope-of-comparison item
    resolved earlier). Per the user's direct correction, replaced "defense"
    with an accurate statement of what was actually done: "The goal of this
    work is to improve how agentic and multi-agent systems are evaluated for
    information leakage and performance degradation under adversarial
    conditions."
  - (b) Verified the Threat Model gap was real, not hypothetical: the
    Attacker Capabilities list names "inter-agent messages" as a generic
    entry point, but AgentDojo is described elsewhere in the paper
    (§Experimental Systems) as single-agent, explicitly "without requiring
    the threat model to assume multi-agent communication in every case," so
    the unqualified list could read as implying inter-agent-message injection
    applies uniformly across all four systems when it structurally can't for
    AgentDojo. Added a qualifying sentence noting not every channel applies
    to every evaluated system and that the exact set exercised depends on
    the configuration.
  - (c) `\texttt{}` consistency, no action needed, already confirmed clean in
    an earlier pass.
  - Compiled cleanly (`latexmk -pdf`, no new warnings).
  *(Ravit, `RavitsRejects.md` §17 "Ethical Considerations," §8 "Threat
  Model," §14 "Results" identifier-formatting subsection.)*

---

## Suggested order of attack

1. Rescope abstract + contributions + RQ1/RQ3 framing (P0) — this determines how
   much of everything else is "missing result" vs. "already consistent."
2. Define external leakage as a real third goal in §Attack Goals, trim/split
   Table 1 metrics, and reconcile the two Limitations blurbs (P1) — these three
   fix the methodology/results mismatch, not just wording.
3. Rewrite Discussion subsections and Conclusion tense (P1) using only
   `results.tex`-backed claims; keep the Ravit watch-list phrases out of the
   rewrite.
4. Consistency audit for external-leakage/degradation framing, cost-amplification
   and "AutoResearch outperforms" phrasing, and the Experimental Systems
   real-vs-official wording (P2).
5. Float placement fix, title-page placeholder, medium-pilot table column, and
   bibliography verification (P3) — independent of the above, can be done anytime.

## What's already confirmed fine (no action needed)

Both Ravit documents and this checklist agree `sections/results.tex` itself is
**not** a major problem area — it's "mostly correct," and its own §Limitations,
§External Leakage side-effect framing, and reported numbers are consistently
treated as trustworthy ground truth throughout this checklist. The remaining work
is bringing the rest of the paper (abstract, introduction, methodology, discussion,
conclusion) into line with what `results.tex` already says correctly — not
re-deriving new results.
