# Live-model panel runbook

This runbook turns the deterministic harness into a real provider/model cell
without turning a convenient command into an uncontrolled bill or an
unqualified public claim.

## Experimental rule

The baseline holds the scaffold constant across providers. Every turn receives
the same compiled transcript and must return one JSON action. Provider-native
tool calling is scientifically valuable, but it is a different scaffold and
therefore belongs in a separately named condition.

The adapters use the providers' current public REST surfaces:

- OpenAI Responses API;
- Anthropic Messages API;
- xAI Responses API; and
- Gemini `generateContent` API.

The contracts were rechecked against the four providers' official references
on 2026-08-21. The receipt records both the requested model id and the model
identity returned by the provider. A missing or different returned identity
makes the cell ineligible and latches the adapter after the paid request. This
refuses missing identity evidence or a visible server-side divergence. It does
not prove that a provider-returned family label is immutable, so the operator
must choose a versioned id whenever the provider exposes one.

Model identifiers are never supplied by this repository. Choose and record an
exact currently available model id immediately before preregistration. Avoid
aliases such as `latest` when the provider offers a versioned id.

The common frontier cell fixes explicit `high` reasoning across all four
adapters: Responses receives `reasoning.effort`, Messages receives
`output_config.effort`, and Gemini receives
`generationConfig.thinkingConfig.thinkingLevel`. Temperature is omitted and
recorded as provider-default because the current frontier reasoning surfaces do
not share one portable temperature contract. A different reasoning level or
sampling posture requires a separately named preregistration.

## Credential boundary

Set exactly one environment variable in the local shell:

```bash
export OPENAI_API_KEY='...'
export ANTHROPIC_API_KEY='...'
export XAI_API_KEY='...'
export GEMINI_API_KEY='...'
```

Use only the variable required for the selected provider. Do not paste a key
into an issue, manifest, command argument or result file. The public scanner
refuses common literal-key shapes and local user paths.

## Cost boundary

Look up the selected model's current input and output prices from the provider
immediately before running. The command treats those numbers as an operator-
supplied estimate, not a provider invoice. Before every request it reserves a
conservative UTF-8 upper bound for input tokens plus the full allowed output.
It refuses before the request if the cumulative reservation could exceed the
cost cap. A dispatched request consumes its reservation even if the provider
times out or returns unusable evidence, because the call may still be billable.
For Gemini reasoning models, billable output accounting includes thinking
tokens rather than only visible candidate text. The parsed usage produces a
separate operator-price estimate; neither number is an invoice. The adapter
sends `store: false` where the API exposes that request control. This is a
storage/logging preference, not proof of zero data retention, and does not
override account settings, provider terms or an approved data-control program.
These local ceilings are safeguards, not substitutes for provider-account
spend limits.

First run exactly one non-benchmark provider-protocol request. It verifies the
endpoint, returned model identity, usage fields, retention sink and budget
reservations without revealing how a model behaves on any frozen task:

```bash
.venv/bin/gradia-universe provider-smoke \
  --run-id '<provider>-protocol-smoke-001' \
  --provider '<openai|anthropic|xai|gemini>' \
  --model '<exact-model-id>' \
  --max-output-tokens 512 \
  --max-cost-usd '<approved-cap>' \
  --input-usd-per-million '<current-price>' \
  --output-usd-per-million '<current-price>' \
  --confirm-live-spend \
  --confirm-private-response-retention \
  --confirm-provider-account-spend-limit
```

The smoke writes `benchmark_task_or_score_present=false`. It is not a
release-eligible frontier cell. The confirmations are operator attestations,
not legal or provider-side proofs.

The operating rule is to preregister the longer frontier-candidate suite before
any paid outcome is inspected. Run this only from a clean public tree. The
command freezes the clean code commit, exact scenario/admission/judge/analysis
digests, provider/model identity rule, sampling posture, public official-source
URLs checked no more than seven days before creation, attempts, and every
execution and spend ceiling into a non-secret tracked manifest:

