# LoanWorld v0: a branchable mortgage universe for end-to-end agents

**Status:** PRE-RESULTS engineering edition. Phases 0–2 are built. No agent or model has run, and nothing here claims difficulty, validity, ranking, novelty or real-workflow relevance. Everything is synthetic.

LoanWorld puts an agent in charge of a whole synthetic purchase-loan file. The agent reads captured documents, talks to parties, orders services, clears conditions and writes to an LOS, then submits a pre-check recommendation with cited claims. Meanwhile the world changes under it. The engine is this repository's: root-owned state, snapshot/restore and one exactly-once hash chain of occurrences. LoanWorld widens the state into typed loan ledgers.

## What exists (phases 0–2)

| Phase | Piece | Where |
|---|---|---|
| 0 | Typed scenario contract `gradia-loanworld-scenario.v1` (fails closed) | `src/gradia_universes/loanworld/schema.py` |
| 0 | World and engine with the public engine's semantics (shared `verify_occurrence_chain`) | `loanworld/world.py`, `world.py` |
| 0 | Design preregistration: git-pinned, self-digested, $0 cap | `loanworld/prereg.py`, `preregistrations/loanworld-v0-design-*.json` |
| 1 | Seeded gold-parent generator: SHA-256 draws, integer cents, integer centipoints | `loanworld/generator.py`, `loanworld/draws.py` |
| 1 | Committed parent `loanworld-parent-dev-001`: 9 documents, 8 uploads, 108 critical values with exact boxes, planted traps, 7 conditions, 7 principals with authority rules, 6 service stubs, an LOS mock with a legacy SSN field labelled as contact data | `fixtures/loanworld/parents/` |
| 1 | Optional pixel renderer: K0 PDF (with a text layer that lies), K1 scan, K2 phone, K3 fax, K4 copy, plus a manifest of SHA-256 hashes and page-corner quads | `loanworld/render.py` (extra `loanworld-render`) |
| 2 | Tool API: 14 tools, one act and one chained receipt each, external effects with idempotency keys, offline proof packs | `loanworld/tools.py` |
| 2 | System-mode adapter: `gradia.loanworld.stdio.v0` JSON lines, censoring of infrastructure failures | `loanworld/adapter.py`, [LOANWORLD-ADAPTER.md](LOANWORLD-ADAPTER.md) |
| 2 | Null control policy (always escalate) | `loanworld/policies.py` |

## Commands

```bash
.venv/bin/gradia-universe loanworld-build --seed dev-001     # writes fixtures/loanworld/parents/
.venv/bin/gradia-universe loanworld-verify                    # regenerate from seed + null control
.venv/bin/gradia-universe loanworld-tools                     # agent tool manifest
.venv/bin/pip install -e '.[loanworld-render]'
.venv/bin/gradia-universe loanworld-render --scenario fixtures/loanworld/parents/loanworld-parent-dev-001.json --out /tmp/lw
.venv/bin/gradia-universe loanworld-prereg-verify --file preregistrations/loanworld-v0-design-20261018.json
```

## Design rules this edition keeps

- **The agent sees a projection, never truth.** Case truth, critical values, trap labels and the authenticity of a message's sender stay private. A test asserts that the SSN and the hidden debt never appear in the projection, until a credit pull legitimately returns the debt.
- **Pixels, not text, for captures.** Image uploads have no text layer, so an agent without OCR has to escalate. Native PDFs expose a text layer that can disagree with the rendered page (trap T-ADV on the VOE).
- **Every call costs an act and leaves a receipt.** That includes failed calls. Receipts chain to each other and bind the arguments, the response and the world root before and after the effect.
- **Rolling back a branch cannot unsend a message.** `LoanWorldSession.restore(..., already_sent=...)` records a re-sent effect as `duplicate_after_restore`.
- **Censoring is not scoring.** Timeouts, malformed output, agent exits and act-budget exhaustion are reported as `censored`, never counted as model zeros.
- **Handwriting is a placeholder in v0.** It is rendered from a font and labelled `font_placeholder_not_valid_for_test`. Test splits need a consented writer corpus.

## Known limits

- **One parent.** It has two benign events: an LO notice and a clock advance. The single-factor fork catalog is phase 3.
- **No oracle yet.** The terminal oracle, the critical-failure detectors and the Wind Tunnel attack on the grader are phase 4. Nothing is graded yet.
- **The renderer covers K0–K4 only.** K5–K8 raise `NotImplementedError`. Byte-identical renders are promised only at the pinned `pymupdf`, `numpy` and `pillow` versions.
- **Receipts are LoanWorld's own format.** Mapping them onto Gradia Guard's SDK bundle is future work. No Guard ABI compatibility is claimed.
- **Generic data only.** The LOS mock and condition taxonomy are generic and synthetic. They contain no lender's private data or field dictionary.
