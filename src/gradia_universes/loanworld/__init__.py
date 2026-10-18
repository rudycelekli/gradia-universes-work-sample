"""LoanWorld: a branchable, witnessed mortgage universe for end-to-end agent evaluation.

PRE-RESULTS engineering edition. Everything here is wholly synthetic. The package
extends the public universe engine with typed loan ledgers (case, documents,
conditions, clock, authority, services, LOS, policy), a seeded gold-parent
generator, a tool API whose every call is a hash-chained receipt, and a
system-mode adapter so any vendor stack can run the same episodes.

Nothing in this package makes a difficulty, validity, ranking or novelty claim.
"""

from __future__ import annotations

GENERATOR_VERSION = "loanworld-gen-0.1.0"
SCENARIO_SCHEMA = "gradia-loanworld-scenario.v1"
