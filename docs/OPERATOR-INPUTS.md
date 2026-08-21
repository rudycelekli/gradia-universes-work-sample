# Operator inputs for the first live agent panel

The keyless engineering gates are complete without provider credentials. A
live-model cell needs the following founder-owned inputs and nothing else.

## 1. Put provider keys on this machine, never in chat

```bash
cp .env.example .env.local
chmod 600 .env.local
```

Open `.env.local` locally and fill only the providers you intend to run:

```dotenv
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
XAI_API_KEY=
GEMINI_API_KEY=
```

Do **not** paste keys into Codex, an issue, a command argument, a result file,
the Gradia application environment or the public repository. Use project-
scoped keys with the lowest useful provider quota and no account-management
permission. The runner reads one environment variable for the selected cell,
does not print it and keeps provider response bytes in a mode-`0700` ignored
directory.

Load the file only into the terminal that will run the cell:

```bash
set -a
source .env.local
set +a
```

When the run is over, close that shell or unset the four variables. Key
rotation, provider retention settings and account-level spend alerts remain
owner responsibilities.

## 2. Send these non-secret choices in chat

For each provider you want included, provide:

- the exact model identifier available to your project now;
- the provider's current input price per million tokens;
- the provider's current output price per million tokens; and
- whether provider terms permit retaining response bytes for private research
  and later publishing a reviewed derived result.

Avoid aliases such as `latest`. A model family name is not an exact pin.
The runner separately records the model identity returned by the provider and
refuses and latches a paid cell when that identity is missing or differs from
the requested id. The retained provider bytes are review evidence; the cell is
not eligible for a reported model score.

Also approve one total dollar ceiling. Recommended first pass:

1. run the non-benchmark `provider-smoke`, one request and one model per provider under a
   **$5 local reservation ceiling**, with a separate provider-account spend
   limit, to verify protocol and usage fields;
2. freeze all five v1 tasks, their judge, analysis, exact model, high reasoning,
   provider-default temperature, rights posture and full-panel cap in one
   manifest before inspecting any paid task outcome;
3. commit and push that manifest alone and wait for green CI;
4. run all 25 task attempts (five tasks × five attempts) from that manifest;
5. inspect receipts, outcome signatures and grader evidence only after the
   entire cell ends; and
6. keep the panel private until blinded review and release governance pass.

The command refuses a request that could cross its cell cap. Provider account-
level budgets remain a second independent control.

Before the first task-bearing request, the non-secret cell manifest is generated from a clean tree,
reviewed, committed and pushed by itself. The live runner refuses if that
public preregistration is missing, uncommitted, no longer the only change after
the recorded code commit, or inconsistent with the current tasks, judge,
analysis, adapter, prices or caps.
This Git check proves commit ordering and manifest-only changed-file scope. It
does not prove that no earlier private run or outcome inspection occurred;
following and attesting to that operating rule remains the operator's duty.

The v1 comparison fixes explicit `high` reasoning and provider-default
temperature for every model. The runner records both. Attempt ids 1–5 are
repeated requests, not random seeds. Results distinguish any-pass@5 capability
coverage from all-pass@5 reliability and preserve individual failure
signatures.

## 3. Inputs needed later, not for the first model smoke

The authenticated Gradia study requires a dedicated synthetic project, an
author identity, a different reviewer identity and a project-scoped service
account. AgentENV parity additionally requires an owned AgentENV cell with its
authenticated file/credential capability enabled. Human validation requires
two reviewers, including one independent of environment authorship.

Before a public model-failure claim, each reviewer receives the blinded task
evidence, criterion definitions and an appeal form. Disagreements, reasons and
adjudication remain versioned evidence. A disagreement is never silently
converted to the deterministic judge's answer.

None of those may be substituted with a model-provider key, and no organization
fact is required for this fully synthetic study.

## 4. Release boundary

A successful provider call is not a public result. Raw responses and local
receipts stay private until exact model/scaffold/seed/budget identities,
provider rights, integrity replay, blinded review and Gradia's governed release
decision all pass. The public Universe bundle remains unchanged until then.
