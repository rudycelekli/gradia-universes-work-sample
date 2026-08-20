"""One canonical, disclosure-labeled bundle for the public Universe Explorer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, digest, load_json, write_canonical
from .runner import load_scenarios, run_panel

BUNDLE_SCHEMA = "public-universe-bundle.v1"
FEATURED_SCENARIO = "policy-revision"
FEATURED_POLICY = "stale_context"


def build_public_bundle(root: Path) -> dict[str, Any]:
    scenarios = load_scenarios(root / "fixtures")
    receipts, panel = run_panel(root / "fixtures")
    featured = next(
        row
        for row in receipts
        if row["scenario_id"] == FEATURED_SCENARIO
        and row["agent_policy"] == FEATURED_POLICY
    )
    scenario_source_sha256 = {
        value["scenario_id"]: digest(value)
        for path in sorted((root / "fixtures" / "scenarios").glob("*.json"))
        if isinstance((value := load_json(path)).get("scenario_id"), str)
    }
    scenario_rows = []
    for scenario in scenarios:
        scenario_rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "title": scenario.title,
                "scenario_sha256": scenario_source_sha256[scenario.scenario_id],
                "condition": "static_control" if not scenario.events else "world_change",
                "event_count": len(scenario.events),
                "restore_after_event": scenario.restore_after_event,
                "synthetic": scenario.synthetic,
            }
        )
    body = {
        "schema": BUNDLE_SCHEMA,
        "slug": "interruptible-underwriting-synthetic",
        "title": "Can an agent stay correct when its world changes?",
        "description": (
            "Five fully synthetic conditions test additions, revisions, retractions, "
            "restore lineage and an unauthorized message."
        ),
        "public_release_status": "candidate_not_authorized",
        "claim_boundary": panel["claim_boundary"],
        "construct": {
            "plain_language": (
                "Whether an agent uses current authoritative evidence after a declared "
                "change instead of committing from stale context or an unverified message."
            ),
            "technical": (
                "Action-bound changed-world adaptation, evidence freshness, authority "
                "handling and exactly-once restore semantics."
            ),
        },
        "provenance": {
            "synthetic": True,
            "customer_material": False,
            "premier_lending_material": False,
            "source_repository": "gradia-universes-work-sample",
            "license": "Apache-2.0",
        },
        "rights": {
            "evaluation": "allowed_synthetic",
            "training": "not_released",
            "public_display": "pending_exact_byte_owner_review",
            "model_output_release": "not_applicable_scripted_policies",
        },
        "measurement_status": {
            "scripted_harness_validation": "measured",
            "live_model_performance": "not_measured",
            "human_judge_agreement": "not_measured",
            "customer_validity": "not_measured",
            "downstream_training_lift": "not_measured",
        },
        "featured_receipt_sha256": featured["receipt_sha256"],
        "featured_reason": (
            "The terminal recommendation is plausible under the old policy, but the "
            "trajectory proves the policy changed and localizes four distinct failures."
        ),
        "scenarios": scenario_rows,
        "panel": panel,
        "episodes": receipts,
        "withheld_register": [
            {
                "field": "private_event_mutation_payload",
                "reason": (
                    "the agent-visible projection is released; hidden mutation controls are not"
                ),
            },
            {
                "field": "provider_credentials",
                "reason": "credentials never enter evidence or release artifacts",
            },
            {
                "field": "customer_facts",
                "reason": "the fixture is synthetic and carries no customer material",
            },
        ],
        "limitations": [
            "Five scenarios do not represent real underwriting work or population diversity.",
            (
                "Scripted policies validate harness sensitivity; they do not estimate model "
                "capability."
            ),
            (
                "A hash chain is tamper-evident but does not prove signer identity or truthful "
                "sensing."
            ),
            (
                "No human agreement, live model panel, customer validity or training lift is "
                "measured."
            ),
        ],
        "source_artifacts": {
            "panel_sha256": panel["report_sha256"],
            "receipt_sha256s": panel["receipt_chain"],
            "scenario_sha256s": [row["scenario_sha256"] for row in scenario_rows],
        },
    }
    return {**body, "bundle_sha256": digest(body)}


def verify_public_bundle(root: Path) -> dict[str, Any]:
    path = root / "release" / "public-universe-bundle.json"
    expected = build_public_bundle(root)
    committed = json.loads(path.read_bytes())
    if not isinstance(committed, dict):
        raise ValueError("public_bundle_object_required")
    if committed.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("public_bundle_schema_unsupported")
    claimed = committed.get("bundle_sha256")
    body = {key: value for key, value in committed.items() if key != "bundle_sha256"}
    if claimed != digest(body):
        raise ValueError("public_bundle_digest_mismatch")
    if canonical_bytes(committed) != canonical_bytes(expected):
        raise ValueError("public_bundle_replay_mismatch")
    return committed


def write_public_bundle(root: Path) -> dict[str, Any]:
    bundle = build_public_bundle(root)
    write_canonical(root / "release" / "public-universe-bundle.json", bundle)
    return bundle
