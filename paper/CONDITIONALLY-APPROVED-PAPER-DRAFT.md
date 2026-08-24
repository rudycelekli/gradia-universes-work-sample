---
title: "Conditionally Approved: A Proof-Bound Mortgage Benchmark for Long-Horizon AI Agents Under Changing Evidence, Authority, and Time"
author: "Rudy M. Celekli, Gradia Research"
date: "Pre-results working draft - 24 August 2026"
---

> **Pre-results boundary.** This manuscript names the frozen study and locks its
> reporting structure while execution is in progress. It does not yet claim model
> performance, comparative superiority, frontier difficulty, human agreement,
> mortgage-domain validity, causal effects, or novelty. Every empirical statement
> must be regenerated from the sealed machine-readable panel and must survive the
> evaluator- and human-admission gates described below.

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

Exact-cell pass-at-two, strict two-attempt consistency, cost, trajectory shape,
failure signatures, and Analytics+ interpretations will be inserted only after the
cost-capped inventory is sealed and independently verified. Missing cells remain
missing rather than being replaced by a pooled statistic. Behavioral interpretation
is reserved for blinded human review. The benchmark was built and verified with the
Gradia Universes platform; Gradia is the execution and evidence system, not the
benchmark name.

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

> **Locked shell — do not hand-edit empirical values.** Tables and figures in this
> section must be generated from the sealed aggregate artifact.

### 7.1 Completion and exclusions

_Pending sealed panel._

### 7.2 Exact-cell outcomes and repeatability

_Pending sealed panel._

### 7.3 Cost and trajectory shape

_Pending sealed panel._

### 7.4 Criterion-level observations

_Pending blinded human adjudication._

### 7.5 Analytics+ findings

_Pending evidence-cited interpretation and human disposition._

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

## 9. Ethics, rights, and release

The public benchmark assets are synthetic. Model outputs, raw trajectories, derived
publication, redistribution, and training use are separate rights surfaces and must
be reviewed per artifact and provider. Public release requires the exact signed
edition, source and evaluator identities, redaction decision, independent review,
and a machine-verifiable release receipt. No customer or partner attribution is
permitted without written authorization tied to the exact released bytes.

## 10. Reproducibility

The release will include the frozen task and evaluator editions, model and runtime
identities, preregistrations, provider-normalized receipts, aggregate generator,
verification commands, result tables, figure sources, and a rendered PDF. Any raw
artifact withheld for rights or security reasons must be named in a reconstruction-
gap report rather than silently omitted.

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
of this program. Their existence is not behavioral evidence. The next scientific
step is to show that the world and evaluator detect controlled defects with low
false rejection before using branches to draw conclusions about live agents.

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

_Generated after the panel seals; includes task, plan, runtime, model, evaluator,
artifact, aggregate, and release digests._

## Appendix B. Human-review decision ledger

_Generated from blinded review; records agreement, disagreement, adjudication, and
any task/evaluator defect without rewriting historical model outcomes._
