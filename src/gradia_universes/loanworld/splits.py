"""Parent splits: public dev parents and a commit-then-reveal held-out split.

Seeds follow the HardLoan spec (section 5):
``file_seed = sha256(f"{master}|{split}|{index}|{generator_version}")[:16]``
(``draws.derive_seed``).

* **dev** uses a public master string. Its parents are committed in full under
  ``fixtures/loanworld/parents/``; anyone can regenerate them.
* **heldout** uses a secret master generated once and kept outside the repository.
  Only a commitment is published (``fixtures/loanworld/heldout/commitment.json``):
  ``sha256(master)``, and per parent ``sha256(file_seed)`` and the digest of its truth
  bundle (scenario and counterpart contract; forks are derived from them by public code,
  so the commitment survives catalog growth). At the next release the
  master is published; ``verify_reveal`` then regenerates every held-out parent and
  checks it against the old commitment, which proves the split was not changed after
  results were seen.

The commitment also records whether each held-out parent passed the solvability and
isolation gates (booleans only), so a broken held-out episode is caught before use
without disclosing anything about its content.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..canonical import digest, load_json
from . import GENERATOR_VERSION_V2
from .counterparts import build_counterparts
from .draws import derive_seed
from .forks import CATALOG, CATALOG_VERSION, build_fork_manifest
from .generator import build_parent
from .oracle import ORACLE_VERSION

DEV_MASTER = "gradia-loanworld-dev-master-v2"
DEV_INDEXES = (2, 3, 4)  # dev-001 is the frozen generator-0.1.0 parent
HELDOUT_COUNT = 3
COMMITMENT_SCHEMA = "gradia.loanworld.heldout-commitment.v1"
COMMITMENT_PATH = Path("fixtures") / "loanworld" / "heldout" / "commitment.json"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def dev_parent(index: int) -> dict[str, Any]:
    seed = derive_seed(DEV_MASTER, "dev", index, GENERATOR_VERSION_V2)
    return build_parent(seed, f"loanworld-parent-dev-{index:03d}")


def heldout_bundle(master: str, index: int) -> tuple[str, dict[str, Any]]:
    """(file seed, truth bundle) for one held-out parent. Never written to the repo."""
    seed = derive_seed(master, "heldout", index, GENERATOR_VERSION_V2)
    scenario = build_parent(seed, f"loanworld-parent-heldout-{index:03d}")
    return seed, {"scenario": scenario, "counterparts": build_counterparts(scenario)}


def heldout_forks(bundle: dict[str, Any]) -> dict[str, Any]:
    return build_fork_manifest(bundle["scenario"], bundle["counterparts"])


def build_commitment(master: str, gate_results: dict[int, dict[str, bool]]) -> dict[str, Any]:
    if len(master) < 32:
        raise ValueError("heldout_master_too_short")
    parents = []
    for index in range(1, HELDOUT_COUNT + 1):
        seed, bundle = heldout_bundle(master, index)
        parents.append(
            {
                "index": index,
                "scenario_id": bundle["scenario"]["scenario_id"],
                "seed_sha256": sha256_text(seed),
                "truth_bundle_sha256": digest(bundle),
                "gates": gate_results[index],
            }
        )
    body = {
        "schema": COMMITMENT_SCHEMA,
        "split": "heldout",
        "generator_version": GENERATOR_VERSION_V2,
        "seed_derivation": "sha256(f'{master}|heldout|{index}|{generator_version}')[:16]",
        "master_sha256": sha256_text(master),
        "gates_context": {
            "oracle_version": ORACLE_VERSION,
            "fork_catalog_version": CATALOG_VERSION,
            "forks_per_parent": len(CATALOG),
        },
        "truth_bundle": "digest of {scenario, counterparts} (canonical JSON)",
        "parents": parents,
        "reveal_policy": (
            "The master is published at the next LoanWorld release; verify_reveal then "
            "regenerates every parent and checks it against this commitment."
        ),
    }
    return {**body, "commitment_sha256": digest(body)}


def verify_commitment_shape(path: Path) -> dict[str, Any]:
    committed = load_json(path)
    body = {k: v for k, v in committed.items() if k != "commitment_sha256"}
    if committed.get("schema") != COMMITMENT_SCHEMA:
        raise ValueError("heldout_commitment_schema_unsupported")
    if digest(body) != committed["commitment_sha256"]:
        raise ValueError("heldout_commitment_digest_mismatch")
    if not all(p["gates"]["solvable"] and p["gates"]["isolated"] for p in committed["parents"]):
        raise ValueError("heldout_parent_failed_gates")
    return committed


def verify_reveal(path: Path, master: str) -> dict[str, Any]:
    """After the master is revealed: regenerate the split and check every hash."""
    committed = verify_commitment_shape(path)
    if sha256_text(master) != committed["master_sha256"]:
        raise ValueError("heldout_master_does_not_match_commitment")
    for row in committed["parents"]:
        seed, bundle = heldout_bundle(master, row["index"])
        if sha256_text(seed) != row["seed_sha256"]:
            raise ValueError(f"heldout_seed_mismatch:{row['index']}")
        if digest(bundle) != row["truth_bundle_sha256"]:
            raise ValueError(f"heldout_truth_bundle_mismatch:{row['index']}")
    return committed
