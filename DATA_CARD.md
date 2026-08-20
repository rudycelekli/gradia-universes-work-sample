# Synthetic data card

## Scope

The repository contains one fictional underwriting workflow with five small
control conditions and a separate five-task frontier-candidate queue suite.
The queue suite has four fictional cases and six synthetic source types. Names,
identifiers, financial values, policies and event stories were authored for
this repository. They are not derived from a lender, applicant, credit bureau
or customer system.

## Intended use

- reproduce event application, visibility, restore and judging semantics;
- test whether an agent adapts to additions, revisions and retractions;
- test authority handling and stale-context failures;
- inspect exact denominators and tamper-evident receipts; and
- test coupled queue decisions, shared capacity and pass@5 reliability; and
- exercise Gradia's public API contract from an external client.

## Prohibited interpretation

The synthetic policy is not legal, lending, underwriting or compliance advice.
Scripted-control pass rates validate this fixture and harness; they do not
estimate model performance in a real institution or population. Frontier
difficulty remains unmeasured until frozen live panels and human calibration
pass. No fairness, safety or production-readiness conclusion may be drawn from
these synthetic tasks.

## Rights

Code and synthetic fixtures are released under Apache-2.0. Generated result
bundles inherit the same license unless a live-model provider's terms require a
more restrictive distribution posture; that must be reviewed before release.
