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

Model identifiers are never supplied by this repository. Choose and record an
exact currently available model id immediately before preregistration. Avoid
aliases such as `latest` when the provider offers a versioned id.

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
It refuses before the request if that reservation could exceed the cost cap.

Example shape—not a price recommendation or runnable model choice:

```bash
.venv/bin/gradia-universe live-panel \
  --run-id preregistered-cell-001 \
  --provider openai \
  --model '<exact-model-id>' \
  --seeds 11 29 47 \
  --max-model-turns 12 \
  --max-acts 10 \
  --max-provider-requests 180 \
  --max-output-tokens 512 \
  --max-total-output-tokens 92160 \
  --max-cost-usd '<approved-cap>' \
  --input-usd-per-million '<current-price>' \
  --output-usd-per-million '<current-price>' \
  --confirm-live-spend
```

The longer frontier-candidate suite uses a different command. It always runs
attempt ids 1 through 5 for each selected task; those ids label independent
requests and are not presented as provider random seeds:

```bash
.venv/bin/gradia-universe frontier-live-panel \
  --run-id '<immutable-cell-id>' \
  --provider '<openai|anthropic|xai|gemini>' \
  --model '<exact-model-id>' \
  --scenario frontier-chained-cutoff \
  --max-model-turns 32 \
  --max-acts 28 \
  --max-provider-requests '<approved-request-cap>' \
  --max-output-tokens '<per-request-cap>' \
  --max-total-output-tokens '<cell-cap>' \
  --max-cost-usd '<approved-cap>' \
  --input-usd-per-million '<current-price>' \
  --output-usd-per-million '<current-price>' \
  --temperature '<frozen-value-if-supported>' \
  --confirm-live-spend
```

Omit `--temperature` only when the preregistration explicitly chooses the
provider default. The panel records that omission rather than inventing a
value. Every full frontier cell reports per-task successes/5, any-pass@5,
all-pass@5, descriptive uncertainty and failure-signature counts.

The output is written only to `results/local/<run-id>/`, which is ignored by
Git. A run id is immutable and cannot be reused. The edition contains:

- a panel receipt with the exact model, adapter, scaffold, seeds and spend
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
blinded human review and appeal/adjudication evidence.

No result should move from `results/local` into a public release until all of
the following are true:

1. the model id and pricing inputs were checked against the provider record;
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
