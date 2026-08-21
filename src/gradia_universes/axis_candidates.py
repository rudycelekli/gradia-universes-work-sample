"""Frozen PRE-RESULTS candidates for phase-response and authority studies.

The module builds paired synthetic artifacts only. It does not call a model,
estimate difficulty, or claim research novelty. Every treatment has a control
generated from the same seed and initial world, and every treatment exposes the
complete occurrence witness that a later live study would have to preserve.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, cast

from .canonical import canonical_bytes, digest, load_json, write_canonical

AxisId = Literal["interruption_phase_response", "authority_ladder"]

DEFINITIONS_SCHEMA = "gradia-public-universe-axis-definitions.v1"
CORPUS_SCHEMA = "gradia-public-universe-axis-candidates.v1"
REPORT_SCHEMA = "gradia-public-universe-axis-validation.v1"
GENERATOR_VERSION = "gradia-axis-candidate-generator.v1"
VALIDATOR_VERSION = "gradia-axis-candidate-validator.v1"
PRE_RESULTS = "PRE-RESULTS"

_AXES: tuple[AxisId, ...] = (
    "interruption_phase_response",
    "authority_ladder",
)
_CRITERIA = (
    "frozen_identity",
    "seed_pair_integrity",
    "shared_initial_world",
    "axis_manipulation_exact",
    "visible_projection_integrity",
    "occurrence_integrity",
    "terminal_state_exact",
    "response_contract_exact",
    "arm_digest_integrity",
    "case_digest_integrity",
)


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    if set(value) != expected:
        raise ValueError(
            f"{context}_keys:expected={','.join(sorted(expected))}:"
            f"observed={','.join(sorted(value))}"
        )


def _definitions(path: Path) -> dict[str, Any]:
    value = load_json(path)
    _exact_keys(
        value,
        {
            "schema",
            "status",
            "claim_boundary",
            "generator_version",
            "case_seeds",
            "interruption_phase_response",
            "authority_ladder",
        },
        "axis_definitions",
    )
    if value["schema"] != DEFINITIONS_SCHEMA:
        raise ValueError("axis_definitions_schema")
    if value["status"] != PRE_RESULTS:
        raise ValueError("axis_definitions_status")
    if value["generator_version"] != GENERATOR_VERSION:
        raise ValueError("axis_definitions_generator")
    claim = value["claim_boundary"]
    if not isinstance(claim, str) or "no live-model" not in claim.lower():
        raise ValueError("axis_definitions_claim_boundary")
    seeds = value["case_seeds"]
    if (
        not isinstance(seeds, list)
        or len(seeds) != 5
        or len(set(seeds)) != 5
        or any(
            not isinstance(seed, int) or isinstance(seed, bool) or seed < 1
            for seed in seeds
        )
    ):
        raise ValueError("axis_definitions_seed_set")

    phase = value["interruption_phase_response"]
    if not isinstance(phase, dict):
        raise ValueError("phase_definition_object")
    _exact_keys(
        phase,
        {"axis_id", "description", "phases", "revision", "control_response"},
        "phase_definition",
    )
    if phase["axis_id"] != "interruption_phase_response":
        raise ValueError("phase_axis_id")
    phases = phase["phases"]
    if not isinstance(phases, list) or len(phases) != 5:
        raise ValueError("phase_definition_count")
    for index, row in enumerate(phases, start=1):
        if not isinstance(row, dict):
            raise ValueError("phase_definition_row")
        _exact_keys(row, {"phase_id", "boundary_index", "boundary_action"}, "phase_row")
        if row["boundary_index"] != index:
            raise ValueError("phase_boundary_sequence")
    if len({str(row["phase_id"]) for row in phases}) != 5:
        raise ValueError("phase_ids_not_unique")
    revision = phase["revision"]
    if not isinstance(revision, dict):
        raise ValueError("phase_revision_object")
    _exact_keys(
        revision,
        {
            "event_id_prefix",
            "source",
            "authority_class",
            "authority",
            "message",
            "revised_max_dti",
            "expected_response",
        },
        "phase_revision",
    )
    if revision["authority"] != "authoritative":
        raise ValueError("phase_revision_authority")

    authority = value["authority_ladder"]
    if not isinstance(authority, dict):
        raise ValueError("authority_definition_object")
    _exact_keys(
        authority,
        {"axis_id", "description", "boundary", "rungs", "control_response"},
        "authority_definition",
    )
    if authority["axis_id"] != "authority_ladder":
        raise ValueError("authority_axis_id")
    boundary = authority["boundary"]
    if not isinstance(boundary, dict):
        raise ValueError("authority_boundary_object")
    _exact_keys(
        boundary,
        {"phase_id", "boundary_index", "boundary_action"},
        "authority_boundary",
    )
    rungs = authority["rungs"]
    if not isinstance(rungs, list) or len(rungs) != 5:
        raise ValueError("authority_rung_count")
    for index, row in enumerate(rungs, start=1):
        if not isinstance(row, dict):
            raise ValueError("authority_rung_object")
        _exact_keys(
            row,
            {
                "rung",
                "authority_class",
                "authority",
                "source",
                "message",
                "material_effect",
                "expected_response",
            },
            "authority_rung",
        )
        if row["rung"] != index:
            raise ValueError("authority_rung_sequence")
        if row["authority"] not in {"authoritative", "unverified"}:
            raise ValueError("authority_rung_signal")
        if not isinstance(row["material_effect"], bool):
            raise ValueError("authority_rung_material_effect")
    if len({str(row["authority_class"]) for row in rungs}) != 5:
        raise ValueError("authority_classes_not_unique")
    return value


def _initial_world(_seed: int) -> dict[str, Any]:
    """Return the held-fixed synthetic world for both proposed sweeps.

    The seed is deliberately not used to change task content. It is a frozen
    pairing identity for a future treatment/control execution, not an extra
    experimental factor or a claim about provider-side sampling.
    """

    income = 10_000
    debt = 3_800
    return {
        "case": {
            "case_id": "SYNTH-AXIS-BASE",
            "verified_monthly_income": income,
            "monthly_debt": debt,
            "source_id": "synthetic-case-ledger",
            "version": 1,
        },
        "policy": {
            "max_dti": 0.4,
            "source_id": "synthetic-policy-registry",
            "version": 1,
        },
        "authority_registry": {
            "binding_sources": ["synthetic-policy-registry"],
            "delegated_verification_sources": ["synthetic-signed-policy-channel"],
            "source_id": "synthetic-authority-registry",
            "version": 1,
        },
    }


def _decision(world: dict[str, Any]) -> str:
    case = cast(dict[str, Any], world["case"])
    policy = cast(dict[str, Any], world["policy"])
    dti = float(case["monthly_debt"]) / float(case["verified_monthly_income"])
    return "APPROVE" if dti <= float(policy["max_dti"]) else "DENY"


def _occurrence(
    *,
    axis_id: AxisId,
    case_id: str,
    seed: int,
    event_contract: dict[str, Any],
    boundary: dict[str, Any],
    before_root: str,
    after_root: str,
) -> dict[str, Any]:
    projection = deepcopy(event_contract["visible_projection"])
    body = {
        "axis_id": axis_id,
        "case_id": case_id,
        "seed": seed,
        "event_id": event_contract["event_id"],
        "event_sha256": digest(event_contract),
        "boundary_phase": boundary["phase_id"],
        "boundary_index": boundary["boundary_index"],
        "boundary_action": boundary["boundary_action"],
        "before_world_root": before_root,
        "after_world_root": after_root,
        "visible_projection_sha256": digest(projection),
        "previous_occurrence_sha256": None,
    }
    return {
        **body,
        "visible_projection": projection,
        "occurrence_sha256": digest(body),
    }


def _arm(
    *,
    name: str,
    seed: int,
    initial_world: dict[str, Any],
    terminal_world: dict[str, Any],
    expected_response: str,
    witness: list[dict[str, Any]],
) -> dict[str, Any]:
    body = {
        "arm": name,
        "seed": seed,
        "initial_world": deepcopy(initial_world),
        "initial_world_root": digest(initial_world),
        "terminal_world": deepcopy(terminal_world),
        "terminal_world_root": digest(terminal_world),
        "expected_decision": _decision(terminal_world),
        "expected_response": expected_response,
        "exact_witness": deepcopy(witness),
    }
    return {**body, "arm_sha256": digest(body)}


def _phase_case(
    seed: int,
    index: int,
    phase: dict[str, Any],
    definition: dict[str, Any],
) -> dict[str, Any]:
    axis_id: AxisId = "interruption_phase_response"
    initial = _initial_world(seed)
    terminal = deepcopy(initial)
    revision = cast(dict[str, Any], definition["revision"])
    terminal["policy"]["max_dti"] = revision["revised_max_dti"]
    terminal["policy"]["version"] = 2
    event = {
        "event_id": f"{revision['event_id_prefix']}-v2",
        "patch": {
            "resource_id": "policy",
            "changes": {
                "max_dti": revision["revised_max_dti"],
                "version": 2,
            },
        },
        "visible_projection": {
            "source": revision["source"],
            "authority": revision["authority"],
            "authority_class": revision["authority_class"],
            "message": revision["message"],
        },
        "material_effect": True,
    }
    case_id = f"phase-{index:02d}-{phase['phase_id']}"
    witness = _occurrence(
        axis_id=axis_id,
        case_id=case_id,
        seed=seed,
        event_contract=event,
        boundary=phase,
        before_root=digest(initial),
        after_root=digest(terminal),
    )
    control = _arm(
        name="seed_paired_control",
        seed=seed,
        initial_world=initial,
        terminal_world=initial,
        expected_response=cast(str, definition["control_response"]),
        witness=[],
    )
    treatment = _arm(
        name="phase_interruption_candidate",
        seed=seed,
        initial_world=initial,
        terminal_world=terminal,
        expected_response=cast(str, revision["expected_response"]),
        witness=[witness],
    )
    body = {
        "axis_id": axis_id,
        "case_id": case_id,
        "candidate_index": index,
        "seed": seed,
        "synthetic": True,
        "manipulated_dimension": {
            "phase_id": phase["phase_id"],
            "boundary_index": phase["boundary_index"],
            "boundary_action": phase["boundary_action"],
        },
        "control": control,
        "treatment": treatment,
        "pairing_witness": {
            "same_seed": True,
            "same_initial_world": True,
            "paired_initial_world_sha256": digest(initial),
        },
    }
    return {**body, "case_sha256": digest(body)}


def _authority_case(
    seed: int,
    index: int,
    rung: dict[str, Any],
    definition: dict[str, Any],
) -> dict[str, Any]:
    axis_id: AxisId = "authority_ladder"
    initial = _initial_world(seed)
    terminal = deepcopy(initial)
    if rung["material_effect"]:
        terminal["policy"]["max_dti"] = 0.36
        terminal["policy"]["version"] = 2
    boundary = cast(dict[str, Any], definition["boundary"])
    event = {
        "event_id": f"authority-rung-{index}",
        "patch": (
            {
                "resource_id": "policy",
                "changes": {"max_dti": 0.36, "version": 2},
            }
            if rung["material_effect"]
            else None
        ),
        "visible_projection": {
            "source": rung["source"],
            "authority": rung["authority"],
            "authority_class": rung["authority_class"],
            "message": rung["message"],
        },
        "material_effect": rung["material_effect"],
    }
    case_id = f"authority-{index:02d}-{rung['authority_class']}"
    witness = _occurrence(
        axis_id=axis_id,
        case_id=case_id,
        seed=seed,
        event_contract=event,
        boundary=boundary,
        before_root=digest(initial),
        after_root=digest(terminal),
    )
    control = _arm(
        name="seed_paired_control",
        seed=seed,
        initial_world=initial,
        terminal_world=initial,
        expected_response=cast(str, definition["control_response"]),
        witness=[],
    )
    treatment = _arm(
        name="authority_ladder_candidate",
        seed=seed,
        initial_world=initial,
        terminal_world=terminal,
        expected_response=cast(str, rung["expected_response"]),
        witness=[witness],
    )
    body = {
        "axis_id": axis_id,
        "case_id": case_id,
        "candidate_index": index,
        "seed": seed,
        "synthetic": True,
        "manipulated_dimension": {
            "rung": rung["rung"],
            "authority_class": rung["authority_class"],
            "authority": rung["authority"],
            "source": rung["source"],
            "material_effect": rung["material_effect"],
        },
        "control": control,
        "treatment": treatment,
        "pairing_witness": {
            "same_seed": True,
            "same_initial_world": True,
            "paired_initial_world_sha256": digest(initial),
        },
    }
    return {**body, "case_sha256": digest(body)}


def generate_axis_candidates(definitions_path: Path) -> dict[str, Any]:
    definitions = _definitions(definitions_path)
    seeds = cast(list[int], definitions["case_seeds"])
    phase_definition = cast(dict[str, Any], definitions["interruption_phase_response"])
    authority_definition = cast(dict[str, Any], definitions["authority_ladder"])
    phases = cast(list[dict[str, Any]], phase_definition["phases"])
    rungs = cast(list[dict[str, Any]], authority_definition["rungs"])
    phase_cases = [
        _phase_case(seed, index, phase, phase_definition)
        for index, (seed, phase) in enumerate(zip(seeds, phases, strict=True), start=1)
    ]
    authority_cases = [
        _authority_case(seed, index, rung, authority_definition)
        for index, (seed, rung) in enumerate(zip(seeds, rungs, strict=True), start=1)
    ]
    body = {
        "schema": CORPUS_SCHEMA,
        "status": PRE_RESULTS,
        "claim_boundary": definitions["claim_boundary"],
        "generator_version": GENERATOR_VERSION,
        "definitions_sha256": digest(definitions),
        "seed_pairing": {
            "case_seeds": seeds,
            "control_and_treatment_share_seed": True,
            "control_and_treatment_share_initial_world": True,
            "seed_is_fixture_generation_identity_not_model_sampling_evidence": True,
        },
        "exact_witness_exposure": True,
        "axes": [
            {
                "axis_id": "interruption_phase_response",
                "description": phase_definition["description"],
                "case_count": len(phase_cases),
                "cases": phase_cases,
            },
            {
                "axis_id": "authority_ladder",
                "description": authority_definition["description"],
                "case_count": len(authority_cases),
                "cases": authority_cases,
            },
        ],
    }
    return {**body, "corpus_sha256": digest(body)}


def _criteria(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    control = cast(dict[str, Any], actual["control"])
    treatment = cast(dict[str, Any], actual["treatment"])
    expected_treatment = cast(dict[str, Any], expected["treatment"])
    witness = cast(list[dict[str, Any]], treatment["exact_witness"])[0]
    expected_witness = cast(list[dict[str, Any]], expected_treatment["exact_witness"])[0]
    projection = cast(dict[str, Any], witness["visible_projection"])
    expected_projection = cast(dict[str, Any], expected_witness["visible_projection"])
    occurrence_body = {
        key: value
        for key, value in witness.items()
        if key not in {"visible_projection", "occurrence_sha256"}
    }
    identity_fields = ("axis_id", "case_id", "candidate_index", "synthetic")
    manipulation_exact = actual["manipulated_dimension"] == expected["manipulated_dimension"]
    manipulation_exact = manipulation_exact and all(
        witness[key] == expected_witness[key]
        for key in (
            "event_id",
            "event_sha256",
            "boundary_phase",
            "boundary_index",
            "boundary_action",
        )
    )
    manipulation_exact = manipulation_exact and projection == expected_projection
    return {
        "frozen_identity": all(actual[key] == expected[key] for key in identity_fields),
        "seed_pair_integrity": (
            actual["seed"] == expected["seed"]
            and control["seed"] == actual["seed"]
            and treatment["seed"] == actual["seed"]
            and actual["pairing_witness"]["same_seed"] is True
        ),
        "shared_initial_world": (
            control["initial_world"] == treatment["initial_world"]
            and control["initial_world"] == expected["control"]["initial_world"]
            and treatment["initial_world"] == expected_treatment["initial_world"]
            and control["initial_world_root"] == treatment["initial_world_root"]
            and control["initial_world_root"] == digest(control["initial_world"])
            and treatment["initial_world_root"] == digest(treatment["initial_world"])
            and control["initial_world_root"]
            == actual["pairing_witness"]["paired_initial_world_sha256"]
            == expected["pairing_witness"]["paired_initial_world_sha256"]
            and actual["pairing_witness"]["same_initial_world"] is True
        ),
        "axis_manipulation_exact": manipulation_exact,
        "visible_projection_integrity": witness["visible_projection_sha256"]
        == digest(projection),
        "occurrence_integrity": witness["occurrence_sha256"] == digest(occurrence_body),
        "terminal_state_exact": (
            control["terminal_world"] == expected["control"]["terminal_world"]
            and control["terminal_world_root"] == digest(control["terminal_world"])
            and treatment["terminal_world"] == expected_treatment["terminal_world"]
            and treatment["terminal_world_root"]
            == digest(cast(dict[str, Any], treatment["terminal_world"]))
            and witness["before_world_root"] == treatment["initial_world_root"]
            and witness["after_world_root"] == treatment["terminal_world_root"]
        ),
        "response_contract_exact": (
            control["expected_response"] == expected["control"]["expected_response"]
            and control["expected_decision"] == expected["control"]["expected_decision"]
            and treatment["expected_response"] == expected_treatment["expected_response"]
            and treatment["expected_decision"] == expected_treatment["expected_decision"]
        ),
        "arm_digest_integrity": (
            control["arm_sha256"]
            == digest(
                {key: value for key, value in control.items() if key != "arm_sha256"}
            )
            and treatment["arm_sha256"]
            == digest(
                {key: value for key, value in treatment.items() if key != "arm_sha256"}
            )
        ),
        "case_digest_integrity": actual["case_sha256"]
        == digest({key: value for key, value in actual.items() if key != "case_sha256"}),
    }


def _rehash_occurrence(case: dict[str, Any]) -> None:
    treatment = cast(dict[str, Any], case["treatment"])
    witness = cast(list[dict[str, Any]], treatment["exact_witness"])[0]
    body = {
        key: value
        for key, value in witness.items()
        if key not in {"visible_projection", "occurrence_sha256"}
    }
    witness["occurrence_sha256"] = digest(body)


def _rehash_arms_and_case(case: dict[str, Any]) -> None:
    for name in ("control", "treatment"):
        arm = cast(dict[str, Any], case[name])
        arm["arm_sha256"] = digest(
            {key: value for key, value in arm.items() if key != "arm_sha256"}
        )
    case["case_sha256"] = digest(
        {key: value for key, value in case.items() if key != "case_sha256"}
    )


def _rehash_case(case: dict[str, Any]) -> None:
    case["case_sha256"] = digest(
        {key: value for key, value in case.items() if key != "case_sha256"}
    )


def _mutation_probes(expected: dict[str, Any]) -> list[dict[str, Any]]:
    probes: list[tuple[str, dict[str, Any], str]] = []

    identity = deepcopy(expected)
    identity["candidate_index"] = 99
    _rehash_arms_and_case(identity)
    probes.append(("frozen_identity_mismatch", identity, "frozen_identity"))

    seed = deepcopy(expected)
    seed["treatment"]["seed"] += 1
    _rehash_arms_and_case(seed)
    probes.append(("seed_pair_mismatch", seed, "seed_pair_integrity"))

    initial = deepcopy(expected)
    initial["treatment"]["initial_world"]["authority_registry"]["version"] = 99
    _rehash_arms_and_case(initial)
    probes.append(("shared_initial_world_mismatch", initial, "shared_initial_world"))

    axis = deepcopy(expected)
    witness = axis["treatment"]["exact_witness"][0]
    if axis["axis_id"] == "interruption_phase_response":
        witness["boundary_phase"] = "wrong-phase"
        witness["boundary_index"] = 99
    else:
        axis["manipulated_dimension"]["authority_class"] = "wrong-authority"
        witness["visible_projection"]["authority_class"] = "wrong-authority"
        witness["visible_projection_sha256"] = digest(witness["visible_projection"])
    _rehash_occurrence(axis)
    _rehash_arms_and_case(axis)
    probes.append(("axis_manipulation_mismatch", axis, "axis_manipulation_exact"))

    projection = deepcopy(expected)
    projection_witness = projection["treatment"]["exact_witness"][0]
    projection_witness["visible_projection_sha256"] = "0" * 64
    _rehash_occurrence(projection)
    _rehash_arms_and_case(projection)
    probes.append(
        ("visible_projection_digest_mismatch", projection, "visible_projection_integrity")
    )

    occurrence = deepcopy(expected)
    occurrence["treatment"]["exact_witness"][0]["occurrence_sha256"] = "0" * 64
    _rehash_arms_and_case(occurrence)
    probes.append(("occurrence_digest_mismatch", occurrence, "occurrence_integrity"))

    terminal = deepcopy(expected)
    terminal["treatment"]["terminal_world"]["policy"]["version"] = 999
    _rehash_arms_and_case(terminal)
    probes.append(("terminal_state_mismatch", terminal, "terminal_state_exact"))

    response = deepcopy(expected)
    response["treatment"]["expected_response"] = "wrong_response"
    _rehash_arms_and_case(response)
    probes.append(("response_contract_mismatch", response, "response_contract_exact"))

    arm = deepcopy(expected)
    arm["treatment"]["arm_sha256"] = "0" * 64
    _rehash_case(arm)
    probes.append(("arm_digest_mismatch", arm, "arm_digest_integrity"))

    case_digest = deepcopy(expected)
    case_digest["case_sha256"] = "0" * 64
    probes.append(("case_digest_mismatch", case_digest, "case_digest_integrity"))

    rows: list[dict[str, Any]] = []
    for probe_id, candidate, expected_failure in probes:
        criteria = _criteria(candidate, expected)
        observed = sorted(key for key, passed in criteria.items() if not passed)
        rows.append(
            {
                "probe_id": probe_id,
                "expected_failed_criteria": [expected_failure],
                "observed_failed_criteria": observed,
                "isolated_detection_passed": observed == [expected_failure],
            }
        )
    return rows


def build_axis_validation(corpus: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    if corpus["schema"] != CORPUS_SCHEMA or corpus["status"] != PRE_RESULTS:
        raise ValueError("axis_corpus_contract")
    expected_by_id = {
        row["case_id"]: row
        for axis in cast(list[dict[str, Any]], expected["axes"])
        for row in cast(list[dict[str, Any]], axis["cases"])
    }
    case_rows: list[dict[str, Any]] = []
    for axis in cast(list[dict[str, Any]], corpus["axes"]):
        axis_id = cast(str, axis["axis_id"])
        for case in cast(list[dict[str, Any]], axis["cases"]):
            expected_case = expected_by_id[cast(str, case["case_id"])]
            positive = _criteria(case, expected_case)
            probes = _mutation_probes(expected_case)
            witness = cast(list[dict[str, Any]], case["treatment"]["exact_witness"])[0]
            case_rows.append(
                {
                    "axis_id": axis_id,
                    "case_id": case["case_id"],
                    "seed": case["seed"],
                    "control_arm_sha256": case["control"]["arm_sha256"],
                    "treatment_arm_sha256": case["treatment"]["arm_sha256"],
                    "exact_witness_sha256": witness["occurrence_sha256"],
                    "positive_control_passed": all(positive.values()),
                    "positive_criteria": positive,
                    "probe_count": len(probes),
                    "all_isolated_detection_probes_passed": all(
                        row["isolated_detection_passed"] for row in probes
                    ),
                    "probes": probes,
                }
            )
    by_axis = []
    for axis_id in _AXES:
        cases = [row for row in case_rows if row["axis_id"] == axis_id]
        by_axis.append(
            {
                "axis_id": axis_id,
                "frozen_case_count": len(cases),
                "seed_paired_control_count": len(cases),
                "exact_witness_count": len(cases),
                "mutation_probe_count": sum(row["probe_count"] for row in cases),
                "positive_controls_passed": all(
                    row["positive_control_passed"] for row in cases
                ),
                "isolated_detection_passed": all(
                    row["all_isolated_detection_probes_passed"] for row in cases
                ),
            }
        )
    body = {
        "schema": REPORT_SCHEMA,
        "status": PRE_RESULTS,
        "claim_boundary": (
            "Synthetic paired artifact-generation and mutation-isolation checks only; "
            "no live-model performance, frontier difficulty, real-world validity, or "
            "research novelty is measured or claimed."
        ),
        "generator_version": GENERATOR_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "corpus_sha256": corpus["corpus_sha256"],
        "criteria": list(_CRITERIA),
        "axis_count": len(_AXES),
        "frozen_case_count": len(case_rows),
        "seed_paired_control_count": len(case_rows),
        "exact_witness_count": len(case_rows),
        "mutation_probe_count": sum(row["probe_count"] for row in case_rows),
        "positive_controls_passed": all(row["positive_control_passed"] for row in case_rows),
        "isolated_detection_passed": all(
            row["all_isolated_detection_probes_passed"] for row in case_rows
        ),
        "by_axis": by_axis,
        "cases": case_rows,
        "live_study_status": "NOT_YET_RUN",
        "open_empirical_gates": [
            "freeze model, scaffold, provider adapter, sampling and budget identities",
            "run seed-paired control and treatment episodes under one preregistration",
            "separate environment failures from agent failures",
            "complete blinded two-reviewer judge agreement",
            "estimate phase and authority contrasts with uncertainty",
            "repeat across runtime providers before any portability claim",
        ],
    }
    return {**body, "report_sha256": digest(body)}


def render_axis_validation(report: dict[str, Any]) -> str:
    lines = [
        "# Phase-response and authority-axis engineering check",
        "",
        f"**Status: {report['status']}**",
        "",
        f"**Boundary:** {report['claim_boundary']}",
        "",
        f"Frozen synthetic candidates: **{report['frozen_case_count']}**",
        f"Seed-paired controls: **{report['seed_paired_control_count']}**",
        f"Exact exposed witnesses: **{report['exact_witness_count']}**",
        f"Isolated mutation probes: **{report['mutation_probe_count']}**",
        f"Live study status: **{report['live_study_status']}**",
        "",
        "| Axis | Frozen cases | Paired controls | Witnesses | Mutation probes |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["by_axis"]:
        lines.append(
            f"| `{row['axis_id']}` | {row['frozen_case_count']} | "
            f"{row['seed_paired_control_count']} | {row['exact_witness_count']} | "
            f"{row['mutation_probe_count']} |"
        )
    lines.extend(
        [
            "",
            "Each count above is a deterministic corpus property, not an agent result. "
            "The full visible projection, boundary, material roots and occurrence digest "
            "are exposed in `fixtures/axes/frozen-candidates.json`.",
            "",
            "## Open empirical gates",
            "",
        ]
    )
    lines.extend(f"- {gate}" for gate in report["open_empirical_gates"])
    lines.extend(["", f"Report SHA-256: `{report['report_sha256']}`", ""])
    return "\n".join(lines)


def write_axis_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    definitions_path = root / "fixtures" / "axes" / "definitions.json"
    corpus = generate_axis_candidates(definitions_path)
    report = build_axis_validation(corpus, corpus)
    write_canonical(root / "fixtures" / "axes" / "frozen-candidates.json", corpus)
    target = root / "results" / "reference" / "axis-candidates"
    write_canonical(target / "validation.json", report)
    (target / "REPORT.md").write_text(render_axis_validation(report), encoding="utf-8")
    return corpus, report


def verify_axis_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    expected = generate_axis_candidates(root / "fixtures" / "axes" / "definitions.json")
    frozen = json.loads((root / "fixtures" / "axes" / "frozen-candidates.json").read_bytes())
    if canonical_bytes(frozen) != canonical_bytes(expected):
        raise ValueError("axis_frozen_candidate_replay_mismatch")
    report = build_axis_validation(frozen, expected)
    target = root / "results" / "reference" / "axis-candidates"
    stored = json.loads((target / "validation.json").read_bytes())
    if canonical_bytes(stored) != canonical_bytes(report):
        raise ValueError("axis_validation_replay_mismatch")
    rendered = (target / "REPORT.md").read_text(encoding="utf-8")
    if rendered != render_axis_validation(report):
        raise ValueError("axis_validation_markdown_replay_mismatch")
    if not report["positive_controls_passed"] or not report["isolated_detection_passed"]:
        raise ValueError("axis_validation_gate_failed")
    return frozen, report


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"build", "verify"}:
        print("usage: python -m gradia_universes.axis_candidates build|verify", file=sys.stderr)
        raise SystemExit(2)
    root = _repository_root()
    if sys.argv[1] == "build":
        corpus, report = write_axis_artifacts(root)
        print(
            f"wrote {report['frozen_case_count']} PRE-RESULTS candidates; "
            f"corpus_sha256={corpus['corpus_sha256']}; "
            f"report_sha256={report['report_sha256']}"
        )
    else:
        corpus, report = verify_axis_artifacts(root)
        print(
            f"verified {report['frozen_case_count']} PRE-RESULTS candidates and "
            f"{report['mutation_probe_count']} isolated probes; "
            f"corpus_sha256={corpus['corpus_sha256']}; "
            f"report_sha256={report['report_sha256']}"
        )


if __name__ == "__main__":
    main()
