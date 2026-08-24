---
title: "Conditionally Approved: A Proof-Bound Mortgage Benchmark for Long-Horizon AI Agents Under Changing Evidence, Authority, and Time"
author: "Rudy M. Celekli, Gradia Research"
date: "Cost-capped pre-results - 24 August 2026"
---

> **Pre-results boundary.** The cost-capped execution is complete and its aggregate
> was independently recomputed from 55 immutable attempt artifacts. This manuscript
> reports physical execution, exact machine-scored outcomes, infrastructure
> exclusions, runtime cohorts, cost, and trajectory shape. It does **not** claim a
> balanced model comparison, broad capability, frontier difficulty, tail reliability,
> human agreement, mortgage-domain validity, causal effects, training utility, or
> novelty. The 37 gradable outcomes remain behaviorally unattributed until blinded
> human adjudication distinguishes model failures from measurement defects.

## Abstract

Mortgage work is not a static question-answering problem. A loan file evolves while
people and systems act: documents arrive incomplete, evidence expires or is
retracted, policies are superseded, deadlines advance, authorities disagree, and
work crosses shifts. We introduce **Conditionally Approved**, a fully synthetic,
proof-bound benchmark for evaluating long-horizon AI agents under those changes.
Five task editions isolate document truth under pushback, epistemic residue after
retraction, competing legitimate authority, temporal portfolio control, and an
honest handoff whose quality is measured by successor performance.

The benchmark binds every eligible episode to a frozen task edition, model identity,
runtime commit, action ledger, material-world roots, agent-visible projections,
event and restore lineage, exact evaluator edition, and infrastructure disposition.
Official reward is a strict binary conjunction over task correctness and evidence
obligations; diagnostic vectors are reported separately and never converted into
unregistered partial reward. We initially preregistered five attempts for each of
four identity-pinned model providers. Before completing that design, the operator
imposed a prospective cost stop: a hard ceiling of 55 physical attempts and a
balanced target of two gradable attempts per provider × task cell. The amendment
preserves every prior attempt, selects the lowest two gradable ordinals within each
exact cell, excludes infrastructure failures from behavioral denominators, and
forbids pass-at-five or tail-reliability claims.

The completed execution recorded 55 physical attempts across four identity-pinned
providers: 37 were gradable and 18 were infrastructure exclusions. None of the 37
gradable attempts satisfied the exact perfect-rubric conjunction. Six of 20
provider-by-task cells contained an eligible same-runtime pair; neither attempt
passed in any of those six pairs. Nine cells had only one gradable attempt and five
were unobserved. The panel consumed 3,617 provider calls, 99.38 million input tokens,
6.08 million output tokens, 2,609 tool actions, 5,325 transcript turns, and $705.88
in recorded provider spend. Because execution crossed three runtime cohorts and did
not cover all cells, the verifier refused a balanced pass-at-two statistic, provider
ranking, and every pass-at-five claim. Behavioral attribution and criterion-level
interpretation remain reserved for blinded human review. The benchmark was built and
verified with the Gradia Universes platform; Gradia is the execution and evidence
system, not the benchmark name.

## 1. Why conditional approval is the right evaluation problem

An agent can produce a plausible final answer and still fail the work. It may cite a
superseded source, silently obey an unauthorized request, miss a deadline boundary,
carry retracted evidence into later decisions, or hand off a summary that causes the
next agent to violate an active constraint. Conversely, a long or inefficient
trajectory is not automatically incorrect. Conditioned on valid infrastructure, the
official score asks whether the submitted work is correct and fully evidence-grounded
under the frozen contract—not whether the agent used a preferred number of steps.

The title has a deliberate double meaning. In mortgage operations, approval is often
conditional on unresolved evidence. In this benchmark, every evaluation claim is
also conditional on a valid world, an admitted evaluator, and reviewable evidence.

## 2. Research questions

- **RQ1 — Exact completion.** Does an identity-pinned frontier agent produce a
  perfect-rubric completion in each observed evolving workflow?
- **RQ2 — Two-attempt repeatability.** In exact provider × task cells with two
  same-runtime gradable attempts, does the model pass at least once, and does it pass
  both times? This is exploratory repeatability evidence, not a tail-reliability or
  general capability estimate.
- **RQ3 — Behavioral differentiation.** Which evidence, authority, temporal, and
  handoff obligations produce distinct, repeatable failure signatures?
