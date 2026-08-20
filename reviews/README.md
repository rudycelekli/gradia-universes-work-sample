# Human calibration protocol

Judge-human agreement is intentionally absent from the reference release until
real human reviews exist. To run the frozen protocol:

```bash
gradia-universe human-packet --output results/local/reviewer-a
```

Give `human-review-packet.json` and a separate copy of the CSV template to each
reviewer. Reviewers must not inspect `results/reference` or one another's file.
Each criterion is `yes`, `no` or `cannot_assess`; every row requires a reason.
Use stable pseudonymous reviewer IDs, not names or emails.

After two distinct reviewers freeze their files:

```bash
gradia-universe human-agreement \
  --reviews reviewer-a.csv reviewer-b.csv \
  --output results/local/agreement.json
```

The receipt reports per-criterion raw agreement, Cohen's kappa where estimable,
cannot-assess counts and item IDs needing adjudication. A disagreement is never
silently majority-voted away.

At least one reviewer must be independent of environment authorship before any
public judge-validity claim. The current deterministic oracle is an executable
fixture specification, not a substitute for that study.

