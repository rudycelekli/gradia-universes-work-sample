#!/usr/bin/env python3
"""Verify arithmetic and claim boundaries in the public four-judge summary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "pre-results" / "conditionally-approved-four-judge-alignment.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    n = payload["assignment_count"]
    require(
        payload["schema_version"]
        == "conditionally-approved-four-judge-alignment-public-summary.v1",
        "schema drift",
    )
    require(payload["judge_count"] == 4, "judge-count mismatch")
    require(sum(payload["consensus"].values()) == n, "consensus partition mismatch")
    require(
        sum(payload["consensus_disposition"].values()) == n,
        "disposition partition mismatch",
    )
    require(
        sum(payload["human_review_priority"].values()) == n,
        "priority partition mismatch",
    )
    require(len(payload["judges"]) == payload["judge_count"], "judge profile mismatch")
    for judge in payload["judges"]:
        require(
            judge["model_failure"] + judge["measurement_defect"] + judge["unresolved"] == n,
            f"vote partition mismatch:{judge['model_pin']}",
        )
    require(len(payload["pairwise"]) == 6, "four judges require six pairwise rows")
    require(payload["score_mutations"] == 0, "machine panel mutated frozen reward")
    require(payload["advisory_only"], "machine panel must remain advisory")
    require(not payload["raw_chain_of_thought_collected"], "raw chain-of-thought claim drift")
    require(not any(payload["claim_boundary"].values()), "unsupported claim enabled")

    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    print(
        "verified four-judge alignment; "
        f"assignments={n}; unanimous={payload['unanimous_assignment_count']}; "
        f"kappa={payload['descriptive_fleiss_kappa']:.6f}; "
        f"sha256={hashlib.sha256(canonical.encode()).hexdigest()}"
    )


if __name__ == "__main__":
    main()