- **RQ4 — Measurement validity.** Do deterministic checks, calibrated model-based
  interpretation, and blinded humans agree on which failures are attributable to the
  agent rather than the environment or evaluator?
- **RQ5 — Operational cost.** What calls, tokens, tool actions, wall time, and provider
  spend are required for a valid attempt, and how much missingness is caused by
  infrastructure rather than behavior?

## 3. Related work and measurement boundary

Dynamic and stateful agent benchmarks already establish that useful evaluation must
go beyond static question answering. Gaia2/Agents Research Environments studies
asynchronous changing worlds; InterruptBench studies user revisions and retractions;
and tau-bench, tau2-bench, AppWorld, ToolSandbox, and OSWorld evaluate agents through
actions that alter persistent environments [1--7]. Those systems occupy the broad
territory of dynamic environments, interruptions, and stateful tool use. This work
does not claim those ideas as new.

The narrower measurement problem is whether a benchmark can prove the chain from a
declared occurrence to the material world transition, the exact projection visible
to the agent, the eligible action boundary, any restore lineage, and the final
judgment. Proof of Execution, CAVA, agent-native telemetry, W3C PROV, and recent
runtime-evidence work establish adjacent execution, provenance, canonical-action,
and telemetry foundations [8--14]. Agentic Data Environments and BranchBench make
the complementary systems case that consequential agents operate over a closure of
files, databases, processes, applications, APIs, memory, and derived state, while
Data Flow Control studies semantic source-to-sink restrictions [15--17]. The method
paper therefore tests a composition and its incremental detection value; it does
not present hashing, logging, branching, provenance, or checkpointing as novel in
isolation.

Benchmark-quality work also warns that a clean headline score can conceal broken
tasks, evaluator leakage, contamination, or a saturated ceiling [18--20].
Conditionally Approved responds with mutation-tested evaluators, immutable
preregistration, explicit infrastructure censors, runtime-stratified denominators,
and human adjudication. These controls make the result more auditable; they do not
substitute for domain-expert validity or a sufficiently powered behavioral study.

## 4. Benchmark design

### 4.1 Frozen five-task panel

| Task edition | Core stressor | Required capability | Registered treatment |
|---|---|---|---|
| Document truth under pushback | Incomplete and conflicting document evidence | Reconcile exact pages, versions, claims, and current authority | `alder.page-missing` |
| Epistemic residue | Evidence observed, retracted, and replaced | Stop using dead evidence and re-ground the decision | `cedar.seen-retracted-replaced` |
| Authority and fair judgment | Two legitimate principals conflict | Apply authority scope, protect fairness constraints, and escalate correctly | `dogwood.competing-legitimate-principals` |
| Temporal portfolio control | Coupled files evolve around a commitment boundary | Coordinate scarce capacity, deadlines, and post-change rechecks | `fir.phase-pre-commit` |
| Honest handoff and verified commit | Work crosses an agent/session boundary | Preserve active constraints, uncertainty, provenance, and successor usability | `birch.contract-altered` |

The stories, people, organizations, values, documents, and policies are synthetic.
They are not customer records, mortgage advice, production policy, or evidence of
external-domain validity.

### 4.2 Long-horizon execution

The safe scripted controls require 113–150 actions under full load. That observation
establishes instrument solvability and the existence of a long execution path; it
does not establish frontier difficulty. Model attempts may use fewer or more actions.
Act count, verbosity, latency, and cost are diagnostic variables rather than reward
criteria unless a task explicitly binds a deadline or resource limit.

### 4.3 Evolving-world evidence

Each declared occurrence binds its frozen event identity, exact eligible action
boundary, before/after material roots, agent-visible projection, authority, restore
generation, and previous occurrence-chain head. This lets the verifier distinguish
environment application, disclosure, authority, restore, evaluator, and agent faults
before an episode enters a model-performance denominator.

### 4.4 Formal episode and disposition contract

An episode is represented as

$$E_i=(T_i,M_i,S_i,W_{i,0},A_i,\Omega_i,R_i,J_i),$$

where $T_i$ is the frozen task edition, $M_i$ the requested and resolved model
identity, $S_i$ the scaffold and runtime identity, $W_{i,0}$ the initial material
world root, $A_i$ the ordered act ledger, $\Omega_i$ the occurrence-witness chain,
$R_i$ the restore lineage, and $J_i$ the evaluator edition and criterion vector.
Every occurrence $\omega_{i,k}$ binds the declared event, eligible boundary,
before/after roots, visible projection, authority, restore generation, and the
previous occurrence digest. A verifier recomputes these bindings from released
bytes; it does not trust a reported scalar.

