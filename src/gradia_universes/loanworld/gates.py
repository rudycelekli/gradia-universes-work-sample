"""Phase-5 release gates for LoanWorld v0: solvability, branch isolation, baselines.

* **Solvability.** For every fork, the truth-reading solver (a positive control)
  must reach ``terminal_pass`` with zero critical failures. An episode no policy
  can pass is a broken episode, not a hard one.
* **Branch isolation.** A neutral plan (read conditions, escalate, submit) runs
  on the parent and on each fork. The final ledgers may differ only in the
  ledgers that the intervention changes in root truth (replaying all scheduled
  events). For event forks, every response before the event's boundary must be
  identical, so nothing leaks before the boundary.
* **Baselines.** The null policy and the credulous policy run on every fork and
  are graded by the oracle. These are $0 scripted baselines, not model results.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..canonical import digest, load_json
from . import oracle as oracle_module
from .adapter import run_python_agent
from .baselines import credulous_agent, solver_plan
from .forks import CATALOG, fork_by_id
from .oracle import Truth, grade_episode
from .policies import null_agent, plan_agent
from .schema import LEDGERS, LoanScenario

GATES_SCHEMA = "gradia.loanworld.phase5-gates.v0"
NEUTRAL_ACTS = 8


def _load(root: Path, parent_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    lw = root / "fixtures" / "loanworld"
    parent = load_json(lw / "parents" / f"{parent_id}.json")
    contract = load_json(lw / "counterparts" / f"{parent_id}.json")
    manifest = load_json(lw / "forks" / f"{parent_id}.json")
    return parent, contract, {w["fork_id"]: w for w in manifest["forks"]}


def _episode(bundle: dict[str, Any], agent: Any) -> dict[str, Any]:
    return run_python_agent(
        LoanScenario.parse(deepcopy(bundle["scenario"])),
        agent,
        counterparts=bundle["counterparts"],
    )


def _summary(grade: dict[str, Any]) -> dict[str, Any]:
    return {
        "terminal_pass": grade["terminal_pass"],
        "autonomous": grade["autonomous"],
        "recommendation": grade["recommendation"],
        "critical_codes": sorted({f["code"] for f in grade["critical_failures"]}),
        "failed_criteria": sorted(k for k, v in grade["criteria"].items() if not v),
        "grade_sha256": grade["grade_sha256"],
    }


def _neutral_plan() -> list[tuple[str, dict[str, Any]]]:
    plan: list[tuple[str, dict[str, Any]]] = [("get_conditions", {})] * NEUTRAL_ACTS
    plan.append(("escalate", {"reason": "Neutral isolation probe."}))
    plan.append(
        ("submit", {"recommendation": "ESCALATE", "open_conditions": [], "account": []})
    )
    return plan


def _comparable(result: dict[str, Any], ledger: str) -> Any:
    """A ledger as compared for isolation. The terminal records the world root it
    observed, which differs whenever any ledger differs; that one derived field is
    set aside so it cannot mask or fake a difference."""
    value = deepcopy(result["final_state"]["world"]["ledgers"][ledger])
    if ledger == "agent_record" and value.get("terminal"):
        value["terminal"].pop("observed_world_root", None)
    return value


def expected_changed_ledgers(parent: dict[str, Any], fork: dict[str, Any]) -> list[str]:
    """Ledgers that differ in root truth once every scheduled event has fired."""
    final = 10**6
    a = Truth({"scenario": parent}, None).ledgers_at(final)
    b = Truth({"scenario": fork}, None).ledgers_at(final)
    return sorted(name for name in a if digest(a[name]) != digest(b[name]))


def isolation_row(
    parent_bundle: dict[str, Any], fork_bundle: dict[str, Any], witness: dict[str, Any]
) -> dict[str, Any]:
    base = _episode(parent_bundle, plan_agent(_neutral_plan()))
    fork = _episode(fork_bundle, plan_agent(_neutral_plan()))
    observed = sorted(
        n for n in LEDGERS if digest(_comparable(base, n)) != digest(_comparable(fork, n))
    )
    expected = expected_changed_ledgers(parent_bundle["scenario"], fork_bundle["scenario"])
    boundary = None
    if witness["declared_paths"] and witness["declared_paths"][0].startswith(
        "/scenario/events"
    ):
        events = fork_bundle["scenario"]["events"]
        index = int(witness["declared_paths"][0].split("/")[3])
        boundary = min(
            events[index]["after_act"],
            parent_bundle["scenario"]["events"][index]["after_act"]
            if index < len(parent_bundle["scenario"]["events"])
            else 10**6,
        )
    leaked_before_boundary: list[int] = []
    if boundary is not None:
        base_responses = {
            r["act"]: r["response_sha256"] for r in base["final_state"]["receipts"]
        }
        for receipt in fork["final_state"]["receipts"]:
            act = receipt["act"]
            if act < boundary and base_responses.get(act) != receipt["response_sha256"]:
                leaked_before_boundary.append(act)
    return {
        "fork_id": witness["fork_id"],
        "expected_changed_ledgers": expected,
        "observed_changed_ledgers": observed,
        "boundary_act": boundary,
        "acts_differing_before_boundary": leaked_before_boundary,
        "isolated": observed == expected and not leaked_before_boundary,
    }


def run_gates(root: Path, parent_id: str = "loanworld-parent-dev-001") -> dict[str, Any]:
    parent, contract, witnesses = _load(root, parent_id)
    return gates_for(parent, contract, witnesses, parent_id)


def gates_for(
    parent: dict[str, Any],
    contract: dict[str, Any],
    witnesses: dict[str, dict[str, Any]],
    parent_id: str,
) -> dict[str, Any]:
    parent_bundle = {"scenario": parent, "counterparts": contract}
    solvability, isolation, baselines = [], [], []
    for spec in CATALOG:
        bundle = fork_by_id(parent, contract, spec.fork_id)
        labels = witnesses[spec.fork_id]["expected_draft"]
        solved = grade_episode(
            bundle,
            labels,
            _episode(bundle, plan_agent(solver_plan(bundle, spec.fork_id))),
            spec.fork_id,
        )
        solvability.append(
            {
                "fork_id": spec.fork_id,
                **_summary(solved),
                "solvable": solved["terminal_pass"] and not solved["critical_failures"],
            }
        )
        isolation.append(isolation_row(parent_bundle, bundle, witnesses[spec.fork_id]))
        for name, agent in (("null", null_agent), ("credulous", credulous_agent())):
            grade = grade_episode(bundle, labels, _episode(bundle, agent), spec.fork_id)
            baselines.append({"policy": name, "fork_id": spec.fork_id, **_summary(grade)})

    def tally(policy: str) -> dict[str, Any]:
        rows = [r for r in baselines if r["policy"] == policy]
        return {
            "episodes": len(rows),
            "terminal_pass": sum(r["terminal_pass"] for r in rows),
            "with_critical_failure": sum(bool(r["critical_codes"]) for r in rows),
            "autonomous": sum(r["autonomous"] for r in rows),
        }

    body = {
        "schema": GATES_SCHEMA,
        "parent_id": parent_id,
        "oracle_version": oracle_module.ORACLE_VERSION,
        "oracle_source_sha256": digest(__import__("inspect").getsource(oracle_module)),
        "solvability": solvability,
        "all_solvable": all(r["solvable"] for r in solvability),
        "isolation": isolation,
        "all_isolated": all(r["isolated"] for r in isolation),
        "baselines": baselines,
        "baseline_summary": {"null": tally("null"), "credulous": tally("credulous")},
        "interpretation": (
            "Scripted $0 controls and baselines on one synthetic parent and its forks, "
            "clustered by parent. No model has run; nothing here ranks agents."
        ),
    }
    return {**body, "gates_sha256": digest(body)}


PHASE7_SCHEMA = "gradia.loanworld.phase7-gates.v0"


def run_phase7_gates(root: Path) -> dict[str, Any]:
    """Phase-5 gates re-run on every committed dev parent (phase 7)."""
    parents = sorted(
        p.stem for p in (root / "fixtures" / "loanworld" / "parents").glob("*.json")
    )
    reports = [run_gates(root, parent_id) for parent_id in parents]
    rows = [
        {
            "parent_id": r["parent_id"],
            "all_solvable": r["all_solvable"],
            "all_isolated": r["all_isolated"],
            "solvable": sum(row["solvable"] for row in r["solvability"]),
            "isolated": sum(row["isolated"] for row in r["isolation"]),
            "forks": len(r["solvability"]),
            "baseline_summary": r["baseline_summary"],
            "gates_sha256": r["gates_sha256"],
        }
        for r in reports
    ]
    body = {
        "schema": PHASE7_SCHEMA,
        "oracle_version": oracle_module.ORACLE_VERSION,
        "oracle_source_sha256": digest(__import__("inspect").getsource(oracle_module)),
        "parents": rows,
        "all_solvable": all(r["all_solvable"] for r in reports),
        "all_isolated": all(r["all_isolated"] for r in reports),
        "detail": reports,
        "interpretation": (
            "Scripted $0 controls and baselines on the public dev parents, clustered by "
            "parent. No model has run in phase 7; nothing here ranks agents."
        ),
    }
    return {**body, "gates_sha256": digest(body)}
