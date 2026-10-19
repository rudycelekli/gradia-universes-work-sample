"""Phase 7: a parent is no longer hard-wired to D-001..D-009 / C-001..C-007."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gradia_universes.canonical import canonical_bytes, digest, load_json
from gradia_universes.loanworld import GENERATOR_VERSION, GENERATOR_VERSION_V2
from gradia_universes.loanworld.counterparts import build_counterparts
from gradia_universes.loanworld.draws import derive_seed
from gradia_universes.loanworld.generator import LEGACY, build_parent, draw_shape
from gradia_universes.loanworld.oracle import Truth
from gradia_universes.loanworld.splits import (
    DEV_INDEXES,
    DEV_MASTER,
    build_commitment,
    dev_parent,
    verify_reveal,
)
from gradia_universes.loanworld.topology import derive

ROOT = Path(__file__).resolve().parents[1]
LW = ROOT / "fixtures" / "loanworld"
PARENTS = sorted(p.stem for p in (LW / "parents").glob("*.json"))


def _parent(parent_id: str) -> dict[str, Any]:
    value: dict[str, Any] = load_json(LW / "parents" / f"{parent_id}.json")
    return value


def test_dev_001_topology_matches_the_constants_it_replaces() -> None:
    topo = derive(_parent("loanworld-parent-dev-001"))
    assert topo.requirements == {
        "C-001": {"docs": ["D-001", "D-003", "D-004"], "fresh": ["D-001"]},
        "C-002": {"docs": ["D-005", "D-006"], "fresh": ["D-005", "D-006"]},
        "C-003": {"docs": ["D-009", "D-006"], "fresh": ["D-006"], "signed": ["D-009"]},
        "C-004": {"docs": ["D-007"], "fresh": []},
        "C-005": {"service": "appraisal"},
        "C-006": {"service": "title"},
        "C-007": {"premature_at_precheck": True},
    }
    assert topo.newest_stub == "D-001" and topo.last_statement == "D-006"
    assert topo.income_docs == {"D-001", "D-002", "D-003", "D-004", "D-007"}


def test_dev_parents_come_from_derived_seeds_and_differ_in_structure() -> None:
    assert [f"loanworld-parent-dev-{i:03d}" for i in (1, *DEV_INDEXES)] == PARENTS
    shapes = set()
    for index in DEV_INDEXES:
        committed = _parent(f"loanworld-parent-dev-{index:03d}")
        seed = derive_seed(DEV_MASTER, "dev", index, GENERATOR_VERSION_V2)
        assert committed["generator"] == {
            "name": "gradia_universes.loanworld.generator",
            "version": GENERATOR_VERSION_V2,
            "seed": seed,
        }
        assert canonical_bytes(dev_parent(index)) == canonical_bytes(committed)
        topo = derive(committed)
        shapes.add((tuple(sorted(topo.roles.items())), topo.pay_stubs, topo.statements))
    assert _parent("loanworld-parent-dev-001")["generator"]["version"] == GENERATOR_VERSION
    assert len(shapes) == len(DEV_INDEXES)  # IDs really move between parents


def test_legacy_shape_is_not_drawn_and_drawn_shapes_vary() -> None:
    assert draw_shape("dev-001") != LEGACY
    seen = {draw_shape(f"seed-{i}").condition_order for i in range(20)}
    assert len(seen) > 5
    assert all(order[-1] == "funding" for order in seen)


def test_underivable_condition_fails_closed() -> None:
    scenario = build_parent("fail-closed-01")
    next(iter(scenario["ledgers"]["conditions"].values()))["satisfied_by"] = ["tax_return"]
    with pytest.raises(ValueError, match="topology_requirement_underivable"):
        derive(scenario)


@pytest.mark.parametrize("parent_id", PARENTS)
def test_oracle_requirements_follow_each_parent(parent_id: str) -> None:
    scenario = _parent(parent_id)
    truth = Truth({"scenario": scenario}, None)
    documents = scenario["ledgers"]["documents"]
    for condition_id, requirement in truth.requirements.items():
        condition = scenario["ledgers"]["conditions"][condition_id]
        for doc_id in requirement.get("docs", []):
            assert documents[doc_id]["doc_type"] in condition["satisfied_by"]
    gift = truth.requirements[truth.topology.condition("gift")]
    deposit = gift["fresh"][0]
    month = scenario["ledgers"]["case"]["gift"]["deposit_txn_month"]
    assert any(
        v["field_id"].endswith("statement_period") and v["norm"][1][:7] == month
        for v in documents[deposit]["critical_values"]
    )


def test_heldout_commitment_reveals_and_refuses_a_wrong_master(tmp_path: Path) -> None:
    master = "a" * 64
    gates = {i: {"solvable": True, "isolated": True} for i in (1, 2, 3)}
    commitment = build_commitment(master, gates)
    assert master not in str(commitment)
    path = tmp_path / "commitment.json"
    from gradia_universes.canonical import write_canonical

    write_canonical(path, commitment)
    assert verify_reveal(path, master)["commitment_sha256"] == commitment["commitment_sha256"]
    with pytest.raises(ValueError, match="heldout_master_does_not_match"):
        verify_reveal(path, "b" * 64)
    with pytest.raises(ValueError, match="too_short"):
        build_commitment("short", gates)


def test_committed_heldout_commitment_has_no_seed_or_truth() -> None:
    from gradia_universes.loanworld.splits import COMMITMENT_PATH, verify_commitment_shape

    committed = verify_commitment_shape(ROOT / COMMITMENT_PATH)
    assert len(committed["parents"]) == 3
    text = (ROOT / COMMITMENT_PATH).read_text()
    assert '"ledgers"' not in text and '"seed":' not in text
    assert not list((LW / "parents").glob("*heldout*"))


def test_counterpart_disclosure_keyword_follows_the_creditor() -> None:
    for parent_id in PARENTS:
        scenario = _parent(parent_id)
        creditor = scenario["ledgers"]["case"]["liabilities"]["hidden"][0]["creditor"]
        keywords = build_counterparts(scenario)["actors"]["P-BORR"]["moves"][0]["trigger"]
        assert creditor.split()[0].lower() in keywords["any_keywords"]
    assert digest(build_counterparts(_parent("loanworld-parent-dev-001"))) == digest(
        load_json(LW / "counterparts" / "loanworld-parent-dev-001.json")
    )


# ---------------------------------------------------------------- renderer K5-K8


@pytest.mark.parametrize("condition", ["K5", "K6", "K7", "K8"])
def test_new_capture_conditions_render_deterministically_with_usable_quads(
    condition: str, tmp_path: Path
) -> None:
    pytest.importorskip("fitz")
    import numpy as np
    from PIL import Image

    from gradia_universes.loanworld.draws import Draws
    from gradia_universes.loanworld.generator import _capture
    from gradia_universes.loanworld.render import _homography, render_scenario

    scenario = dev_parent(2)
    scenario["scenario_id"] = f"probe-{condition}"
    uploads = scenario["ledgers"]["uploads"]
    keep = sorted(uploads)[0]
    for upload_id in list(uploads):
        if upload_id != keep:
            del uploads[upload_id]
    upload = uploads[keep]
    upload.update(media="image", text_layer_overrides={})
    upload["capture"] = _capture(Draws(f"probe-{condition}", "capture"), condition)
    first = render_scenario(scenario, tmp_path)
    assert render_scenario(scenario, tmp_path) == first
    row = first["files"][0]
    assert row["quad_exact"] is (condition != "K6")
    image = np.asarray(Image.open(tmp_path / row["path"]).convert("L"), dtype=float)
    width, height = upload["page_size"]
    a, b, c, d, e, f, g, h = _homography(
        [(float(x), float(y)) for x, y in row["quad_px"]],
        [(0.0, 0.0), (float(width), 0.0), (float(width), float(height)), (0.0, float(height))],
    )
    hits = total = 0
    document = next(
        doc for doc in scenario["ledgers"]["documents"].values() if doc["upload_id"] == keep
    )
    for value in document["critical_values"]:
        if value["upload_page"] != 1 or value["hand"]:
            continue
        x0, y0, x1, y1 = value["bbox_cpt"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        den = g * cx + h * cy + 1
        px, py = (a * cx + b * cy + c) / den, (d * cx + e * cy + f) / den
        if 0 <= px < image.shape[1] and 0 <= py < image.shape[0]:
            total += 1
            window = image[
                max(0, int(py) - 6) : int(py) + 6, max(0, int(px) - 25) : int(px) + 25
            ]
            hits += bool(window.min() < image.mean() - 60)
    assert total >= 5 and hits / total >= (0.7 if condition == "K6" else 0.9)


# ---------------------------------------------------------------- F6 successor handoff

DEV_001_BUNDLES = {  # fork_bundle_sha256[:16] from catalog 0.1.0, before phase 7
    "FK-00": "69dbac68d22ece72",
    "FK-01": "0fbaa6f062d990ee",
    "FK-02": "8d1983287c24531c",
    "FK-03": "69a5352b76415be3",
    "FK-04": "92b12cc4a26f5192",
    "FK-05": "6709487fee52ea18",
    "FK-06": "e9fb8e65a82a12d7",
    "FK-07": "87317154e3641701",
    "FK-08": "45b558ac2cadc289",
    "FK-09": "51c841dba7eb9fb8",
    "FK-10": "e0cc359aadf9e16b",
    "FK-11": "ad8f11c5b47f6721",
    "FK-12": "c159aae2521160ea",
    "FK-13": "96182be5936041dc",
}


def _bundle(parent_id: str, fork_id: str) -> dict[str, Any]:
    from gradia_universes.loanworld.forks import fork_by_id

    return fork_by_id(
        _parent(parent_id), load_json(LW / "counterparts" / f"{parent_id}.json"), fork_id
    )


def test_generalized_catalog_leaves_every_dev_001_fork_bundle_unchanged() -> None:
    manifest = load_json(LW / "forks" / "loanworld-parent-dev-001.json")
    witnesses = {w["fork_id"]: w for w in manifest["forks"]}
    for fork_id, prefix in DEV_001_BUNDLES.items():
        assert witnesses[fork_id]["fork_bundle_sha256"].startswith(prefix)
    assert [w["fork_id"] for w in manifest["forks"] if w["harness"] == "handoff"] == [
        "FK-14",
        "FK-15",
        "FK-16",
    ]
    assert manifest["families_not_in_v0"] == []


def test_f6_change_lands_after_the_predecessor_and_before_the_successor() -> None:
    from gradia_universes.loanworld.forks import HANDOFF_ACT
    from gradia_universes.loanworld.handoff import (
        artifact_follower,
        handoff_bound,
        run_handoff_episode,
        scripted_predecessor,
    )
    from gradia_universes.loanworld.policies import reference_plan
    from gradia_universes.loanworld.schema import LoanScenario

    bundle = _bundle("loanworld-parent-dev-002", "FK-14")
    plan = reference_plan(bundle)
    seen: list[dict[str, Any]] = []
    inner = scripted_predecessor(plan, HANDOFF_ACT)

    def predecessor(message: dict[str, Any]) -> dict[str, Any]:
        seen.append(message)
        return inner(message)

    follower = artifact_follower()
    first: dict[str, Any] = {}

    def successor(message: dict[str, Any]) -> dict[str, Any]:
        first.setdefault("start", message)
        return follower(message)

    result = run_handoff_episode(
        LoanScenario.parse(bundle["scenario"]),
        predecessor,
        successor,
        HANDOFF_ACT,
        counterparts=bundle["counterparts"],
    )
    assert result["outcome"] == "terminal" and handoff_bound(result, HANDOFF_ACT)
    assert seen[-1] == {"type": "handoff_request", "act": HANDOFF_ACT}
    assert not any("E-F14" in str(m) for m in seen)  # the predecessor never sees it
    inbox_ids = [row["event_id"] for row in first["start"]["projection"]["inbox"]]
    assert "E-F14" in inbox_ids  # the cold successor's world already has it
    assert first["start"]["acts_used"] == HANDOFF_ACT
    assert set(first["start"]) >= {"handoff", "projection", "tools"}


def test_handoff_failures_are_censored_not_scored() -> None:
    from gradia_universes.loanworld.handoff import run_handoff_episode
    from gradia_universes.loanworld.policies import null_agent
    from gradia_universes.loanworld.schema import LoanScenario

    bundle = _bundle("loanworld-parent-dev-001", "FK-00")
    scenario = LoanScenario.parse(bundle["scenario"])
    early = run_handoff_episode(scenario, null_agent, null_agent, 5)
    assert (early["outcome"], early["censor_reason"]) == (
        "censored",
        "finished_before_handoff",
    )

    def bad(message: dict[str, Any]) -> dict[str, Any]:
        if message["type"] == "handoff_request":
            return {"type": "handoff", "artifact": {"notes": "x"}}
        return {"type": "call", "tool": "get_conditions", "args": {}}

    broken = run_handoff_episode(scenario, bad, null_agent, 3)
    assert broken["censor_reason"] == "malformed_handoff"


def test_oracle_refuses_an_f6_pass_without_the_handoff_harness() -> None:
    from gradia_universes.loanworld.adapter import run_python_agent
    from gradia_universes.loanworld.baselines import solver_plan
    from gradia_universes.loanworld.oracle import grade_episode
    from gradia_universes.loanworld.policies import plan_agent
    from gradia_universes.loanworld.schema import LoanScenario

    bundle = _bundle("loanworld-parent-dev-001", "FK-16")
    manifest = load_json(LW / "forks" / "loanworld-parent-dev-001.json")
    labels = next(w for w in manifest["forks"] if w["fork_id"] == "FK-16")["expected_draft"]
    result = run_python_agent(
        LoanScenario.parse(bundle["scenario"]),
        plan_agent(solver_plan(bundle, "FK-16")),
        counterparts=bundle["counterparts"],
    )
    grade = grade_episode(bundle, labels, result, "FK-16")
    assert not grade["terminal_pass"]
    assert grade["criteria"]["handoff_bound_to_receipts"] is False