Before scoring, every physical attempt receives exactly one disposition:

1. **gradable** — protocol, identity, runtime, world, and evaluator evidence close;
2. **infrastructure censor** — dispatch, transport, provider, or host evidence makes
   behavior unscorable;
3. **measurement defect** — the environment or evaluator cannot support the intended
   attribution; or
4. **pending adjudication** — deterministic observations exist, but their cause has
   not yet been assigned.

Only the first disposition may enter a behavioral denominator. The others remain
visible, retain cost and receipt evidence, and cannot be silently retried into a
preferred outcome.

### 4.5 Gradia Universes: methodological differentiators

Gradia Universes is the execution and evidence apparatus used to build and verify
this benchmark; it is not the benchmark's name. Its purpose is to turn an episode
from a transcript plus score into a versioned scientific object. Seven design
choices matter for this study:

1. **Material world and visible world are separate commitments.** The runtime binds
   both the root-owned state transition and the exact projection available to the
   agent. An event cannot count merely because it appears in an operator log.
2. **Evolution is witnessed at an eligible act boundary.** Every occurrence binds
   what changed, when the change became visible, the before/after roots, authority,
   previous chain head, and restore generation. This localizes disclosure and stale-
   context defects that a terminal-state judge cannot see.
3. **Restore and replay preserve lineage rather than erasing history.** A restored
   world must name its parent, generation, and occurrence history. Counterfactual
   work can therefore distinguish a legitimate fork from an unrelated rerun.
4. **Identity is part of the measurement.** Requested and resolved model, task,
   evaluator, runtime, scaffold, Git commit, and sampling contract are frozen into
   the episode. Provider substitution or runtime drift is a measurement event, not
   an invisible implementation detail.
5. **Disposition precedes scoring.** Infrastructure censorship and measurement
   defects are retained with receipts but excluded from model denominators. This
   prevents transport failures from becoming apparent model failures and prevents
   retries from silently replacing inconvenient outcomes.
6. **Evaluators must survive mutations.** Positive controls establish a solvable
   floor; isolated one-defect probes test whether each criterion catches exactly its
   intended defect; current-source and post-change reread requirements prevent a
   plausible narrative from passing without observable evidence.
7. **Analysis is claim-gated.** Binary reward, criterion diagnostics, trajectory
   shape, human adjudication, causal inference, and training labels are separate
   evidence products. Analytics+ may summarize only the claims licensed by the
   exact evidence edition rather than upgrading correlations into mechanisms.

Dynamic worlds, interruption handling, snapshots, event logs, and provenance are
all established prior art. The candidate research contribution is narrower: the
composition above may provide incremental defect detection and more defensible
behavioral attribution than terminal state, ordinary logs, or an unversioned judge
alone. This paper demonstrates the instrument, its live execution inventory, and
its refusal behavior. A comparative detection study and blinded human agreement are
still required before that incremental-value hypothesis—or any novelty claim—is
accepted.

## 5. Evaluation contract

### 5.1 Official reward

Official reward is 1 only when every registered binary requirement passes. It is 0
otherwise. Criterion vectors, branch probes, tool-use traces, and narrative analyses
are diagnostic evidence—not hidden partial credit. A correct and complete result is
not penalized merely for taking more actions.

Formally, if $g_{i,1},\ldots,g_{i,K_i}\in\{0,1\}$ are the registered applicable
gates, the official episode outcome is

$$y_i=\prod_{k=1}^{K_i}g_{i,k}.$$

The conjunction prevents a strong final narrative from compensating for stale
evidence, missing authority, an unauthorized irreversible act, or an unusable
handoff. Separately reported criterion coverage can help diagnose where an episode
failed, but it is not partial credit and cannot change $y_i$.

### 5.2 Evaluator admission

The evaluator package must demonstrate:

1. a positive control for every task edition;
2. isolated one-defect mutations for each criterion;
3. current-source citations backed by root-owned read evidence;
4. post-boundary re-reading of every materially changed resource;
5. exact task, runtime, world-root, and evaluator-edition binding;
6. blinded independent human review of the criteria and representative outcomes; and
7. a fail-closed disposition for unresolved measurement defects.

Deterministic red criteria are initially **unresolved observations**. They become
model-attributable failure modes only after adjudication rules exclude environment,
provider, and evaluator defects.

### 5.3 Panel, amendment, and denominator

