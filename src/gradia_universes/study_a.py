"""Deterministic engineering corpus for the preregistered Study A.

This module does not run the confirmatory study. It creates isolated synthetic
forks and reports which bytes survive five evidence projections. Projection
sensitivity is an upper bound on what a detector could use, not a measured
detector result and not evidence of research novelty.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, cast

from .canonical import canonical_bytes, digest, load_json, write_canonical
from .contracts import Scenario
from .runner import load_scenarios, run_episode

MutationId = Literal["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]
EvidencePolicy = Literal["T", "L+T", "M+T", "P+T*", "W"]

GENERATOR_VERSION = "gradia-study-a-mutation-generator.v1"
PROJECTION_VERSION = "gradia-study-a-evidence-projections.v1"
POLICIES: tuple[EvidencePolicy, ...] = ("T", "L+T", "M+T", "P+T*", "W")

MUTATIONS: dict[MutationId, dict[str, str]] = {
    "M1": {
        "label": "event logged but material root unchanged",
        "held_fixed": "event id, projection, terminal bytes",
        "discriminating_field": "before/after root transition",
    },
    "M2": {
        "label": "correct mutation, altered visible message",
        "held_fixed": "material transition, boundary",
        "discriminating_field": "visible projection",
    },
    "M3": {
        "label": "correct message, altered authority",
        "held_fixed": "message text, material transition",
        "discriminating_field": "projection authority",
    },
    "M4": {
        "label": "event duplicated after restore",
        "held_fixed": "terminal material state",
        "discriminating_field": "restore generation and multiplicity",
    },
    "M5": {
        "label": "event evidence missing after restore",
        "held_fixed": "snapshot identity and terminal material state",
        "discriminating_field": "preserved occurrence evidence",
    },
    "M6": {
        "label": "previous occurrence link broken",
        "held_fixed": "occurrence bodies",
        "discriminating_field": "previous occurrence linkage",
    },
    "M7": {
        "label": "invalid intermediate transition repaired at terminal",
        "held_fixed": "terminal material root",
        "discriminating_field": "intermediate occurrence root",
    },
    "M8": {
        "label": "event applied at wrong action boundary",
        "held_fixed": "event and terminal material state",
        "discriminating_field": "declared versus realized boundary",
    },
}


def _escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _changed_paths(left: Any, right: Any, path: str = "") -> list[str]:
    if type(left) is not type(right):
        return [path or "/"]
    if isinstance(left, dict):
        paths: list[str] = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}/{_escape_pointer(key)}"
            if key not in left or key not in right:
                paths.append(child)
            else:
                paths.extend(_changed_paths(left[key], right[key], child))
        return paths
    if isinstance(left, list):
        paths = []
        for index in range(max(len(left), len(right))):
            child = f"{path}/{index}"
            if index >= len(left) or index >= len(right):
                paths.append(child)
            else:
                paths.extend(_changed_paths(left[index], right[index], child))
        return paths
    return [] if left == right else [path or "/"]


def _equal_leaf_manifest(left: Any, right: Any, path: str = "") -> list[dict[str, Any]]:
    if type(left) is not type(right):
        return []
    if isinstance(left, dict):
        rows: list[dict[str, Any]] = []
        for key in sorted(set(left) & set(right)):
            rows.extend(
                _equal_leaf_manifest(
                    left[key], right[key], f"{path}/{_escape_pointer(key)}"
                )
            )
        return rows
    if isinstance(left, list):
        rows = []
        for index in range(min(len(left), len(right))):
            rows.extend(_equal_leaf_manifest(left[index], right[index], f"{path}/{index}"))
        return rows
    if left == right:
        return [{"path": path or "/", "value": left}]
    return []


def _rehash_occurrence(row: dict[str, Any]) -> None:
    row["visible_projection_sha256"] = digest(row["visible_projection"])
    body = {
        key: value
        for key, value in row.items()
        if key not in {"visible_projection", "occurrence_sha256"}
    }
    row["occurrence_sha256"] = digest(body)


def _rechain(receipt: dict[str, Any]) -> None:
    previous: str | None = None
    for occurrence in receipt["evolution_witness"]:
        occurrence["previous_occurrence_sha256"] = previous
        _rehash_occurrence(occurrence)
        previous = cast(str, occurrence["occurrence_sha256"])


def _rehash_restore_receipts(receipt: dict[str, Any]) -> None:
    for row in receipt["restore_receipts"]:
        body = {key: value for key, value in row.items() if key != "receipt_sha256"}
        row["receipt_sha256"] = digest(body)


def _rehash_receipt(receipt: dict[str, Any]) -> None:
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = digest(body)


def _refresh_restore_head(receipt: dict[str, Any]) -> None:
    if not receipt["restore_receipts"]:
        return
    occurrences = receipt["evolution_witness"]
    receipt["restore_receipts"][0]["occurrence_chain_head"] = (
        occurrences[0]["occurrence_sha256"] if occurrences else None
    )
    _rehash_restore_receipts(receipt)


def _event_act(receipt: dict[str, Any], event_id: str) -> int:
    for row in receipt["acts"]:
        if event_id in row.get("events_delivered_after_act", []):
            return cast(int, row["act_index"])
    raise ValueError(f"event_act_not_found:{event_id}")


def _remove_event_marker(receipt: dict[str, Any], event_id: str) -> None:
    for row in receipt["acts"]:
        events = row.get("events_delivered_after_act")
        if not isinstance(events, list) or event_id not in events:
            continue
        events.remove(event_id)
        if not events:
            del row["events_delivered_after_act"]
        return
    raise ValueError(f"event_marker_not_found:{event_id}")


def _add_event_marker(receipt: dict[str, Any], act_index: int, event_id: str) -> None:
    row = next((item for item in receipt["acts"] if item["act_index"] == act_index), None)
    if row is None:
        raise ValueError(f"event_target_act_not_found:{act_index}")
    events = row.setdefault("events_delivered_after_act", [])
    events.append(event_id)


def _state_changing_occurrence(receipt: dict[str, Any]) -> int:
    for index, row in enumerate(receipt["evolution_witness"]):
        if row["before_world_root"] != row["after_world_root"]:
            return index
    raise ValueError("state_changing_occurrence_not_found")


def _mutate(
    parent: dict[str, Any], mutation_id: MutationId
) -> tuple[dict[str, Any], list[str]]:
    fork = deepcopy(parent)
    witnesses = fork["evolution_witness"]
    primary: list[str]

    if mutation_id == "M1":
        index = _state_changing_occurrence(fork)
        witnesses[index]["after_world_root"] = witnesses[index]["before_world_root"]
        primary = [f"/evolution_witness/{index}/after_world_root"]
        _rechain(fork)
        _refresh_restore_head(fork)
    elif mutation_id == "M2":
        index = 0
        path = f"/evolution_witness/{index}/visible_projection/message"
        witnesses[index]["visible_projection"]["message"] += " [altered projection]"
        primary = [path]
        _rechain(fork)
        _refresh_restore_head(fork)
    elif mutation_id == "M3":
        index = 0
        path = f"/evolution_witness/{index}/visible_projection/authority"
        current = witnesses[index]["visible_projection"]["authority"]
        witnesses[index]["visible_projection"]["authority"] = (
            "unverified" if current == "authoritative" else "authoritative"
        )
        primary = [path]
        _rechain(fork)
        _refresh_restore_head(fork)
    elif mutation_id == "M4":
        if not fork["restore_receipts"]:
            raise ValueError("M4_requires_restore_parent")
        duplicate = deepcopy(witnesses[-1])
        duplicate["restore_generation"] = fork["restore_receipts"][0]["after_generation"]
        duplicate["before_world_root"] = fork["terminal_world_root"]
        duplicate["after_world_root"] = fork["terminal_world_root"]
        witnesses.append(duplicate)
        final_act = cast(int, fork["acts"][-1]["act_index"])
        _add_event_marker(fork, final_act, cast(str, duplicate["event_id"]))
        primary = [
            f"/acts/{len(fork['acts']) - 1}/events_delivered_after_act",
            f"/evolution_witness/{len(witnesses) - 1}",
        ]
        _rechain(fork)
        _rehash_restore_receipts(fork)
    elif mutation_id == "M5":
        if not fork["restore_receipts"]:
            raise ValueError("M5_requires_restore_parent")
        event_id = cast(str, witnesses[0]["event_id"])
        act_index = _event_act(fork, event_id)
        act_offset = next(
            index for index, row in enumerate(fork["acts"]) if row["act_index"] == act_index
        )
        witnesses.clear()
        _remove_event_marker(fork, event_id)
        fork["restore_receipts"][0]["occurrence_chain_head"] = None
        primary = [
            f"/acts/{act_offset}/events_delivered_after_act",
            "/evolution_witness/0",
            "/restore_receipts/0/occurrence_chain_head",
        ]
        _rehash_restore_receipts(fork)
    elif mutation_id == "M6":
        if len(witnesses) < 2:
            raise ValueError("M6_requires_two_occurrences")
        witnesses[1]["previous_occurrence_sha256"] = "0" * 64
        primary = ["/evolution_witness/1/previous_occurrence_sha256"]
        _rehash_occurrence(witnesses[1])
    elif mutation_id == "M7":
        index = _state_changing_occurrence(fork)
        invalid_root = "f" * 64
        if witnesses[index]["after_world_root"] == invalid_root:
            invalid_root = "e" * 64
        witnesses[index]["after_world_root"] = invalid_root
        primary = [f"/evolution_witness/{index}/after_world_root"]
        _rechain(fork)
        _refresh_restore_head(fork)
    elif mutation_id == "M8":
        index = 0
        event_id = cast(str, witnesses[index]["event_id"])
        old_act = _event_act(fork, event_id)
        new_act = old_act + 1
        _remove_event_marker(fork, event_id)
        _add_event_marker(fork, new_act, event_id)
        old_offset = next(
            offset for offset, row in enumerate(parent["acts"]) if row["act_index"] == old_act
        )
        new_offset = next(
            offset for offset, row in enumerate(parent["acts"]) if row["act_index"] == new_act
        )
        witnesses[index]["boundary_act"] = new_act
        primary = [
            f"/acts/{old_offset}/events_delivered_after_act",
            f"/acts/{new_offset}/events_delivered_after_act",
            f"/evolution_witness/{index}/boundary_act",
        ]
        _rechain(fork)
        _refresh_restore_head(fork)
    else:
        raise AssertionError(mutation_id)

    _rehash_receipt(fork)
    return fork, primary


def _project(policy: EvidencePolicy, receipt: dict[str, Any]) -> dict[str, Any]:
    terminal = {
        "terminal_world_root": receipt["terminal_world_root"],
        "submission": receipt["submission"],
    }
    if policy == "T":
        return terminal
    if policy == "L+T":
        return {
            **terminal,
            "ordinary_event_log": [
                {
                    "event_id": row["event_id"],
                    **row["visible_projection"],
                }
                for row in receipt["evolution_witness"]
            ],
        }
    if policy == "M+T":
        return {
            **terminal,
            "action_milestones": [
                {
                    "act_index": row["act_index"],
                    "tool": row["tool"],
                    "events_delivered_after_act": row["events_delivered_after_act"],
                }
                for row in receipt["acts"]
                if "events_delivered_after_act" in row
            ],
        }
    if policy == "P+T*":
        causal_steps = []
        previous: str | None = None
        for row in receipt["evolution_witness"]:
            body = {
                "event_id": row["event_id"],
                "event_sha256": row["event_sha256"],
                "boundary_act": row["boundary_act"],
                "before_world_root": row["before_world_root"],
                "after_world_root": row["after_world_root"],
                "restore_generation": row["restore_generation"],
                "previous_causal_step_sha256": previous,
            }
            step = {**body, "causal_step_sha256": digest(body)}
            causal_steps.append(step)
            previous = step["causal_step_sha256"]
        return {
            **terminal,
            "causal_execution_steps": causal_steps,
            "restore_checkpoints": [
                {
                    "before_generation": row["before_generation"],
                    "after_generation": row["after_generation"],
                    "world_root": row["world_root"],
                }
                for row in receipt["restore_receipts"]
            ],
        }
    return {
        **terminal,
        "acts": receipt["acts"],
        "evolution_witness": receipt["evolution_witness"],
        "restore_receipts": receipt["restore_receipts"],
    }


def _parents(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    scenarios = {
        row.scenario_id: row
        for row in load_scenarios(fixtures_dir)
        if row.scenario_id != "static-control"
    }
    chain = Scenario.parse(load_json(fixtures_dir / "study_a" / "chain_control.json"))
    scenarios[chain.scenario_id] = chain
    parents = {
        scenario_id: run_episode(scenario, "interrupt_safe")
        for scenario_id, scenario in sorted(scenarios.items())
    }
    refused = [
        scenario_id
        for scenario_id, receipt in parents.items()
        if not receipt["verdict"]["passed"]
    ]
    if refused:
        raise ValueError("study_a_parent_not_valid:" + ",".join(refused))
    return parents


def _eligible(mutation_id: MutationId, receipt: dict[str, Any]) -> bool:
    if mutation_id in {"M1", "M7"}:
        return any(
            row["before_world_root"] != row["after_world_root"]
            for row in receipt["evolution_witness"]
        )
    if mutation_id in {"M4", "M5"}:
        return bool(receipt["restore_receipts"])
    if mutation_id == "M6":
        return len(receipt["evolution_witness"]) >= 2
    return bool(receipt["evolution_witness"])


def build_study_a(fixtures_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    parents = _parents(fixtures_dir)
    forks: list[dict[str, Any]] = []
    for mutation_id in cast(tuple[MutationId, ...], tuple(MUTATIONS)):
        for scenario_id, parent in parents.items():
            if not _eligible(mutation_id, parent):
                continue
            fork, primary_paths = _mutate(parent, mutation_id)
            changed_paths = _changed_paths(parent, fork)
            missing_primary = sorted(
                primary
                for primary in primary_paths
                if not any(
                    changed == primary or changed.startswith(primary + "/")
                    for changed in changed_paths
                )
            )
            if missing_primary:
                raise ValueError(
                    f"study_a_primary_path_not_changed:{mutation_id}:"
                    + ",".join(missing_primary)
                )
            unchanged = _equal_leaf_manifest(parent, fork)
            sensitivity: dict[str, dict[str, Any]] = {}
            for policy in POLICIES:
                parent_view = _project(policy, parent)
                fork_view = _project(policy, fork)
                projected_changes = _changed_paths(parent_view, fork_view)
                sensitivity[policy] = {
                    "sensitive": bool(projected_changes),
                    "projected_changed_paths": projected_changes,
                    "evidence_bytes_parent": len(canonical_bytes(parent_view)),
                    "evidence_bytes_fork": len(canonical_bytes(fork_view)),
                }
            body = {
                "fork_id": f"{scenario_id}--{mutation_id.lower()}",
                "parent_scenario_id": scenario_id,
                "parent_receipt_sha256": parent["receipt_sha256"],
                "mutation_id": mutation_id,
                **MUTATIONS[mutation_id],
                "primary_changed_paths": sorted(primary_paths),
                "dependent_changed_paths": sorted(
                    changed
                    for changed in changed_paths
                    if not any(
                        changed == primary or changed.startswith(primary + "/")
                        for primary in primary_paths
                    )
                ),
                "all_changed_paths": changed_paths,
                "unchanged_leaf_manifest_sha256": digest(unchanged),
                "fork_receipt_sha256": fork["receipt_sha256"],
                "fork_artifact_sha256": digest(fork),
                "policy_projection_sensitivity": sensitivity,
            }
            forks.append({**body, "fork_manifest_sha256": digest(body)})

    corpus_body = {
        "schema": "gradia-study-a-engineering-corpus.v1",
        "claim_boundary": (
            "Synthetic paired projection-sensitivity engineering check only; "
            "not a confirmatory detector result, model result, prevalence estimate, "
            "or novelty claim."
        ),
        "generator_version": GENERATOR_VERSION,
        "projection_version": PROJECTION_VERSION,
        "causal_proxy_boundary": (
            "P+T* is an engineering proxy over causal steps, material roots and "
            "restore checkpoints; it is not a faithful reproduction of Proof of "
            "Execution and cannot fill the preregistered P+T result cell."
        ),
        "parent_receipts": [
            {
                "scenario_id": scenario_id,
                "receipt_sha256": receipt["receipt_sha256"],
                "receipt_artifact_sha256": digest(receipt),
            }
            for scenario_id, receipt in parents.items()
        ],
        "forks": forks,
    }
    corpus = {**corpus_body, "corpus_sha256": digest(corpus_body)}

    policy_rows = []
    for policy in POLICIES:
        detected = sum(
            1
            for row in forks
            if row["policy_projection_sensitivity"][policy]["sensitive"]
        )
        policy_rows.append(
            {
                "evidence_policy": policy,
                "invalid_forks": len(forks),
                "projection_sensitive": detected,
                "projection_insensitive": len(forks) - detected,
                "faithful_parent_projection_changes": 0,
            }
        )
    family_rows = []
    for mutation_id in MUTATIONS:
        cells = [row for row in forks if row["mutation_id"] == mutation_id]
        family_rows.append(
            {
                "mutation_id": mutation_id,
                "forks": len(cells),
                "sensitive_by_policy": {
                    policy: sum(
                        1
                        for row in cells
                        if row["policy_projection_sensitivity"][policy]["sensitive"]
                    )
                    for policy in POLICIES
                },
            }
        )
    report_body = {
        "schema": "gradia-study-a-engineering-report.v1",
        "claim_boundary": corpus["claim_boundary"],
        "corpus_sha256": corpus["corpus_sha256"],
        "parent_count": len(parents),
        "invalid_fork_count": len(forks),
        "policy_rows": policy_rows,
        "family_rows": family_rows,
        "confirmatory_study_status": "NOT_YET_RUN",
        "open_confirmatory_gates": [
            "faithful strongest-baseline reproduction or justified equivalent",
            "independent mutation-isolation audit",
            "public preregistration with frozen power and stopping rules",
            "detector implementations blinded to mutation labels",
            "two-reviewer human study",
            "E2B and AgentENV runtime conformance",
        ],
    }
    return corpus, {**report_body, "report_sha256": digest(report_body)}


def render_study_a(report: dict[str, Any]) -> str:
    lines = [
        "# Study A engineering projection-sensitivity check",
        "",
        f"**Boundary:** {report['claim_boundary']}",
        "",
        f"Parents: **{report['parent_count']}**  ",
        f"Isolated synthetic forks: **{report['invalid_fork_count']}**  ",
        f"Confirmatory status: **{report['confirmatory_study_status']}**",
        "",
        "| Evidence policy | Forks | Projection sensitive | Projection insensitive "
        "| Faithful-parent changes |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["policy_rows"]:
        lines.append(
            f"| `{row['evidence_policy']}` | {row['invalid_forks']} | "
            f"{row['projection_sensitive']} | {row['projection_insensitive']} | "
            f"{row['faithful_parent_projection_changes']} |"
        )
    lines.extend(
        [
            "",
            "`P+T*` is an engineering causal-evidence proxy, not a faithful Proof of "
            "Execution reproduction. These counts show only whether a paired change is "
            "present in a projection; they do not show that a blinded detector found it.",
            "",
            "## Mutation-family matrix",
            "",
            "| Family | Forks | T | L+T | M+T | P+T* | W |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["family_rows"]:
        values = row["sensitive_by_policy"]
        lines.append(
            f"| {row['mutation_id']} | {row['forks']} | {values['T']} | "
            f"{values['L+T']} | {values['M+T']} | {values['P+T*']} | {values['W']} |"
        )
    lines.extend(["", "## Gates that remain", ""])
    lines.extend(f"- {gate}" for gate in report["open_confirmatory_gates"])
    lines.extend(["", f"Report SHA-256: `{report['report_sha256']}`", ""])
    return "\n".join(lines)


def write_study_a(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    corpus, report = build_study_a(root / "fixtures")
    target = root / "results" / "reference" / "study-a-engineering"
    write_canonical(target / "corpus.json", corpus)
    write_canonical(target / "report.json", report)
    (target / "REPORT.md").write_text(render_study_a(report), encoding="utf-8")
    return corpus, report