```bash
.venv/bin/gradia-universe frontier-preregister \
  --run-id '<immutable-cell-id>' \
  --created-at '<RFC3339-UTC>' \
  --provider '<openai|anthropic|xai|gemini>' \
  --model '<exact-model-id>' \
  --max-model-turns 32 \
  --max-acts 28 \
  --max-provider-requests '<approved-request-cap>' \
  --max-output-tokens '<per-request-cap>' \
  --max-total-output-tokens '<cell-cap>' \
  --max-cost-usd '<approved-cap>' \
  --input-usd-per-million '<current-price>' \
  --output-usd-per-million '<current-price>' \
  --price-source-url '<official-provider-pricing-url>' \
  --price-checked-at '<RFC3339-UTC>' \
  --retention-terms-url '<official-provider-data-terms-url>' \
  --retention-checked-at '<RFC3339-UTC>' \
  --derived-publication-posture '<operator-assessed: unknown|not_permitted|derived_only_permitted>' \
  --reasoning-effort high \
  --confirm-private-response-retention \
  --confirm-provider-account-spend-limit
```

Inspect `preregistrations/<immutable-cell-id>.json`, commit and push that file
alone, and wait for green CI. The live command refuses an uncommitted manifest,
a dirty tree, a changed task/judge/adapter, or a commit containing anything
besides that one manifest:

```bash
.venv/bin/gradia-universe frontier-live-panel \
  --preregistration preregistrations/<immutable-cell-id>.json \
  --confirm-live-spend
```

That Git check proves only that the manifest commit follows the recorded code
commit and contains only the expected manifest path. It cannot prove that no
earlier private execution or outcome inspection occurred; the operator must
attest to that procedural fact. Official-source URLs reject credentials,
queries, fragments and nonstandard ports so a public manifest cannot smuggle a
secret through evidence metadata.

Selective scenario flags are not accepted: the manifest always binds all five
v1 tasks before any paid task outcome may be inspected. The preregistration
requires explicit `high` reasoning and provider-default temperature; either
deviation is refused. Every full frontier cell reports per-task successes/5, any-pass@5,
all-pass@5, descriptive uncertainty and failure-signature counts.

The output is written only to `results/local/<run-id>/`, which is ignored by
Git. A run id is immutable and cannot be reused. The edition contains:

- a panel receipt with the exact requested and returned model identities,
  adapter, scaffold, seeds or attempt ids, and spend
  policy;
- one evidence-bearing episode receipt per scenario/seed;
- provider response ids, token usage, output text and response-byte digests;
  and
- exact provider response bytes in a local permissions-restricted directory.

## Interpretation boundary

Provider failures and budget stops never masquerade as model failures.
Environment failures are excluded. A budget stop is reported separately as an
incomplete cell. A model that uses every allowed turn without a valid terminal
submission remains an eligible model failure.

`0/5` is “stable failure observed under this exact cell,” `1–4/5` is
“inconsistency observed,” and `5/5` is “stable pass observed.” These labels do
not by themselves locate the cause in model capability, scaffold, task design
or sampling policy. Strong failure claims require the committed judge probes,
whose current-source criterion binds citations to actual root-owned source-read
results and whose adaptation criterion binds post-event reads to each changed
resource, plus blinded human review and appeal/adjudication evidence. The 44
isolated probes have canonical report digest
`fdeea4ae15c00a0f225f48a4bde7c42e261be648dd7d7cea2ec100c64935653e`.

No result should move from `results/local` into a public release until all of
the following are true:

1. the requested and returned model ids match, and pricing inputs were checked
   against the provider record;
2. the panel, seed set, exclusions and analysis were frozen before outcomes
   were inspected;
3. provider terms permit the intended retention and publication;
4. the exact receipts pass replay/integrity checks;
5. two blinded human reviews exist, including one independent reviewer;
6. Gradia's synthetic project records the author/reviewer/service-account
   separation and the relevant evidence digests; and
7. a disclosure projection removes anything outside the approved public
   evidence contract without changing a reported number.

Until then, the deterministic reference panel is the only committed result.