The original plan crossed four identity-pinned provider/model cells with five task
editions and five gradable attempts per cell. It was not completed. The cost-cap
amendment instead defines 20 exact provider × task cells, targets two gradable
attempts per cell, and limits the entire execution to 55 physical attempts.
Infrastructure failures retain their receipts and costs but do not enter behavioral
denominators. Within a cell, the lowest two gradable ordinals are selected; later
gradable attempts remain disclosed as overage and cannot replace an earlier result.
An exact-cell pair is reportable only if both selected attempts bind the same task,
evaluator, model identity, Git commit, and runtime-implementation digest.

The execution wrapper was allowed to remain active while the repository advanced.
The post-run verifier therefore partitions attempts by exact runtime cohort and
refuses pooled panel claims if more than one cohort is present. A later code gate
latches the panel commit before dispatch and rejects any child that drifts. The
historical cohort split is retained as a measurement defect, not edited away.

## 6. Locked analysis plan

For each provider × task cell, report:

- physical attempts, gradable attempts, and infrastructure exclusions;
- the exact runtime cohort of every selected attempt;
- `pass@2`: whether at least one of the two selected same-runtime attempts succeeds,
  only where an eligible pair exists;
- `pass^2`: whether both selected same-runtime attempts succeed, only where an
  eligible pair exists;
- single-attempt outcomes where exactly one gradable attempt exists, without
  relabeling them as pass@2;
- infrastructure exclusions and reasons;
- calls, input/output tokens, tool actions, wall time, and cost;
- registered criterion-failure frequencies, initially labeled unresolved; and
- identity-blinded Analytics+ interpretations with cited trajectory evidence and
  human disposition.

Across the panel, report inventory summaries without pooling away task, provider, or
runtime identity. A balanced statistic exists only if all 20 exact cells have two
eligible attempts under one common runtime cohort. No significance test, causal
claim, provider ranking, pass@5 claim, difficulty claim, or novelty claim may be
added after seeing outcomes unless it belongs to a separately preregistered study.

For an eligible exact cell $c$ with the two selected binary outcomes
$(y_{c,1},y_{c,2})$, this draft uses two deliberately different descriptive
quantities:

$$\operatorname{pass@2}_c=\max(y_{c,1},y_{c,2}),\qquad
\operatorname{pass^2}_c=y_{c,1}y_{c,2}.$$

The first asks whether either observed attempt passed; the second asks whether both
did. With only two attempts, neither is a stable tail-reliability or population
capability estimate. No value is emitted if the two attempts differ in frozen task,
model, evaluator, Git commit, or runtime-implementation digest.

## 7. Results

> **Machine-derived pre-results.** This section is generated from verification
> artifact `b8e013fc05b5f9868a892f89a2a0986d67978c68153b47d9b1756fbbec3b5777`.
> It reports exact execution and scoring facts, not human-attributed failure modes.

### 7.1 Completion and exclusions

The cost-capped execution completed at 14:24:51 UTC on 24 August 2026 after
reaching its prospective hard ceiling of **55 physical attempts**. Of those,
**37** produced a complete, gradable terminal artifact and **18** were
infrastructure exclusions. The machine-scored perfect-rubric outcome was **0/37**
among gradable attempts. This is an exact observation about the registered
artifacts—not an estimate of broad model capability and not yet an attribution to
model behavior.

The 18 exclusions remain in the physical-attempt and cost ledgers but never enter
behavioral denominators. Their terminal causes were seven OpenAI HTTP 401
authentication refusals, two Anthropic HTTP 529 overload failures after bounded
retries, six read timeouts, one OpenAI read error, and two xAI responses that
completed transport but did not yield an admitted text payload. Excluded attempts
accounted for **$173.35** of recorded spend. Seven OpenAI authentication exclusions
failed before a billable response and recorded zero spend; several other exclusions
occurred only after long partial trajectories.

| Provider/model | Physical | Gradable | Infrastructure exclusions | Perfect-rubric passes | Recorded spend |
|---|---:|---:|---:|---:|---:|
| `anthropic/claude-opus-5` | 14 | 8 | 6 | 0 | $281.50 |
| `gemini/gemini-3.1-pro-preview` | 13 | 13 | 0 | 0 | $2.99 |
| `openai/gpt-5.6-sol` | 18 | 10 | 8 | 0 | $308.62 |
| `xai/grok-4.6` | 10 | 6 | 4 | 0 | $112.77 |
| **Total** | **55** | **37** | **18** | **0** | **$705.88** |

