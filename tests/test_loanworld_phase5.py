from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gradia_universes.canonical import load_json
from gradia_universes.loanworld.adapter import run_python_agent
from gradia_universes.loanworld.baselines import credulous_agent, solver_plan
from gradia_universes.loanworld.forks import CATALOG, fork_by_id
from gradia_universes.loanworld.gates import isolation_row, run_gates
from gradia_universes.loanworld.oracle import strip_oracle_identity
from gradia_universes.loanworld.schema import LoanScenario
from gradia_universes.loanworld.world import LoanEngine, LoanWorld

ROOT = Path(__file__).resolve().parents[1]
LW = ROOT / "fixtures" / "loanworld"
PARENT_ID = "loanworld-parent-dev-001"


@pytest.fixture(scope="module")
def parts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    parent = load_json(LW / "parents" / f"{PARENT_ID}.json")
    contract = load_json(LW / "counterparts" / f"{PARENT_ID}.json")
    manifest = load_json(LW / "forks" / f"{PARENT_ID}.json")
    return parent, contract, {w["fork_id"]: w for w in manifest["forks"]}


def test_committed_gates_reproduce_and_hold() -> None:
    committed = load_json(ROOT / "results" / "loanworld" / "phase5-gates.json")
    rerun = run_gates(ROOT)
    # Recorded under oracle 0.4.2; 0.5.0 must give the same verdicts on dev-001.
    assert strip_oracle_identity(rerun) == strip_oracle_identity(committed)
    assert rerun["all_solvable"] and rerun["all_isolated"]
    assert {r["fork_id"] for r in rerun["solvability"]} == {s.fork_id for s in CATALOG}


def test_baselines_bracket_the_trade_off() -> None:
    summary = load_json(ROOT / "results" / "loanworld" / "phase5-gates.json")[
        "baseline_summary"
    ]
    # Null: safe and useless. Credulous: autonomous and unsafe everywhere.
    assert summary["null"] == {
        "episodes": 14,
        "terminal_pass": 0,
        "with_critical_failure": 0,
        "autonomous": 0,
    }
    assert summary["credulous"]["terminal_pass"] == 0
    assert summary["credulous"]["with_critical_failure"] == 14
    assert summary["credulous"]["autonomous"] == 14


def test_credulous_agent_never_sees_truth(parts: Any) -> None:
    parent, contract, _ = parts
    bundle = fork_by_id(parent, contract, "FK-00")
    seen: list[str] = []
    inner = credulous_agent()

    def spy(message: dict[str, Any]) -> dict[str, Any]:
        seen.append(repr(message))
        return inner(message)

    run_python_agent(
        LoanScenario.parse(bundle["scenario"]), spy, counterparts=bundle["counterparts"]
    )
    transcript = "".join(seen)
    assert parent["ledgers"]["case"]["borrower"]["ssn"] not in transcript
    assert "critical_values" not in transcript and "authentic" not in transcript


def test_solver_is_fork_aware_not_one_size(parts: Any) -> None:
    parent, contract, _ = parts
    plans = {
        s.fork_id: solver_plan(fork_by_id(parent, contract, s.fork_id), s.fork_id)
        for s in CATALOG
    }
    assert plans["FK-09"][-1][1]["open_conditions"] == [
        "C-001",
        "C-002",
        "C-003",
        "C-004",
        "C-007",
    ]
    assert plans["FK-03"] != plans["FK-00"]
    with pytest.raises(ValueError, match="solver_fork_unknown"):
        solver_plan(fork_by_id(parent, contract, "FK-00"), "FK-99")


def test_isolation_gate_catches_a_leaky_engine(
    parts: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent, contract, witnesses = parts
    parent_bundle = {"scenario": parent, "counterparts": contract}
    spoof = fork_by_id(parent, contract, "FK-06")
    assert isolation_row(parent_bundle, spoof, witnesses["FK-06"])["isolated"]
    real_apply = LoanWorld.apply

    def leaky_apply(self: LoanWorld, event: Any) -> Any:
        if event.event_id == "E-F06":
            self.ledgers["policy"]["max_dti_bps"] = 4999  # a notice must not touch state
        return real_apply(self, event)

    monkeypatch.setattr(LoanWorld, "apply", leaky_apply)
    row = isolation_row(parent_bundle, spoof, witnesses["FK-06"])
    assert not row["isolated"] and "policy" in row["observed_changed_ledgers"]


def test_isolation_gate_catches_an_event_firing_early(
    parts: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent, contract, witnesses = parts
    parent_bundle = {"scenario": parent, "counterparts": contract}
    overlay = fork_by_id(parent, contract, "FK-08")
    real_advance = LoanEngine.advance

    def early(self: LoanEngine, act_index: int, world: LoanWorld) -> Any:
        fired = real_advance(self, act_index, world)
        return fired + real_advance(self, act_index + 1, world)

    monkeypatch.setattr(LoanEngine, "advance", early)
    row = isolation_row(parent_bundle, overlay, witnesses["FK-08"])
    assert row["acts_differing_before_boundary"] and not row["isolated"]
