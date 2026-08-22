# Frontier-plus task engineering checkpoint

**Status:** PRE-RESULTS · review artifact · not a benchmark release

**Checkpoint date:** 2026-08-21

**Author:** Rudy M. Celekli, Gradia

## Why publish this checkpoint

Gradia is hardening five synthetic long-horizon task candidates before spending
on a repeated frontier-model panel. This document exposes the present design and
the defects found while making its evaluator executable. It is meant to invite
criticism before live results make design changes scientifically expensive.

It does **not** claim that the tasks are frontier-hard, realistic enough for a
customer domain, novel, or suitable for training. It contains no customer data
and names no design partner. The implementation and generated manifests remain
outside this public repository while their release boundary is reviewed, so the
identifiers below are review handles rather than independently reproducible
public evidence.

## The five candidates

Each candidate uses six fully synthetic cases in one shared work queue. The
common world evolves over 120 simulated business hours and introduces a policy
revision, a capacity reduction, a source-condition revision, market repricing,
a document-system outage and recovery, a moved close, a close deadline, an
expiring lock and an unverified volume-pressure message. Each task then adds a
different primary construct.

| Candidate | Primary construct | Exact criteria | Positive-control acts | Control evidence identifier |
|---|---|---:|---:|---|
| `pilot.document-truth-under-pushback.v2` | Reconcile incomplete and superseded document evidence while resisting unsupported pressure | 24 | 125 | `27fe4b08746620e6003342ee42fc786e44b73a4c0eef8e1cfe4b12cd2566485e` |
| `pilot.epistemic-residue.v2` | Retract evidence, recompute downstream decisions and distinguish the retracted path from a never-seen counterfactual | 26 | 130 | `38f8c3e840aa661a570be96664d5ac1a84fc6b7a880424cd6c57c7823a690cf6` |
| `pilot.authority-and-fair-judgment.v2` | Resolve source authority, conflicting principals and evidence-supported escalation without using protected traits | 24 | 112 | `6158f3a7ead82a45e9fd65a002955c049f743ee3f6b8273426a995b2b4bc4400` |
| `pilot.temporal-portfolio-control.v2` | Manage coupled cases under deadlines, capacity constraints, interruptions and time-dependent source changes | 18 | 93 | `7cf75e9fdb83f6e5fb8fde279c8b242acec40de012b5be7ee69149d00566f565` |
| `pilot.honest-handoff-and-verified-commit.v2` | Produce an artifact-only cold handoff whose quality is measured by a successor's verified outcome | 24 | 129 | `240667a5c227f3811715f9b3bb14d2fdafb5dd2a8a794bd14a99bf14f41ba6f3` |

The positive controls execute through the real task gateway, scenario engine,
sandbox and exact live grading function. Their purpose is only to establish
that the current synthetic tasks have a known passing path. A deterministic
solver passing does not establish language-model difficulty or construct
validity.

## An important open horizon defect

Every candidate currently declares a target of at least 140 expected acts, but
the deterministic controls above use 93–130 acts. The declaration is therefore
design metadata, not an execution-enforced horizon guarantee. Calling these
tasks “140-act tasks” would be an overclaim.

The gate remains open until the design requires at least that many
**meaningful, construct-relevant** observations or actions and both the positive
control and admitted live runs prove the requirement. Padding a trace with
status checks would increase length without increasing difficulty and will not
close the gate.

## What evaluator hardening already caught

The evaluator was not accepted merely because the positive controls passed.
Exact criterion probes exposed three defects:

1. The authority candidate initially queried superseded v1 source references
   after common revisions had made them stale. The evaluator was asking for an
   impossible combination of current behavior and old evidence.
2. The residue check initially searched the entire multi-case terminal packet.
   A number belonging to another case could be mistaken for reuse of retracted
   evidence. The check is now scoped to the affected synthetic case and decision.
3. The residue comparison initially required the latest duplicated response
   rather than a valid before/after comparison across the exact retraction
   boundary. It now accepts the intended evidence pair and rejects stale reuse.

The live sandbox grade now calls the same pure, probeable full-check function
used by the mutation screen. This removes a dangerous class of tests that
validate an abstraction while production executes a different reward surface.

## Dependency-aware mutation screen

The current candidate manifest contains one declared mutation target for each
of 116 exact criteria. Every target was detected by the full evaluator, but some
mutations correctly trigger dependent criteria as well:

| Detected criterion-closure size | Mutation count |
|---:|---:|
| 1 | 91 |
| 2 | 17 |
| 3 | 1 |
| 4 | 4 |
| 5 | 3 |

Per-candidate targets are 24, 26, 24, 18 and 24, matching the task criteria.
The current private manifest review identifier is
`a6cd9d9138f7fd7f86aadd2a4380eb5e2e56dee2e3ac38548596ba4047105bdb`.

This screen is still **ineligible for admission**. The observed closures need an
independent semantic review, and the runtime must bind the exact root-owned
world, action boundary, visible projection and evaluator version. Detecting a
mutation in a local object is not proof that a hosted episode produced the same
evidence.

## Gates before a paid live panel

The five candidates are ready for review, not for a headline result. The next
edition must satisfy all of the following:

1. Replace the unenforced act declaration with meaningful execution-level
   horizon evidence.
2. Complete independent expected-closure review for all 116 mutations.
3. Bind each outcome to the exact scenario edition, occurrence chain, act
   ledger, model/scaffold identity and eligible evaluator-admission report.
4. Run a small capped diagnostic first and stop if the task is obviously easy,
   broken, truncated or evaluator-sensitive.
5. Freeze any v1+ correction before a repeated pass@5 panel. Never harden after
   seeing confirmatory model identities and then report the result as
   preregistered.
6. Obtain blinded human review of solvability, rubric meaning, disagreement and
   adjudication.
7. Keep empirical capability, causal effect, customer validity, novelty,
   training utility and public-release claims false until their separate gates
   pass.

## What reviewers can challenge now

The most useful review is not “does this look hard?” It is:

- Which required behavior can be satisfied through a shortcut that bypasses
  the intended construct?
- Which criterion has more than one reasonable interpretation?
- Which event, artifact or authority transition is not observable to the agent
  at the moment the evaluator expects it?
- Which coupled obligation creates accidental impossibility rather than useful
  difficulty?
- Which mutation closure is semantically wrong?
- Which common event adds realistic load, and which merely adds noise?

Those questions determine whether the next public artifact measures agent
capability or only benchmark-author confidence.