The provider rows are execution inventory, not a reliability or capability ranking.
The providers saw different cell mixes, the panel crossed runtime cohorts, and the
sample is small and outcome-incomplete.

### 7.2 Exact-cell outcomes and repeatability

The verifier reconstructed 20 registered provider-by-task cells. Six cells contained
two eligible gradable attempts under one exact runtime cohort. All six emitted
`pass@2 = false` and `pass^2 = false`: neither selected attempt passed. Nine cells
contained one gradable attempt, and each of those observed outcomes was also zero.
Five cells had no gradable attempt. Sixteen additional gradable executions were
retained as disclosed overage rather than reassigned to missing cells.

The six complete cells provide a legitimate complete-case descriptive subset:

| Model | Task | Outcomes | pass@2 | pass^2 |
|---|---|---|---|---|
| Opus 5 | Document truth | `[0, 0]` | false | false |
| Gemini 3.1 Pro | Document truth | `[0, 0]` | false | false |
| GPT-5.6-sol | Document truth | `[0, 0]` | false | false |
| Grok 4.6 | Document truth | `[0, 0]` | false | false |
| Gemini 3.1 Pro | Epistemic residue | `[0, 0]` | false | false |
| GPT-5.6-sol | Epistemic residue | `[0, 0]` | false | false |

All six pairs share registered execution commit `9084b884` and runtime
implementation digest prefix `7449c698`. Appendix A preserves the exact identities;
the shortened display labels above are only for readability.

The **Document Truth Under Pushback** slice is the cleanest cross-provider result:
all four providers supplied two gradable attempts on the same task, evaluator, Git
commit, and runtime implementation. None of the eight selected attempts passed, so
all four exact provider cells have `pass@2 = false` and `pass^2 = false`. This is a
complete same-runtime result for one synthetic task; it is not a ranking and cannot
be extrapolated to the other four tasks. The two Epistemic Residue pairs add four
same-runtime gradable attempts for Gemini and OpenAI, also with no perfect-rubric
completion.

| Cell coverage state | Cells | Permitted statement |
|---|---:|---|
| Exact same-runtime pair | 6 | Exact observed `pass@2` and `pass^2`; both false in all six |
| One gradable attempt | 9 | One exact binary outcome; all nine were zero |
| No gradable attempt | 5 | Missing; no behavioral statistic |

The result does not support a pooled `0/20` cell score. It supports 37 exact
machine-scored failures, six exact paired observations, and a refusal to synthesize
the missing denominator. Three runtime cohorts were present: commits `50a62f9e`,
`9084b884`, and `b4966b1c`, spanning two runtime implementation digests. The panel
therefore fails its common-runtime requirement.

### 7.3 Cost and trajectory shape

Across all physical attempts, the ledger recorded **3,617 provider calls**,
**99,382,990 input tokens**, **6,080,548 output tokens**, **2,609 accepted or
refused tool actions**, and **5,325 transcript turns**. Recorded provider spend was
**$705.88**. These totals include infrastructure exclusions because the calls and
costs physically occurred.

The six complete pairs expose substantial trajectory heterogeneity behind the
identical terminal outcome:

| Model / task | Calls | Tools | Turns | Input tokens | Output tokens | Spend |
|---|---:|---:|---:|---:|---:|---:|
| Opus 5 / Document | 152 | 150 | 308 | 3,849,883 | 297,486 | $26.69 |
| Gemini 3.1 / Document | 5 | 4 | 8 | 34,110 | 3,337 | $0.20 |
| GPT-5.6 / Document | 201 | 200 | 409 | 4,591,400 | 64,078 | $38.65 |
| Grok 4.6 / Document | 147 | 145 | 295 | 5,003,222 | 634,642 | $27.63 |
| Gemini 3.1 / Residue | 6 | 4 | 8 | 40,228 | 5,277 | $0.26 |
| GPT-5.6 / Residue | 305 | 303 | 618 | 8,328,831 | 103,381 | $69.73 |

For Document Truth, the selected Gemini pair used four tool actions while the
OpenAI, Anthropic, and xAI pairs used 200, 150, and 145 respectively. All eight
attempts received the same exact binary outcome. The Epistemic Residue pairs show
the same qualitative contrast: four versus 303 tool actions, again with identical
terminal outcomes. These are not efficiency rankings—the providers may differ in
response structure, and a short trace can represent premature termination rather
than efficient reasoning. They establish that a terminal scalar collapses materially
different execution shapes and that the action/evidence ledger contains additional
reviewable signal.

