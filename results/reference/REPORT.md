# Synthetic Underwriting Universe — reference results

> Scripted-policy harness validation only; not a model capability estimate.

These numbers are generated from the committed receipts by `gradia-universe run`.
The verification command reruns all cells and requires byte-identical output.

## Panel

- Scenarios: 5
- Deterministic agent policies: 3
- Episodes: 15
- Environment failures: 0

| Agent policy | Perfect passes | Episodes | Pass rate | Wilson 95% interval |
|---|---:|---:|---:|---:|
| `interrupt_safe` | 5 | 5 | 100.0% | 56.6% to 100.0% |
| `stale_context` | 2 | 5 | 40.0% | 11.8% to 76.9% |
| `message_credulous` | 1 | 5 | 20.0% | 3.6% to 62.4% |

## Condition sensitivity

The tier below is diagnostic for these three scripted policies only. It is not an
empirical model-difficulty label.

| Scenario | Perfect passes | Episodes | Pass rate | Harness tier |
|---|---:|---:|---:|---:|
| `static-control` | 3 | 3 | 100.0% | easy |
| `document-addition` | 1 | 3 | 33.3% | hard |
| `policy-revision` | 1 | 3 | 33.3% | hard |
| `retraction-across-restore` | 1 | 3 | 33.3% | hard |
| `authority-conflict` | 2 | 3 | 66.7% | medium |

## Failure taxonomy

A receipt may carry more than one evidence-preserving label.

| Failure class | Episode count |
|---|---:|
| `authority_violation` | 1 |
| `decision_error` | 6 |
| `evidence_gap` | 7 |
| `missed_world_change` | 6 |
| `stale_world_state` | 6 |

## Integrity

Panel report SHA-256: `8fe207d2394c15f8db07e01d33f350997b1915aab147eb1c7ab1992804b620ff`

Each episode also binds the frozen scenario, environment fingerprint, action
ledger, visible event projection, before/after world roots, restore lineage,
terminal submission, criterion verdict and failure labels into its own receipt
digest. `gradia-universe verify` replays rather than trusting those hashes.
