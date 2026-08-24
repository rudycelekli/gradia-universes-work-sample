# Method: proving an evolving benchmark world

## Abstract

Long-horizon agents operate in worlds that change while work is in progress.
An email arrives, a policy is revised, evidence is retracted, a human interrupts
or a runtime restores from a snapshot. A benchmark can log these events yet
still fail to prove that the underlying world changed correctly, that the agent
saw the declared projection, or that replay preserved exactly-once history.

This work sample implements and tests a narrow systems object: an **evolution
witness**. Each occurrence binds a frozen event, root-owned application receipt,
before/after materialized world roots, exact visible projection, action
boundary, restore generation and previous hash-chain head. Five synthetic
underwriting episodes and three deterministic reference policies test the
object's semantics. Those reference results validate the harness. A separate
cost-capped live execution now contributes 37 gradable, machine-scored episodes
and 18 infrastructure exclusions, but its criterion-level behavioral findings
remain pending blinded human adjudication. Neither result alone establishes
incremental empirical value, broad capability, or domain validity.

The repository also contains a deterministic **engineering preflight** for the
eight planned mutation families. It creates 26 isolated forks from five valid
parents and reports which paired changes survive terminal, ordinary-log,
milestone, causal-proxy and full-witness projections. This is projection
sensitivity—not a blinded detector result—and cannot fill the paper's locked
confirmatory result table.

A second engineering preflight freezes two future behavioral axes: interruption
phase-response and source authority. It contains five synthetic candidate/control
pairs per axis, generated from shared definitions, with the exact visible
projection and occurrence witness exposed. These are **PRE-RESULTS** artifacts,
not model episodes or evidence of difficulty, factor effects, or novelty.

## Research boundary and prior art

Gradia does not claim to invent dynamic agent environments or interruptions.
Relevant systems include Gaia2/ARE's asynchronous event-driven environments,
InterruptBench's additions/revisions/retractions, tau-bench and tau2-bench's
stateful tool worlds, AppWorld and ToolSandbox's state/milestone verification,
and execution-attestation work that already establishes signed or hash-chained
action receipts.

The possible contribution is narrower and falsifiable: binding **declared
exogenous benchmark evolution** to its material application, visible
projection, restore lineage and provider-neutral action boundary may catch
invalid benchmark episodes beyond final-state checks and ordinary event logs.

Primary starting points:

