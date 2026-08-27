# Numerical claim trust

This repository treats the manuscript as a derived artifact, not an editorial
source of truth. A plausible-looking table is insufficient. Every empirical
result reported by *Conditionally Approved* must traverse this evidence chain:

1. a physical attempt retains its disposition, usage, exact identities, and
   evidence digests;
2. the public redacted index recomputes behavioral denominators without turning
   infrastructure exclusions into model failures;
3. receipt, panel, projection, and judge artifacts pass self-digest and
   partition checks;
4. derived prose and table fragments are regenerated from those verified
   objects; and
5. the rendered PDF must contain the same bound claims.

`make all` executes that chain and fails closed through
`scripts/verify_paper_numeric_claims.py`. The gate binds the execution partition,
provider inventory, costs and usage, exact cell coverage, selected-pair process
counts, diagnostic task and family distributions, near-universal criteria,
four-judge consensus and evidence-alignment statistics, scripted-control
receipts, and the evidence-projection ablation.

The gate intentionally does not classify bibliography years, section or equation
numbers, model/version identifiers, timestamps, hashes, or prospectively declared
design parameters as empirical outcomes. Those remain inspectable source claims.
Private-edition measurements are omitted from numerical results when the bytes
needed to reproduce them cannot ship with the artifact.

## Audit corrections

The first full manuscript-binding audit caught two real prose defects before this
edition was frozen:

- selected-pair tool use spans 4 to 303 actions, a 75.75 ratio reported as
  **75.8x**, not “two orders of magnitude”; and
- eight, not six, exact criteria were red in 34--37 of 37 gradable attempts.

It also removed exact replacement-edition control counts from both manuscripts
because those private edition bytes are outside the public and anonymous
reproduction packets. The engineering correction remains disclosed, but its
unreleased counts are not borrowed as paper evidence.

## What this proves—and what it does not

The gate proves internal consistency, source binding, denominator discipline,
and rendered-artifact fidelity. It does not make scientific interpretation
unquestionable. Reviewers should question task validity, evaluator validity,
external validity, causal identification, and novelty. The artifact makes those
questions answerable without first debating which number is real.

The next trust rung is independent reproduction from a clean checkout, followed
by blinded human attribution and a prospectively frozen replacement cohort. A
future release may remotely anchor final evidence roots, but anchoring cannot
repair a wrong evaluator or an invalid scientific claim; it can only prove which
bytes existed when.