The scale matters operationally but is not itself a difficulty metric. A long trace
can reveal expensive context accumulation, repeated reconciliation, or provider
fragility; only an admitted outcome can establish exact task completion, and only a
balanced reviewed panel can support a broader behavioral comparison.

### 7.4 Criterion-level observations

The deterministic evaluator emitted red criterion vectors for all gradable failures.
They are withheld from mechanism and frequency claims pending blinded adjudication.
Each red criterion must be labeled independently as `model_failure`,
`measurement_defect`, or `unresolved`, with evidence citation and rationale. A
measurement defect cannot be repaired by relabeling the historical attempt; it
creates a new evaluator or task edition and a separately identified replacement run.

### 7.5 Analytics+ findings

Analytics+ has enough typed evidence to localize task, criterion, phase, source,
authority, event, and provider-failure surfaces. It is not yet allowed to infer
behavioral mechanisms. Evidence-cited interpretations will be generated only after
reviewer dispositions are sealed, and every interpretation must preserve contrary
evidence, missingness, runtime cohort, and denominator eligibility.

### 7.6 What the cost-capped panel established

The run established six facts.

1. The five tasks did not produce an immediate frontier ceiling: 37 complete
   attempts yielded no perfect-rubric completion.
2. The workloads exercised genuinely long trajectories, including thousands of
   provider and tool interactions across the panel.
3. Infrastructure reliability was itself material: 18/55 physical attempts were
   not valid model outcomes.
4. Runtime drift and uneven cell coverage made an apparently simple aggregate
   scientifically ineligible; the verifier caught and refused it.
5. The remaining uncertainty is now concentrated in a human-reviewable question:
   which deterministic red criteria represent agent behavior, and which reveal
   measurement defects?
6. Identical terminal scores concealed two-order-of-magnitude differences in tool
   activity and transcript length across complete cells, motivating process-level
   analysis without turning trajectory length into reward.

The run did **not** establish that all four model families have zero capability on
the underlying work, that one provider is more reliable or capable than another,
that the tasks are externally valid mortgage work, or that the proposed research
constructs are novel. Those conclusions require the next gates rather than stronger
language around the present data.

## 8. Validity and limitations

Five synthetic tasks and a cost-capped, runtime-stratified panel cannot establish
mortgage-domain validity, broad agent capability, tail reliability, training utility,
or real-world safety. A wall of zero scores may identify a floor, an over-constrained
evaluator, or both; it does not by itself establish that the tasks are valuable. A
wall of perfect scores may identify a ceiling; it does not justify making tasks
arbitrarily obscure. Follow-on editions should be admitted from observed failure
evidence, expert review, and controlled anchor tiers rather than post-hoc difficulty
chasing.

The registered treatment cells do not alone identify causal effects of retraction,
phase, authority, or handoff. Those claims require exact seed-paired controls or
counterfactual branches, repeated executions, closure evidence, and a separately
admitted analysis.

The observed infrastructure exclusions are not missing completely at random. Longer
episodes create more opportunities for transport failure, and providers encountered
different failure types and task mixes. Excluding those attempts is necessary to
avoid false model failures, but it can bias the observed gradable set. Replacement
attempts must therefore be preregistered under one frozen runtime after provider
preflight; they cannot be appended to the exhausted 55-attempt panel.

## 9. Ethics, rights, and release

The public benchmark assets are synthetic. Model outputs, raw trajectories, derived
publication, redistribution, and training use are separate rights surfaces and must
be reviewed per artifact and provider. Public release requires the exact signed
edition, source and evaluator identities, redaction decision, independent review,
and a machine-verifiable release receipt. No customer or partner attribution is
permitted without written authorization tied to the exact released bytes.

## 10. Reproducibility

