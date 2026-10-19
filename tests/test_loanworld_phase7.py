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
