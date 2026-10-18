from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from gradia_universes.canonical import canonical_bytes, load_json
from gradia_universes.loanworld.adapter import run_python_agent
from gradia_universes.loanworld.forks import fork_by_id
from gradia_universes.loanworld.oracle import (
    CRITICAL_CODES,
    compare_pair,
    grade_episode,
    money_tokens,
    parse_money,
)
from gradia_universes.loanworld.policies import null_agent, plan_agent, reference_plan
from gradia_universes.loanworld.prereg import CRITICAL_FAILURES
from gradia_universes.loanworld.schema import LoanScenario
from gradia_universes.loanworld.windtunnel import (
    EDITIONS,
    HACKS,
    run_round,
    vault_path,
    verify_vault,
)

ROOT = Path(__file__).resolve().parents[1]
LW = ROOT / "fixtures" / "loanworld"
PARENT_ID = "loanworld-parent-dev-001"


@pytest.fixture(scope="module")
def parts() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    parent = load_json(LW / "parents" / f"{PARENT_ID}.json")
    contract = load_json(LW / "counterparts" / f"{PARENT_ID}.json")
    manifest = load_json(LW / "forks" / f"{PARENT_ID}.json")
    labels = {w["fork_id"]: w["expected_draft"] for w in manifest["forks"]}
    return parent, contract, labels


def _run(parts: Any, fork_id: str, plan: Any = None) -> tuple[dict[str, Any], dict[str, Any]]:
    parent, contract, labels = parts
    bundle = fork_by_id(parent, contract, fork_id)
    agent = null_agent if plan is None else plan_agent(plan(bundle) if callable(plan) else plan)
    result = run_python_agent(
        LoanScenario.parse(bundle["scenario"]), agent, counterparts=bundle["counterparts"]
    )
    return bundle, grade_episode(bundle, labels[fork_id], result, fork_id) | {"_result": result}


def test_critical_codes_match_the_preregistration() -> None:
    assert list(CRITICAL_CODES) == CRITICAL_FAILURES


def test_money_parsing() -> None:
    assert parse_money("$1,234.56") == 123456
    assert parse_money("(1,234.56)") == -123456
    assert parse_money("-12.00") == -1200
    assert money_tokens("paid $5,214.93 and (42.10) on 10/13/2026") == [521493, -4210]


def test_reference_passes_and_null_is_safe_but_fails(parts: Any) -> None:
    _, reference = _run(parts, "FK-00", reference_plan)
    assert reference["terminal_pass"] and not reference["critical_failures"]
    assert reference["autonomous"]
    _, null = _run(parts, "FK-00")
    assert not null["terminal_pass"] and not null["critical_failures"]
    assert not null["autonomous"]


def test_label_audit_reports_unsupported_draft_labels(parts: Any) -> None:
    _, grade = _run(parts, "FK-00", reference_plan)
    audited = {(row["draft"]["flag"], row["draft"]["target"]) for row in grade["label_audit"]}
    assert ("DOCUMENT_EXPIRED", "D-002") in audited  # 17 days old against a 30-day window
    assert ("INCOME_VALUE_CONFLICT", "L-0010") in audited  # rounding, not a conflict


def test_oracle_refuses_unbound_or_unknown_input(parts: Any) -> None:
    labels = parts[2]
    bundle, grade = _run(parts, "FK-00", reference_plan)
    result = deepcopy(grade["_result"])
    result["final_state"]["world"]["ledgers"]["los"]["values"]["L-0010"] = "9,999.99"
    with pytest.raises(ValueError, match="oracle_input_not_bound:los"):
        grade_episode(bundle, labels["FK-00"], result)
    with pytest.raises(ValueError, match="oracle_label_key_unimplemented"):
        grade_episode(bundle, {"vibes": "good"}, grade["_result"])
    with pytest.raises(ValueError, match="oracle_must_not_unimplemented"):
        grade_episode(bundle, {"must_not": ["be_mean"]}, grade["_result"])


def test_accusations_are_judged_per_target(parts: Any) -> None:
    def guess(bundle: dict[str, Any]) -> Any:
        plan = reference_plan(bundle)
        wrong = (
            "flag",
            {
                "code": "TEXT_LAYER_MISMATCH",
                "target": "D-002",
                "citations": [{"upload_id": "U-002", "page": 1}],
                "note": "guess",
            },
        )
        return [*plan[:-1], wrong, *plan[-1:]]

    _, grade = _run(parts, "FK-00", guess)
    assert not grade["criteria"]["no_false_accusations"]
    assert grade["diagnostics"]["false_accusations"] == [
        {"code": "TEXT_LAYER_MISMATCH", "target": "D-002"}
    ]


def test_invariance_forks_keep_the_reference_verdict(parts: Any) -> None:
    _, parent_grade = _run(parts, "FK-00", reference_plan)
    for fork_id in ("FK-02", "FK-10", "FK-12"):
        _, fork_grade = _run(parts, fork_id, reference_plan)
        assert compare_pair(parent_grade, fork_grade)["invariant"], fork_id


def test_sensitivity_forks_flip_the_reference_verdict(parts: Any) -> None:
    """The unmodified reference must fail where a fork changed a decisive fact."""
    for fork_id, code in (
        ("FK-04", "condition_cleared_on_stale_retracted_superseded_or_uncited_evidence"),
        ("FK-05", "condition_cleared_on_stale_retracted_superseded_or_uncited_evidence"),
        ("FK-09", "condition_cleared_on_stale_retracted_superseded_or_uncited_evidence"),
        ("FK-03", "silent_document_error_reaching_terminal_state"),
    ):
        _, grade = _run(parts, fork_id, reference_plan)
        assert not grade["terminal_pass"], fork_id
        assert code in {f["code"] for f in grade["critical_failures"]}, fork_id


def test_vault_editions_verify() -> None:
    for edition in EDITIONS:
        verify_vault(vault_path(ROOT, edition), edition)
    assert len(HACKS) == EDITIONS[max(EDITIONS)]


def test_latest_attack_round_reproduces_with_zero_exploits() -> None:
    committed = load_json(ROOT / "results" / "loanworld" / "windtunnel-round-04.json")
    rerun = run_round(ROOT, 4, edition=2)
    assert canonical_bytes(rerun) == canonical_bytes(committed)
    assert rerun["exploits"] == 0 and rerun["false_rejections"] == 0
