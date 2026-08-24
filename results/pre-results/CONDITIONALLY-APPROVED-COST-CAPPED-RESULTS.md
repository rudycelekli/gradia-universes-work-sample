# Conditionally Approved cost-capped panel

**Status:** machine-derived PRE-RESULTS, 24 August 2026  
**Panel:** concatenate `frontier-v4-five-task` and
`-pass5-pre-results-20260823-04` (the split avoids a secret-shaped scanner
collision without changing the registered identity).

## Claim boundary

This is an exact execution inventory from a prospectively cost-capped panel. It
does not establish broad capability, frontier difficulty, provider superiority,
tail reliability, mortgage-domain validity, causal effects, training utility or
novelty. Deterministic red criteria remain behaviorally unattributed until
blinded human adjudication distinguishes model failures from measurement
defects.

## Complete-case result

Six provider-by-task cells contain exactly two selected, gradable attempts under
one task, evaluator, Git commit and runtime implementation. All 12 selected
attempts received the machine-scored perfect-rubric outcome zero. Therefore all
six exact cells have `pass@2 = false` and `pass^2 = false`.

| Provider/model | Task | Outcomes | pass@2 | pass^2 |
|---|---|---|---|---|
| `anthropic/claude-opus-5` | Document truth | `[0, 0]` | false | false |
| `gemini/gemini-3.1-pro-preview` | Document truth | `[0, 0]` | false | false |
| `openai/gpt-5.6-sol` | Document truth | `[0, 0]` | false | false |
| `xai/grok-4.6` | Document truth | `[0, 0]` | false | false |
| `gemini/gemini-3.1-pro-preview` | Epistemic residue | `[0, 0]` | false | false |
| `openai/gpt-5.6-sol` | Epistemic residue | `[0, 0]` | false | false |

Document Truth Under Pushback is the cleanest cross-provider slice: all four
providers completed two selected attempts on the same task and runtime, and none
of the eight attempts passed. This is a complete same-runtime result for one
synthetic task, not a provider ranking or a claim about the four missing task
slices.

## Trajectory shape inside the complete cells

| Provider/model | Task | Calls | Tool actions | Turns | Input tokens | Output tokens | Spend |
|---|---|---:|---:|---:|---:|---:|---:|
| `anthropic/claude-opus-5` | Document truth | 152 | 150 | 308 | 3,849,883 | 297,486 | $26.69 |
| `gemini/gemini-3.1-pro-preview` | Document truth | 5 | 4 | 8 | 34,110 | 3,337 | $0.20 |
| `openai/gpt-5.6-sol` | Document truth | 201 | 200 | 409 | 4,591,400 | 64,078 | $38.65 |
| `xai/grok-4.6` | Document truth | 147 | 145 | 295 | 5,003,222 | 634,642 | $27.63 |
| `gemini/gemini-3.1-pro-preview` | Epistemic residue | 6 | 4 | 8 | 40,228 | 5,277 | $0.26 |
| `openai/gpt-5.6-sol` | Epistemic residue | 305 | 303 | 618 | 8,328,831 | 103,381 | $69.73 |

The exact zero outcome hides radically different paths. This observation supports
process-level review; it does not establish that longer or shorter execution is
better, or identify a behavioral mechanism before adjudication.

## Full execution inventory

- 55 physical attempts reached the hard execution ceiling.
- 37 attempts produced complete, gradable terminal artifacts.
- 18 attempts were infrastructure exclusions and remain outside behavioral
  denominators.
- 0/37 gradable attempts satisfied the exact perfect-rubric conjunction.
- Nine cells contained one gradable attempt; five cells were unobserved.
- The execution crossed three runtime cohorts, so a balanced pooled result was
  refused.
- Recorded execution totaled 3,617 provider calls, 99,382,990 input tokens,
  6,080,548 output tokens, 2,609 tool actions, 5,325 transcript turns and
  $705.88 in provider spend.

| Provider/model | Physical | Gradable | Infrastructure | Perfect passes | Spend |
|---|---:|---:|---:|---:|---:|
| `anthropic/claude-opus-5` | 14 | 8 | 6 | 0 | $281.50 |
| `gemini/gemini-3.1-pro-preview` | 13 | 13 | 0 | 0 | $2.99 |
| `openai/gpt-5.6-sol` | 18 | 10 | 8 | 0 | $308.62 |
| `xai/grok-4.6` | 10 | 6 | 4 | 0 | $112.77 |
| **Total** | **55** | **37** | **18** | **0** | **$705.88** |

These provider rows are inventory, not a ranking. Providers encountered
different task mixes and failure surfaces.

## Infrastructure exclusions

The 18 excluded attempts comprised seven first-dispatch OpenAI HTTP 401
authentication refusals, two Anthropic HTTP 529 overload failures after bounded
retries, six read timeouts, one OpenAI read error, and two xAI responses that
completed transport without an admitted text payload. Excluded attempts
accounted for $173.35 of physical spend. Their partial traces remain immutable;
they are neither passes nor model failures.

## Evidence identities

| Object | Digest |
|---|---|
| Original plan | `3818860f9719a7b0f8258535546f481ededb2b72e16f6998a5c1e79989c51849` |
| Cost-cap amendment | `5f5bf7aa8c74cc0307bc86a90f8dadb26c120a74636d1c3db509b22e744953ba` |
| Cost-capped index | `e3dec5dc9ddf8718dcaa786b4e999d77c34f6752bc31694edbda99752c781003` |
| Verification report | `b8e013fc05b5f9868a892f89a2a0986d67978c68153b47d9b1756fbbec3b5777` |
| Evaluator contract | `668383df2589330fac87fc2e2f8e8e786c5896fb5f8b4b2b74c5639fb2ccbb88` |

Raw provider responses and full trajectories remain private pending
per-artifact rights, redaction, human adjudication and release review. A public
reader therefore cannot yet recompute this aggregate from raw bytes; that
reconstruction gap is explicit.

## Frozen human-review input

The unsigned blinded packet is now generated from all 37 gradable attempts. It
contains 889 red-criterion assignments per reviewer and zero human decisions.
The generator blinds provider, model and cost identity; binds the presented
evidence and source artifact digests; and requires relationship/compensation
disclosures before submission.

- Packet digest: `0d0fa2c7b02d554a9e906dac9fca4ddbfd33324c6d28703ea70937e8c8b2b18c`
- Manifest digest: `42e826e969093c2ce74be292c37575035fc4f8c2314b10a39078d824b301a6a9`
- Packet file SHA-256: `b5ee55acb8493393dbf8a0c2caa06994e748ffceb004c406bc03ad416706dbe4`

The only absent evidence in that packet is the human judgment itself. Two
independent reviewers must disposition every assignment, disagreements must be
resolved by a separately identified adjudicator, and agreement statistics must
be recomputed from the sealed decisions.

## Next gates

1. Two independent, identity-blinded reviewers disposition every red criterion.
2. A separate adjudicator resolves qualified disagreement.
3. Verified measurement defects create new task/evaluator editions; historical
   outcomes remain unchanged.
4. Provider preflight and one frozen runtime precede separately identified
   replacement attempts for excluded and unobserved cells.
5. Only a complete admitted panel may support stronger empirical claims.