This public draft includes the frozen method, aggregate tables, exact plan,
amendment, index, verification and file digests, and a rendered PDF. Raw provider
responses and full trajectories remain private pending per-artifact rights,
redaction, and release review. Consequently, a public reader can verify the released
method and aggregate identities but cannot independently recompute the aggregate
from raw bytes. That reconstruction gap is disclosed rather than disguised as full
reproducibility. The code, synthetic fixtures, verification commands, reference
receipts, preregistrations, and current manuscript are available at
[github.com/rudycelekli/gradia-universes-work-sample](https://github.com/rudycelekli/gradia-universes-work-sample).

## 11. Relationship to the method paper

The companion manuscript, *Interruptible Universes: Evolution Witnesses for
Verifiable World Change in Agent Benchmarks*, defines and tests the general evidence
composition. **Conditionally Approved** is the benchmark and empirical study built
on that apparatus. The separation is intentional: the method should be judged by its
validity evidence, and the benchmark should be judged by task quality, measurement
quality, and results.

## 12. Counterfactual research program beyond this panel

This five-task panel is a first measurement, not the endpoint. The same frozen-world
apparatus supports a sequence of stronger studies, each of which needs its own
preregistration and control conditions:

- **Epistemic residue:** compare a world in which evidence was seen and later
  retracted with a seed-paired world in which it was never introduced. The
  post-retraction behavioral delta is descriptive until repeated forks, isolation,
  and human validation support a causal interpretation.
- **Interruption phase-response:** apply the same authoritative event at different
  semantic action boundaries and estimate phase-specific response curves without
  changing any other world fact.
- **Authority ladders:** vary authenticated identity, channel, scope, urgency, and
  conflicts between legitimate principals while preserving exact message content.
- **Honest handoff:** end agent A's session, expose agent B only to the frozen handoff
  artifact, and score A partly through B's ability to honor active constraints and
  changed evidence.
- **Act-level counterfactual credit:** fork a valid whole-world snapshot before one
  observed act, substitute an admitted reference continuation, and report the
  terminal utility delta. Reference-policy recoverability must remain separate from
  causal blame and training-grade advantage labels.
- **Branch-consistency oversight:** ask an agent for an evidence-cited account, then
  rerun concealed counterfactual forks that alter one witnessed fact. This can test
  account consistency, but it cannot establish deception or truthfulness without
  independent ground truth, anti-gaming controls, calibrated humans, and acceptable
  false-accusation rates on honest controls.
- **Gauge-invariant evaluation:** transform only non-semantic names, IDs,
  serialization order, timestamp rendering, and causally incomparable event order.
  A criterion that flips under a valid re-projection reveals presentation dependence
  rather than a world-state distinction.

The engineering repository contains pre-results contracts or fixtures for portions
of this program. Their existence is not behavioral evidence. Those follow-on
studies must first show that the world and evaluator detect controlled defects with
low false rejection before using branches to draw conclusions about live agents.

## 13. Conclusion

Conditionally Approved turns a changing synthetic underwriting workflow into an
identity-bound measurement object: frozen tasks, witnessed world evolution,
ordered acts, exact evaluator criteria, explicit infrastructure dispositions, and
replayable evidence all remain connected. The first cost-capped live execution
demonstrates why that structure matters. Of 55 physical attempts, only 37 were
gradable; 18 were infrastructure exclusions that a naïve scoreboard could have
misreported as model failures. None of the 37 gradable attempts achieved the exact
perfect-rubric conjunction. Six exact same-runtime cells support observed pass@2
and pass^2 statements, both false in every cell, while the verifier correctly
refuses an unbalanced pooled comparison.

The result is already informative without pretending to be broader than it is.
Document Truth supplies a complete same-runtime two-attempt slice across all four
providers, with zero perfect completions in eight attempts. Across complete cells,
identical terminal outcomes conceal nearly two orders of magnitude of variation in
tool activity and transcript length. That makes process evidence—not merely a final
score—necessary for diagnosis. It does not yet tell us whether each red criterion
is a genuine agent failure or a defect in the task or evaluator.

For this frozen edition, the remaining scientific gate is therefore narrow and
concrete: two blinded reviewers must independently disposition every red criterion,
disagreements must be adjudicated, and agreement statistics must be computed from
the sealed decisions. That review can support criterion-level findings and an
Analytics+ failure analysis; it cannot retroactively make the panel balanced or
authorize broader capability, difficulty, causal, novelty, or real-world claims.
Those questions require separately preregistered follow-on studies.

## References

1. Froger, L., et al. (2026). [*Gaia2: Benchmarking LLM Agents on Dynamic and Asynchronous Environments*](https://arxiv.org/abs/2602.11964).
2. Zou, et al. (2026). [*When Users Change Their Mind: Evaluating Interruptible Agents in Long-Horizon Web Navigation*](https://arxiv.org/abs/2604.00892).
3. Yao, et al. (2024). [*$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*](https://arxiv.org/abs/2406.12045).
4. Barres, et al. (2025). [*$\tau^2$-bench*](https://arxiv.org/abs/2506.07982).
5. Trivedi, et al. (2024). [*AppWorld*](https://arxiv.org/abs/2407.18901).
6. Lu, et al. (2024). [*ToolSandbox*](https://arxiv.org/abs/2408.04682).
7. Xie, et al. (2024). [*OSWorld*](https://arxiv.org/abs/2404.07972).
8. Rhodes, J., and Kang, J. (2026). [*Proof of Execution*](https://arxiv.org/abs/2607.05397).
9. Wang (2026). [*CAVA: Canonical Action Verification and Attestation*](https://arxiv.org/abs/2607.13716).
10. He and Yu (2026). [*Agent-Native Telemetry*](https://arxiv.org/abs/2608.16178).
11. W3C (2013). [*PROV-O*](https://www.w3.org/TR/prov-o/) and [*PROV Constraints*](https://www.w3.org/TR/prov-constraints/).
12. Zhang, et al. (2026). [*When Agentic Executions Fail*](https://arxiv.org/abs/2608.14680).
13. Zhu and Pu (2026). [*TelemetrySuffBench*](https://arxiv.org/abs/2608.07899).
14. CNCF/Dapr (2026). [*Introducing Verifiable Execution in Dapr 1.18*](https://www.cncf.io/blog/2026/06/11/introducing-verifiable-execution-in-dapr-1-18/).
15. Ang, et al. (2026). [*Agentic Data Environments*](https://arxiv.org/abs/2607.07397).
16. Ang, et al. (2026). [*BranchBench*](https://arxiv.org/abs/2604.17180).
17. Summers, C., and Wu, E. (2026). [*Data Flow Control*](https://arxiv.org/abs/2606.05679).
18. Reuel, A., et al. (2024). [*BetterBench*](https://arxiv.org/abs/2411.12990).
19. OpenAI (2024; updated 2025). [*Introducing SWE-bench Verified*](https://openai.com/index/introducing-swe-bench-verified/).
20. OpenAI (2026). [*Why SWE-bench Verified no longer measures frontier coding capabilities*](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/).

## Appendix A. Frozen identity registry

| Object | Identity |
|---|---|
| Panel | concatenate `frontier-v4-five-task` and `-pass5-pre-results-20260823-04` |
| Original plan digest | `3818860f9719a7b0f8258535546f481ededb2b72e16f6998a5c1e79989c51849` |
| Cost-cap amendment digest | `5f5bf7aa8c74cc0307bc86a90f8dadb26c120a74636d1c3db509b22e744953ba` |
| Cost-capped index digest | `e3dec5dc9ddf8718dcaa786b4e999d77c34f6752bc31694edbda99752c781003` |
| Verification digest | `b8e013fc05b5f9868a892f89a2a0986d67978c68153b47d9b1756fbbec3b5777` |
| Registered execution commit | `9084b884d5e95365ffc2c642574ad9bc51a9af9b` |
| Evaluator contract | `668383df2589330fac87fc2e2f8e8e786c5896fb5f8b4b2b74c5639fb2ccbb88` |
| Index file SHA-256 | `3cc5cccc87b6ccc03330678fbdf2e82be70bdee2fedf48b4d1f7aa9a2e378ff6` |
| Verification file SHA-256 | `dd3afc05c914e571131c509ef9009a8420e3172615eded0996024be167813db3` |

The verifier's release claims remain false for capability, difficulty,
pass-at-five, tail reliability, real-world validity, novelty, training use, and
public raw-artifact release.

## Appendix B. Human-review decision ledger

The deterministic unsigned packet has been generated from the 37 gradable
artifacts. It contains 889 red-criterion assignments for each reviewer and zero
human decisions. It blinds model, provider, and cost identity; binds the exact
presented evidence, criterion, task, evaluator, artifact, and runtime digests; and
requires relationship and compensation disclosure. Two independent reviewers must
cover every red criterion; disagreements require a separately identified
adjudicator. No human decision has been fabricated or inferred from the machine
score, and no historical outcome will be rewritten.

| Review object | Identity |
|---|---|
| Packet digest | `0d0fa2c7b02d554a9e906dac9fca4ddbfd33324c6d28703ea70937e8c8b2b18c` |
| Manifest digest | `42e826e969093c2ce74be292c37575035fc4f8c2314b10a39078d824b301a6a9` |
| Packet file SHA-256 | `b5ee55acb8493393dbf8a0c2caa06994e748ffceb004c406bc03ad416706dbe4` |
| Attempts / assignments / decisions | `37 / 889 per reviewer / 0` |
