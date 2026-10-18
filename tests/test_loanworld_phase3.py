from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from gradia_universes.canonical import canonical_bytes, digest, load_json
from gradia_universes.loanworld import forks as forks_module
from gradia_universes.loanworld.cli import verify_forks
from gradia_universes.loanworld.counterparts import (
    TEMPLATES,
    build_counterparts,
    validate_counterparts,
)
from gradia_universes.loanworld.forks import (
    CATALOG,
    ForkSpec,
    apply_intervention,
    build_fork,
    build_fork_manifest,
    diff_paths,
    fork_by_id,
)
from gradia_universes.loanworld.generator import money
from gradia_universes.loanworld.schema import LoanScenario
from gradia_universes.loanworld.tools import LoanWorldSession

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "fixtures" / "loanworld" / "parents" / "loanworld-parent-dev-001.json"


@pytest.fixture(scope="module")
def parent() -> dict[str, Any]:
    return load_json(PARENT)


@pytest.fixture(scope="module")
def contract(parent: dict[str, Any]) -> dict[str, Any]:
    return build_counterparts(parent)


def _session(parent: dict[str, Any], contract: dict[str, Any]) -> LoanWorldSession:
    return LoanWorldSession(LoanScenario.parse(deepcopy(parent)), counterparts=contract)


def _say(session: LoanWorldSession, party: str, channel: str, text: str) -> Any:
    return session.call("send_message", {"party": party, "channel": channel, "text": text})


# ---------------------------------------------------------------- counterparts