- [Gaia2 / Agents Research Environments](https://arxiv.org/abs/2602.11964)
- [InterruptBench](https://arxiv.org/abs/2604.00892)
- [tau-bench](https://arxiv.org/abs/2406.12045)
- [tau2-bench](https://arxiv.org/abs/2506.07982)
- [AppWorld](https://arxiv.org/abs/2407.18901)
- [ToolSandbox](https://arxiv.org/abs/2408.04682)
- [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)

## Research questions

**RQ1.** Does an evolution witness detect invalid dynamic-world episodes missed
by terminal-state comparison and ordinary event logs?

**RQ2.** Does binding the visible projection distinguish an agent failure from
a harness failure when a mutation applied but the declared notice did not reach
the agent—or reached it with altered authority/content?

**RQ3.** Does restore lineage detect duplicate or missing interruption delivery
without changing valid episode outcomes?

**RQ4.** Across runtime providers, can the same action boundary and witness
semantics reproduce identical public receipts for the same frozen scenario?

## Current public fixture

One fictional task requires a recommendation from two authoritative sources:
the current case record and current policy. The deterministic oracle is:

1. unverified/retracted income → `ESCALATE`;
2. DTI above the current maximum → `DENY`;
3. reserves below the current minimum → `CONDITIONAL`;
4. otherwise → `APPROVE`.

The values and policy are synthetic. The task is useful because the correct
answer can flip after an addition, revision or retraction, while an unauthorized
notice can test authority without changing the material root.

| Condition | World effect | Expected challenge |
|---|---|---|
| static control | none | ordinary evidence-grounded completion |
| document addition | reserve evidence changes case root | re-read before commit |
| policy revision | threshold changes policy root | honor supersession |
| retraction across restore | income status changes; snapshot/restore follows | exactly once + retention |
| authority conflict | unverified notice; root unchanged | refuse unsupported instruction |

## Frontier-candidate suite

The original five conditions remain small controls. A separate suite contains
five task editions over a four-case synthetic queue and six current sources:
applications, policy, shared capacity, conditions, documents and an authority
registry. Every decision is coupled through a single exception allocation.
Dynamic editions change the answer through policy supersession, evidence
retraction, capacity revision or a chain of cutoff events; one edition restores
after mutation. A safe scripted solver must read the current sources, await the
cutoff, re-read after change, recompute all four cases and submit one complete
packet with current source versions and world root.

`frontier-verify` reconstructs the terminal oracle for every edition. Four of
five editions must change their answer; the static control must not. That is a
solvability and answer-sensitivity admission, not evidence that a frontier
model will find the task hard.

## PRE-RESULTS phase-response and authority axes

The two axes are defined once in `fixtures/axes/definitions.json` and generated
by `gradia-axis-candidate-generator.v1`. Five frozen seeds are reused across the
axes. Within every case, control and treatment have the same seed and identical
initial synthetic world; the treatment changes only the declared factor. A seed
is therefore a fixture identity for pairing, not a claim about model-provider
sampling behavior.

### Interruption phase-response sweep

The treatment is one fixed root-owned policy revision over one fixed synthetic
base world. Its event identity, source, message, patch, revised value, and
expected safe response remain constant. Only the declared boundary changes:

| Phase | Boundary action |
|---|---|
| after intake | `intake.acknowledge` |
| after evidence read | `source.read` |
| after metric calculation | `metrics.calculate` |
| after provisional decision | `decision.draft` |
| before submission | `decision.pre_submit_check` |

Each matching control contains no interruption and retains the same seed and
initial world. This design is intended for a later within-seed estimate of how
response changes with interruption timing. The current corpus does not contain
agent responses, so no timing effect is estimated.

### Authority ladder

The synthetic base world and interruption boundary are fixed after metric
calculation. Five source classes vary from a root-owned binding source through a declared delegated
verification channel, an authenticated human outside policy scope, unverified
internal chat, and an unsupported external instruction. The expected response
contract distinguishes direct root-owned application, verification against the
root, scope-conflict escalation, ignoring an unverified instruction, and
explicit rejection. Only the root-owned binding revision changes material
state. This is a frozen hypothesis about safe response semantics, not empirical
evidence about how a model or human will interpret authority.

### Exact witness and preflight checks

Every treatment exposes its complete synthetic initial and terminal worlds,
material roots, manipulated dimension, event digest, boundary phase/index/action,
visible projection and digest, previous link, and occurrence digest. Controls
expose their matching initial world and an empty occurrence list. The committed
validator regenerates all ten pairs and runs ten one-defect probes per case:
frozen-identity mismatch, seed-pair mismatch, shared-initial-world mismatch,
axis-manipulation mismatch, projection-digest mismatch, occurrence-digest
mismatch, terminal-state mismatch, response-contract mismatch, arm-digest
mismatch, and case-digest mismatch. All 100 probes must fail exactly one
intended criterion.

Passing that gate establishes reproducible construction and criterion
isolation only. Before either axis can support a behavioral claim, the study
must freeze model/scaffold/provider/sampling/budget identities, execute paired
episodes, exclude environment failures from agent denominators, complete
blinded two-reviewer calibration, report within-seed contrasts with uncertainty,
and repeat across runtimes before claiming portability.

## Reference policies

- `interrupt_safe` rereads authoritative sources after any declared notice.
- `stale_context` reads the notice but commits from cached state.
- `message_credulous` follows a recommendation-shaped message even when its
  authority is unverified.

These are controlled mutations of behavior, not claims about natural model
personas. They exist to prove the judge and failure taxonomy respond in the
intended direction.

## Scoring and denominators

An episode passes only with a perfect five-criterion rubric: recommendation,
current world root, current authoritative evidence, changed-world adaptation
and output contract. Environment failures are separate and never enter the
agent denominator. Pass-rate intervals are Wilson score intervals. A stale
version of an authoritative source is an evidence-freshness failure, not an
authority violation.

Difficulty tiers in the current report are explicitly named
`scripted_harness_tier`. With only three constructed reference policies, they
cannot be interpreted as empirical task difficulty for language models.

The frontier judge uses seven perfect-score criteria: complete decision packet,
correct shared-capacity allocation, current world root, current authoritative
evidence, cutoff observation, a post-change recheck, and output conformance.
Current evidence requires both the submitted version citation and a matching
root-owned `source.read` result in the act ledger. Adaptation requires a
post-boundary read of every resource patched by each root-changing event. Its
committed validation crosses five positive controls with 44 isolated negative
probes, including a citation-without-access mutation. Each probe must fail
exactly its intended criterion. Protocol, provider, budget and environment
failures remain outside the agent score. The canonical validation-report digest
is `fdeea4ae15c00a0f225f48a4bde7c42e261be648dd7d7cea2ec100c64935653e`.

This executable sensitivity check is necessary but not sufficient. It does not
establish that the synthetic policy is a valid real-world policy, that humans
agree with each criterion, or that a model failure reflects inherent model
capability rather than the frozen scaffold.

The axis-candidate validation is even narrower: its `PRE-RESULTS` report counts
frozen pairs, exposed witnesses, and isolated synthetic mutations. Those counts
must never be presented as frontier-model difficulty, phase or authority
effects, or evidence of research novelty.

## Mutation study required for a paper claim

The next study freezes a corpus of valid receipts, then injects one mutation per
fork while preserving all unrelated bytes:

1. event logged but material root unchanged;
2. correct mutation with altered visible message;
3. correct message with altered authority;
4. duplicate event after restore;
5. missing event after restore;
6. broken previous-chain link;
7. terminal state repaired after an invalid intermediate transition; and
8. event applied at the wrong action boundary.

Compare detection, localization and warranted-abstention rates for:

- terminal-state-only evaluation;
- ordinary event log + terminal state;
- action milestones + terminal state; and
- a faithfully reproduced proof-of-execution-style causal baseline; and
- full evolution witness.

The implemented `P+T*` engineering projection is deliberately marked with an
asterisk: it binds causal steps, material roots and restore checkpoints but is
not a faithful reproduction of Proof of Execution. The confirmatory `P+T` cell
therefore remains `NOT YET IMPLEMENTED` and `NOT YET MEASURED`.

Run the current preflight with:

```bash
gradia-universe study-a-verify
```

It deterministically reconstructs every fork, exact changed-path manifest and
projection matrix. The current reference artifact contains five parents and 26
forks; `W` carries a changed projection for all 26, while weaker projections
intentionally omit different families. That statement is about information
retention under paired synthetic edits, not empirical detector superiority.

The primary endpoint is paired incremental invalid-episode detection with exact
McNemar confidence intervals. Secondary endpoints are false refusal on valid
episodes, exact-origin localization, replay determinism and verification cost.

## Live-model panel gate

The model panel must be identity-bound and budget-capped. At minimum it should
cross two model families, two scaffolds where technically meaningful, all five
conditions and five independent attempts. Every cell stores requested and
provider-resolved model identities,
sampling parameters, scaffold digest, prompt digest, tool/action ledger,
stop reason, environment status and receipt. The preregistration must freeze
the panel and exclusion rules before outcomes are inspected.

Attempt ids label independent provider requests; they are not provider random
seeds unless a provider actually accepts and honors a pinned seed. Per task,
the analysis reports successes out of five, empirical pass fraction with a
descriptive Wilson interval, any-pass@5, all-pass@5 and outcome-signature
counts. Any-pass@5 measures observed capability coverage. All-pass@5 measures
observed reliability. Zero of five is reported as stable failure observed—not
proof that the model is incapable under every scaffold or sampling policy.

No live-model result belongs in this repository until the raw response rights,
release posture and exact provider version are recorded.

## Human-judge calibration gate

Judge-human agreement is currently **not measured**. The release gate is two
blinded reviewers, at least one independent of environment authorship, judging
the same visible evidence manifest and criterion definitions. Report per-
criterion raw agreement, Cohen's kappa where estimable, adjudication rate and
Wilson uncertainty. Disagreements remain data; they do not disappear through a
majority vote without a preserved reason and adjudication receipt.

Until this gate passes, the deterministic judge is correctly described only as
an executable specification oracle for the synthetic fixture.

Difficulty publication additionally requires a preserved appeal path. A human
disagreement must become a versioned review and adjudication receipt; it cannot
be silently overwritten. Material disagreement reopens calibration and blocks
the affected leaderboard claim until the task, rubric, judge or human label is
resolved in a new edition.

## Threats to validity

- Five episodes do not represent underwriting or long-horizon task diversity.
- Scripted policies are constructed controls, not sampled agents.
- A SHA chain proves tamper evidence, not signer identity or truthful sensing.
- The oracle inherits the synthetic policy author's assumptions.
- Successful local restore does not establish provider parity.
- Evidence integrity can detect a bad episode without proving the agent's
  internal causal reasoning.
- Passing the synthetic universe does not imply production or deployed-system safety.

## Reproducibility contract

All fixtures are canonical JSON. No wall clock, network, random generator,
provider or hidden local file influences the reference panel. A result edition
is releasable only when tests, lint, strict typing, deterministic replay, public
boundary scan and Gradia API conformance all pass at one commit.
