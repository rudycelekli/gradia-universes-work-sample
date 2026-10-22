from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from gradia_universes.canonical import canonical_bytes, digest
from gradia_universes.loanworld.adapter import run_python_agent, run_stdio_episode
from gradia_universes.loanworld.cli import verify_parents
from gradia_universes.loanworld.draws import Draws, derive_seed
from gradia_universes.loanworld.generator import build_gold_parent, money
from gradia_universes.loanworld.policies import null_agent
from gradia_universes.loanworld.schema import LoanScenario
from gradia_universes.loanworld.tools import (
    LoanWorldSession,
    verify_proof_pack,
    verify_receipts,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw() -> dict[str, Any]:
    return build_gold_parent("test-seed-001")


@pytest.fixture()
def scenario(raw: dict[str, Any]) -> LoanScenario:
    return LoanScenario.parse(deepcopy(raw))


def _upload_citation(upload_id: str = "U-002", page: int = 1) -> dict[str, Any]:
    return {"upload_id": upload_id, "page": page}


# ---------------------------------------------------------------- determinism


def test_draws_are_portable_and_seeded() -> None:
    a, b = Draws("s", "x"), Draws("s", "x")
    assert [a.between(0, 999) for _ in range(20)] == [b.between(0, 999) for _ in range(20)]
    assert Draws("s", "y").between(0, 10**9) != Draws("s", "x").between(0, 10**9)
    assert derive_seed("m", "dev", 1, "v") == derive_seed("m", "dev", 1, "v")
    assert len(derive_seed("m", "dev", 1, "v")) == 16


def test_generator_is_byte_reproducible(raw: dict[str, Any]) -> None:
    assert canonical_bytes(build_gold_parent("test-seed-001")) == canonical_bytes(raw)
    assert digest(build_gold_parent("test-seed-002")) != digest(raw)
    assert "." not in json.dumps(raw["ledgers"]["case"]["pay_stubs"])  # integer cents only


def test_committed_parents_regenerate_and_pass_null_control() -> None:
    rows = verify_parents(ROOT)
    by_id = {row["scenario_id"]: row for row in rows}
    assert by_id["loanworld-parent-dev-001"]["documents"] == 9  # frozen generator 0.1.0
    assert len(rows) == 4 and all(9 <= row["documents"] <= 11 for row in rows)


# ---------------------------------------------------------------- case truth


def test_case_truth_is_internally_consistent(raw: dict[str, Any]) -> None:
    case = raw["ledgers"]["case"]
    for stub in case["pay_stubs"]:
        deductions = sum(
            stub[k] for k in ("k401", "federal", "social_security", "medicare", "state")
        )
        assert stub["net"] == stub["gross"] - deductions
        assert stub["ytd_gross"] == stub["gross"] * stub["periods_ytd"]
    assert case["employment"]["annual_base"] == case["employment"]["per_period_gross"] * 26
    statements = case["bank"]["statements"]
    assert statements[1]["opening"] == statements[0]["closing"]
    for statement in statements:
        balance = statement["opening"]
        for txn in statement["transactions"]:
            balance += txn["amount"]
            assert txn["balance"] == balance
        assert statement["closing"] == balance
    for w2 in case["w2s"]:
        assert w2["box1"] + w2["box12_d"] == w2["box5"]
    deposits = [
        t
        for s in statements
        for t in s["transactions"]
        if t["amount"] == case["gift"]["amount"]
    ]
    assert len(deposits) == 1
    stated = case["stated_on_application"]["base_monthly_income"]
    assert stated < case["employment"]["annual_base"] // 12


def test_older_stub_is_stale_by_pay_date_only_when_planted(raw: dict[str, Any]) -> None:
    today = date.fromisoformat(raw["ledgers"]["clock"]["today"])
    recency = raw["ledgers"]["policy"]["recency_days"]["pay_stub"]
    newest = date.fromisoformat(raw["ledgers"]["case"]["pay_stubs"][0]["pay_date"])
    assert today - newest <= timedelta(days=recency)


def test_every_critical_value_is_printed_at_its_box(raw: dict[str, Any]) -> None:
    uploads = raw["ledgers"]["uploads"]
    for document in raw["ledgers"]["documents"].values():
        upload = uploads[document["upload_id"]]
        for value in document["critical_values"]:
            run = upload["pages"][value["upload_page"] - 1]["runs"][value["run_index"]]
            assert run["text"] == value["raw"]
            assert run["bbox_cpt"] == value["bbox_cpt"]
            x0, y0, x1, y1 = value["bbox_cpt"]
            assert 0 <= x0 < x1 <= upload["page_size"][0]
            assert 0 <= y0 < y1 <= upload["page_size"][1]


def test_money_styles() -> None:
    assert money(-123456) == "-1,234.56"
    assert money(-123456, "paren") == "(1,234.56)"
    assert money(5) == "0.05"


# ---------------------------------------------------------------- schema


def test_schema_fails_closed(raw: dict[str, Any]) -> None:
    bad = deepcopy(raw)
    bad["extra"] = 1
    with pytest.raises(ValueError, match="loan_scenario_keys_invalid"):
        LoanScenario.parse(bad)
    bad = deepcopy(raw)
    bad["synthetic"] = False
    with pytest.raises(ValueError, match="must_be_synthetic"):
        LoanScenario.parse(bad)
    bad = deepcopy(raw)
    bad["events"][0]["value"] = {"x": 1}
    with pytest.raises(ValueError, match="notice_cannot_mutate"):
        LoanScenario.parse(bad)
    bad = deepcopy(raw)
    bad["events"][1]["target"] = "outbox"
    with pytest.raises(ValueError, match="loan_event_target_invalid"):
        LoanScenario.parse(bad)
    bad = deepcopy(raw)
    bad["ledgers"]["uploads"]["U-001"]["capture"]["condition"] = "K0"
    with pytest.raises(ValueError, match="image_upload_cannot_be_native_pdf"):
        LoanScenario.parse(bad)


# ---------------------------------------------------------------- projection


def test_projection_never_leaks_truth(scenario: LoanScenario, raw: dict[str, Any]) -> None:
    session = LoanWorldSession(scenario)
    visible = json.dumps(session.call("get_projection")["result"])
    case = raw["ledgers"]["case"]
    assert case["borrower"]["ssn"] not in visible
    assert "QUICKBRIDGE" not in visible  # hidden debt appears only after a credit pull
    assert "critical_values" not in visible and "expected_flag" not in visible
    assert "authentic" not in visible
    pulled = json.dumps(session.call("order_service", {"kind": "credit"})["result"])
    assert "QUICKBRIDGE" in pulled


def test_image_pages_have_no_text_layer_and_pdf_layer_can_lie(
    scenario: LoanScenario, raw: dict[str, Any]
) -> None:
    session = LoanWorldSession(scenario)
    photo = session.call("get_page", {"upload_id": "U-001", "page": 1})["result"]
    assert photo["text_layer"] is None
    voe = session.call("get_page", {"upload_id": "U-006", "page": 1})["result"]
    texts = [run["text"] for run in voe["text_layer"]]
    truth = money(raw["ledgers"]["case"]["employment"]["annual_base"])
    assert truth not in texts  # the text layer carries the override, not the truth


# ---------------------------------------------------------------- world and events


def test_events_fire_exactly_once_across_restore(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    for _ in range(5):
        session.call("get_conditions")
    snapshot = session.snapshot()
    for _ in range(3):
        session.call("get_conditions")
    assert [row.event_id for row in session.engine.occurrences] == ["E-001", "E-002"]
    restored = LoanWorldSession.restore(scenario, snapshot)
    assert restored.world.restore_generation == 1
    for _ in range(3):
        restored.call("get_conditions")
    assert [row.event_id for row in restored.engine.occurrences] == ["E-001", "E-002"]
    assert restored.world.ledgers["clock"]["today"] == session.world.ledgers["clock"]["today"]


def test_notice_changes_inbox_not_root(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    roots = []
    for _ in range(3):
        session.call("get_conditions")
        roots.append(session.world.root)
    assert roots[1] == roots[2]
    assert session.world.inbox[0]["event_id"] == "E-001"


# ---------------------------------------------------------------- tools


def test_tool_validation_fails_closed(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    assert session.call("teleport")["error"] == "unknown_tool"
    assert session.call("get_page", {"upload_id": "U-001"})["error"] == "missing_arg:page"
    assert session.call("get_page", {"upload_id": "U-001", "page": 1, "x": 1})[
        "error"
    ].startswith("unknown_args")
    cleared = session.call(
        "clear_condition", {"condition_id": "C-001", "citations": [], "note": "trust me"}
    )
    assert cleared["error"] == "citations_required"
    assert session.world.ledgers["conditions"]["C-001"]["status"] == "open"
    bad_page = session.call(
        "flag",
        {
            "code": "OTHER",
            "target": "U-001",
            "citations": [_upload_citation("U-001", 9)],
            "note": "x",
        },
    )
    assert bad_page["error"] == "citation_page_out_of_range"
    unpulled = session.call(
        "flag",
        {
            "code": "LOX_REQUIRED",
            "target": "credit",
            "citations": [{"service": "credit"}],
            "note": "x",
        },
    )
    assert unpulled["error"] == "citation_service_not_returned"
    read_only = session.call(
        "write_los_field",
        {"key": "L-0091", "value": "2030-01-01", "citation": _upload_citation()},
    )
    assert read_only["error"] == "los_field_read_only"
    assert len(session.receipts) == session.act == 7  # failed calls still cost an act


def test_effects_are_recorded_in_root_owned_ledgers(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    before = session.world.ledger_roots()
    session.call(
        "write_los_field",
        {"key": "L-0065", "value": "someone@mail.example.test", "citation": _upload_citation()},
    )
    after = session.world.ledger_roots()
    assert [name for name in before if before[name] != after[name]] == ["los"]
    log = session.world.ledgers["los"]["write_log"]
    assert log[0]["prior"].startswith("***-**-")  # the legacy SSN field was overwritten


def test_duplicate_external_effect_after_restore_is_recorded(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    snapshot = session.snapshot()
    request = {"party": "P-BORR", "doc_type": "bank_statement", "reason": "October statement"}
    assert (
        session.call("request_document", request)["result"]["duplicate_after_restore"] is False
    )
    restored = LoanWorldSession.restore(scenario, snapshot, already_sent=session.sent_keys)
    response = restored.call("request_document", request)
    assert response["result"]["duplicate_after_restore"] is True
    assert restored.world.ledgers["outbox"]["document_requests"][0]["restore_generation"] == 1


def test_message_records_whether_channel_is_on_file(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    session.call("send_message", {"party": "P-DONOR", "channel": "email", "text": "Confirm?"})
    assert session.world.ledgers["outbox"]["messages"][0]["channel_on_file"] is False


def test_submit_is_terminal_and_requires_cited_claims(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    bad = session.call(
        "submit", {"recommendation": "APPROVE", "open_conditions": [], "account": []}
    )
    assert bad["error"] == "recommendation_invalid"
    uncited = session.call(
        "submit",
        {
            "recommendation": "ESCALATE",
            "open_conditions": [],
            "account": [{"claim": "Income verified", "citations": []}],
        },
    )
    assert uncited["error"] == "citations_required"
    done = session.call(
        "submit",
        {
            "recommendation": "CONDITIONAL",
            "open_conditions": ["C-005"],
            "account": [
                {"claim": "Stub shows biweekly pay", "citations": [_upload_citation()]}
            ],
        },
    )
    assert done["ok"] and session.terminal is not None
    assert session.call("get_conditions")["error"] == "episode_already_submitted"


# ---------------------------------------------------------------- evidence


def test_receipts_and_proof_pack_detect_tampering(scenario: LoanScenario) -> None:
    result = run_python_agent(scenario, null_agent)
    pack = result["proof_pack"]
    verify_proof_pack(pack)
    assert result["outcome"] == "terminal"
    assert pack["terminal"]["recommendation"] == "ESCALATE"
    tampered = deepcopy(pack)
    tampered["receipts"][0]["args"]["reason"] = "edited later"
    with pytest.raises(ValueError, match="receipt_args_digest_mismatch"):
        verify_receipts(tampered["receipts"])
    tampered = deepcopy(pack)
    tampered["terminal"]["recommendation"] = "PRECHECK_PASS"
    with pytest.raises(ValueError, match="proof_pack_digest_mismatch"):
        verify_proof_pack(tampered)


def test_restore_rejects_a_broken_receipt_chain(scenario: LoanScenario) -> None:
    session = LoanWorldSession(scenario)
    session.call("list_uploads")
    session.call("get_conditions")
    snapshot = session.snapshot()
    snapshot["receipts"][1]["previous_receipt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="receipt_chain_previous_mismatch"):
        LoanWorldSession.restore(scenario, snapshot)


# ---------------------------------------------------------------- adapter

_STDIO_AGENT = """
import json, sys
for line in sys.stdin:
    message = json.loads(line)
    if message["type"] == "end":
        break
    if message["type"] == "start":
        assert "case" not in json.dumps(message["projection"]["uploads"])
        call = {"type": "call", "tool": "list_uploads", "args": {}}
    else:
        call = {"type": "call", "tool": "submit",
                "args": {"recommendation": "ESCALATE", "open_conditions": [], "account": []}}
    print(json.dumps(call), flush=True)
"""


def test_stdio_adapter_runs_an_external_agent(scenario: LoanScenario) -> None:
    result = run_stdio_episode(
        scenario, [sys.executable, "-c", _STDIO_AGENT], step_timeout_s=20
    )
    assert result["outcome"] == "terminal", result["censor_reason"]
    assert result["acts"] == 2
    verify_proof_pack(result["proof_pack"])


def test_stdio_adapter_censors_infrastructure_failures(scenario: LoanScenario) -> None:
    garbage = run_stdio_episode(
        scenario, [sys.executable, "-c", "print('not json')"], step_timeout_s=20
    )
    assert garbage["outcome"] == "censored"
    assert garbage["censor_reason"] == "malformed_agent_message"
    silent = run_stdio_episode(scenario, [sys.executable, "-c", "pass"], step_timeout_s=20)
    assert silent["outcome"] == "censored"
    assert silent["censor_reason"] in {"agent_exited", "agent_not_accepting_input"}


# ---------------------------------------------------------------- optional renderer


def test_renderer_is_deterministic_when_installed(raw: dict[str, Any], tmp_path: Path) -> None:
    pytest.importorskip("fitz")
    from gradia_universes.loanworld.render import render_scenario

    first = render_scenario(raw, tmp_path)
    second = render_scenario(raw, tmp_path)
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert first["handwriting_source"] == "font_placeholder_not_valid_for_test"
    pdfs = [row for row in first["files"] if row["media"] == "pdf"]
    images = [row for row in first["files"] if row["media"] == "image"]
    assert {row["upload_id"] for row in pdfs} == {"U-002", "U-006"}
    assert all(len(row["quad_px"]) == 4 for row in images)


# ---------------------------------------------------------------- preregistration


def test_design_preregistration_is_self_digested(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gradia_universes.canonical import write_canonical
    from gradia_universes.loanworld import prereg

    monkeypatch.setattr(prereg, "clean_git_sha", lambda root: "a" * 40)
    with pytest.raises(ValueError, match="rfc3339"):
        prereg.build_design_preregistration(ROOT, "yesterday")
    value = prereg.build_design_preregistration(ROOT, "2026-10-18T12:00:00Z")
    assert value["spend_cap_usd"] == 0 and value["parents_sha256"]
    path = tmp_path / "prereg.json"
    write_canonical(path, value)
    assert prereg.verify_design_preregistration(path)["digest"] == value["digest"]
    write_canonical(path, {**value, "spend_cap_usd": 0, "families": ["edited"]})
    with pytest.raises(ValueError, match="prereg_digest_mismatch"):
        prereg.verify_design_preregistration(path)