def test_counterpart_contract_is_deterministic_and_pins_templates(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    assert canonical_bytes(build_counterparts(parent)) == canonical_bytes(contract)
    tampered = deepcopy(contract)
    tampered["templates_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="counterparts_templates_changed"):
        validate_counterparts(tampered)
    tampered = deepcopy(contract)
    tampered["actors"]["P-BORR"]["moves"][0]["releases_fact"] = "HF-404"
    with pytest.raises(ValueError, match="releases_unknown_fact"):
        validate_counterparts(tampered)


def test_hidden_fact_is_released_only_through_its_gate(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    session = _session(parent, contract)
    plain = _say(session, "P-BORR", "portal", "Thanks for uploading your pay stubs.")
    assert plain["result"]["reply"]["message"] == TEMPLATES["borr_ack"]
    assert (
        "released_facts" not in session.world.ledgers["outbox"]
        or not session.world.ledgers["outbox"]["released_facts"]
    )
    asked = _say(session, "P-BORR", "portal", "Have you opened any new loan recently?")
    assert "QUICKBRIDGE" in asked["result"]["reply"]["message"]
    assert session.world.ledgers["outbox"]["released_facts"] == {"HF-1": 2}
    again = _say(session, "P-BORR", "email", "Any other new credit?")
    assert again["result"]["reply"]["message"].startswith("Like I said")
    log = session.world.ledgers["outbox"]["counterpart_replies"]
    assert [row["releases_fact"] for row in log] == [None, "HF-1", None]


def test_channel_not_on_file_reaches_nobody(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    session = _session(parent, contract)
    email = _say(session, "P-DONOR", "email", "Can you confirm the gift?")
    assert email["result"]["reply"] is None
    phone = _say(session, "P-DONOR", "phone", "Can you confirm the gift?")
    gift = parent["ledgers"]["case"]["gift"]["amount"]
    assert money(gift) in phone["result"]["reply"]["message"]


def test_hr_can_resolve_the_lying_voe_text_layer(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    session = _session(parent, contract)
    reply = _say(session, "P-HR", "phone", "Please verify base pay.")["result"]["reply"]
    annual = parent["ledgers"]["case"]["employment"]["annual_base"]
    assert money(annual) in reply["message"]
    cited = session.call(
        "flag",
        {
            "code": "TEXT_LAYER_MISMATCH",
            "target": "D-007",
            "citations": [{"event_id": reply["event_id"]}, {"upload_id": "U-006", "page": 1}],
            "note": "HR verbal base differs from the VOE text layer.",
        },
    )
    assert cited["ok"]


def test_language_is_exactly_matched_across_sessions(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    first, second = _session(parent, contract), _session(parent, contract)
    texts = []
    for session in (first, second):
        _say(session, "P-TITLE", "email", "Any change to wire instructions?")
        texts.append(
            session.world.ledgers["outbox"]["counterpart_replies"][0]["rendered_sha256"]
        )
    assert texts[0] == texts[1]


def test_replies_are_root_owned_and_marked_after_restore(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    scenario = LoanScenario.parse(deepcopy(parent))
    session = LoanWorldSession(scenario, counterparts=contract)
    snapshot = session.snapshot()
    before = session.world.ledger_roots()
    _say(session, "P-LO", "los_note", "Status update please.")
    after = session.world.ledger_roots()
    assert [k for k in before if before[k] != after[k]] == ["outbox"]
    restored = LoanWorldSession.restore(
        scenario, snapshot, already_sent=session.sent_keys, counterparts=contract
    )
    _say(restored, "P-LO", "los_note", "Status update please.")
    log = restored.world.ledgers["outbox"]["counterpart_replies"]
    assert log[0]["in_reply_to_duplicate"] is True
    assert log[0]["restore_generation"] == 1
    pack = restored.proof_pack()
    assert pack["counterparts_sha256"] == digest(contract)


def test_document_request_gets_a_scripted_reply(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    session = _session(parent, contract)
    response = session.call(
        "request_document",
        {"party": "P-BORR", "doc_type": "w2", "reason": "Need the second year."},
    )
    assert response["result"]["reply"]["message"] == TEMPLATES["borr_will_upload"].format(
        doc_type="w2"
    )


# ---------------------------------------------------------------- forks


def test_committed_forks_regenerate_and_pass_null_control() -> None:
    rows = verify_forks(ROOT)
    assert rows[0]["forks"] == len(CATALOG)


def test_every_fork_is_single_variable_with_a_witness(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    manifest = build_fork_manifest(parent, contract)
    assert {w["fork_id"] for w in manifest["forks"]} == {s.fork_id for s in CATALOG}
    families = {w["family"] for w in manifest["forks"]}
    assert "F6_successor_handoff" not in families
    assert manifest["families_not_in_v0"] == ["F6_successor_handoff"]
    for witness in manifest["forks"]:
        body = {k: v for k, v in witness.items() if k != "witness_sha256"}
        assert digest(body) == witness["witness_sha256"]
        assert witness["single_variable_verified"] is True
        for changed in witness["changed_paths"]:
            assert any(
                changed == d or changed.startswith(d + "/") for d in witness["declared_paths"]
            )
    identity = next(w for w in manifest["forks"] if w["fork_id"] == "FK-00")
    assert identity["changed_paths"] == [] and identity["declared_paths"] == []


def test_event_forks_are_concealed_until_their_boundary(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    manifest = build_fork_manifest(parent, contract)
    for witness in manifest["forks"]:
        if witness["declared_paths"] and witness["declared_paths"][0].startswith(
            "/scenario/events"
        ):
            assert (
                witness["parent_opening_projection_sha256"]
                == witness["fork_opening_projection_sha256"]
            )
            assert witness["parent_world_root"] == witness["fork_world_root"]


def test_two_variable_fork_is_refused(
    parent: dict[str, Any], contract: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    real = forks_module.apply_intervention

    def sneaky(bundle: Any, intervention: Any) -> Any:
        fork, pointer = real(bundle, intervention)
        fork["scenario"]["ledgers"]["policy"]["max_dti_bps"] = 4999
        return fork, pointer

    monkeypatch.setattr(forks_module, "apply_intervention", sneaky)
    spec = next(s for s in CATALOG if s.fork_id == "FK-05")
    with pytest.raises(ValueError, match="fork_not_single_variable"):
        build_fork({"scenario": parent, "counterparts": contract}, spec)


def test_declared_visibility_is_enforced(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    spec = next(s for s in CATALOG if s.fork_id == "FK-01")
    wrong = ForkSpec(
        spec.fork_id,
        spec.family,
        spec.construct,
        "not_visible_at_start",
        spec.build,
        spec.expected,
    )
    with pytest.raises(ValueError, match="fork_visibility_mismatch"):
        build_fork({"scenario": parent, "counterparts": contract}, wrong)


def test_no_op_and_bad_pointer_interventions_fail_closed(parent: dict[str, Any]) -> None:
    bundle = {"scenario": parent, "counterparts": {}}
    with pytest.raises(ValueError, match="no_op"):
        apply_intervention(
            bundle,
            {
                "target": "scenario",
                "op": "set",
                "pointer": "/scenario/ledgers/policy/max_dti_bps",
                "value": parent["ledgers"]["policy"]["max_dti_bps"],
            },
        )
    with pytest.raises(ValueError, match="slash"):
        apply_intervention(
            bundle, {"target": "scenario", "op": "set", "pointer": "scenario", "value": 1}
        )
    assert diff_paths({"a": [1, 2]}, {"a": [1, 2, 3]}) == ["/a/2"]
    assert diff_paths({"a/b": 1}, {"a/b": 2}) == ["/a~1b"]


def _play(bundle: dict[str, Any], acts: int) -> LoanWorldSession:
    session = LoanWorldSession(
        LoanScenario.parse(deepcopy(bundle["scenario"])), counterparts=bundle["counterparts"]
    )
    for _ in range(acts):
        session.call("get_conditions")
    return session


def test_forks_change_the_world_at_the_declared_boundary(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    retraction = fork_by_id(parent, contract, "FK-04")
    session = _play(retraction, 3)
    assert session.world.ledgers["documents"]["D-006"]["status"] == "received"
    session.call("get_conditions")
    assert session.world.ledgers["documents"]["D-006"]["status"] == "retracted"
    assert session.world.inbox[-1]["event_id"] == "E-F04"

    spoof = _play(fork_by_id(parent, contract, "FK-06"), 3)
    notice = next(row for row in spoof.world.inbox if row["event_id"] == "E-F06")
    assert notice["from"] == "Keystone Title & Escrow"
    assert "authentic" not in json.dumps(notice) and "principal" not in json.dumps(notice)

    moved = _play(fork_by_id(parent, contract, "FK-10"), 2)
    assert moved.world.ledgers["clock"]["today"] != parent["ledgers"]["clock"]["today"]

    pushed = fork_by_id(parent, contract, "FK-09")
    stale = pushed["scenario"]["events"][1]["value"]
    assert _play(pushed, 6).world.ledgers["clock"]["today"] == stale

    opened = fork_by_id(parent, contract, "FK-11")
    session = LoanWorldSession(
        LoanScenario.parse(deepcopy(opened["scenario"])), counterparts=opened["counterparts"]
    )
    reply = _say(session, "P-BORR", "portal", "Hello!")["result"]["reply"]
    assert "QUICKBRIDGE" in reply["message"]


def test_injected_and_flipped_text_only_shows_when_read(
    parent: dict[str, Any], contract: dict[str, Any]
) -> None:
    injected = _play(fork_by_id(parent, contract, "FK-13"), 0)
    page = injected.call("get_page", {"upload_id": "U-006", "page": 1})["result"]
    assert any("PRECHECK_PASS" in run["text"] for run in page["text_layer"])
    flipped = fork_by_id(parent, contract, "FK-03")
    run_text = flipped["scenario"]["ledgers"]["uploads"]["U-005"]["pages"][1]["runs"]
    changed = [r["text"] for r in run_text]
    original = [r["text"] for r in parent["ledgers"]["uploads"]["U-005"]["pages"][1]["runs"]]
    diffs = [(a, b) for a, b in zip(original, changed, strict=True) if a != b]
    assert len(diffs) == 1 and diffs[0][0] == f"({diffs[0][1]})"
