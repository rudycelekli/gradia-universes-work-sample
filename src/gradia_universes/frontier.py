"""Hard, solvable, synthetic long-horizon Universe conditions.

The original five scenarios remain small harness controls.  This module adds a
separate multi-file queue-allocation task whose difficulty comes from coupled
decisions, staged authoritative changes, scarce capacity, restore and evidence
freshness.  It is fictional and must not be interpreted as lending policy.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from .canonical import digest, load_json
from .contracts import Observation
from .live_runner import CompletionBackend, CompletionBackendStop

Outcome = Literal["APPROVE", "APPROVE_EXCEPTION", "ESCALATE", "DENY"]

FRONTIER_SCAFFOLD_VERSION = "gradia-frontier-json-action-scaffold.v1"
FRONTIER_JUDGE_VERSION = "gradia-frontier-queue-deterministic-judge.v2"
FRONTIER_SCHEMA = "gradia-frontier-universe-scenario.v1"

FRONTIER_TOOLS: dict[str, set[str]] = {
    "source.list": set(),
    "source.read": {"resource_id"},
    "metrics.calculate": {"case_id"},
    "inbox.read": set(),
    "timeline.await_cutoff": set(),
    "decision.submit": {
        "decisions",
        "exception_award",
        "observed_world_root",
        "citations",
        "rationale",
    },
}


def _exact_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{context}_unknown_fields:{','.join(unknown)}")


@dataclass(frozen=True)
class FrontierPatch:
    resource_id: str
    path: tuple[str | int, ...]
    value: Any

    @classmethod
    def parse(cls, value: dict[str, Any], resources: set[str]) -> FrontierPatch:
        _exact_keys(value, {"resource_id", "path", "value"}, "frontier_patch")
        resource_id = value.get("resource_id")
        path = value.get("path")
        if not isinstance(resource_id, str) or resource_id not in resources:
            raise ValueError("frontier_patch_resource_invalid")
        if (
            not isinstance(path, list)
            or not path
            or any(
                not isinstance(item, (str, int)) or isinstance(item, bool)
                for item in path
            )
        ):
            raise ValueError("frontier_patch_path_invalid")
        return cls(
            resource_id,
            tuple(cast(list[str | int], path)),
            deepcopy(value.get("value")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "path": list(self.path),
            "value": deepcopy(self.value),
        }


@dataclass(frozen=True)
class FrontierTrigger:
    kind: Literal["after_act", "after_tool"]
    act_index: int | None
    tool: str | None
    occurrence: int | None

    @classmethod
    def parse(cls, value: dict[str, Any]) -> FrontierTrigger:
        kind = value.get("kind")
        if kind == "after_act":
            _exact_keys(value, {"kind", "act_index"}, "frontier_trigger")
            act_index = value.get("act_index")
            if not isinstance(act_index, int) or isinstance(act_index, bool) or act_index < 1:
                raise ValueError("frontier_trigger_act_invalid")
            return cls("after_act", act_index, None, None)
        if kind == "after_tool":
            _exact_keys(value, {"kind", "tool", "occurrence"}, "frontier_trigger")
            tool = value.get("tool")
            occurrence = value.get("occurrence")
            if not isinstance(tool, str) or tool not in FRONTIER_TOOLS:
                raise ValueError("frontier_trigger_tool_invalid")
            if (
                not isinstance(occurrence, int)
                or isinstance(occurrence, bool)
                or occurrence < 1
            ):
                raise ValueError("frontier_trigger_occurrence_invalid")
            return cls("after_tool", None, tool, occurrence)
        raise ValueError("frontier_trigger_kind_invalid")

    def as_dict(self) -> dict[str, Any]:
        if self.kind == "after_act":
            return {"kind": self.kind, "act_index": self.act_index}
        return {"kind": self.kind, "tool": self.tool, "occurrence": self.occurrence}


@dataclass(frozen=True)
class FrontierEvent:
    event_id: str
    trigger: FrontierTrigger
    patches: tuple[FrontierPatch, ...]
    observation: Observation
    restore_after: bool

    @classmethod
    def parse(cls, value: dict[str, Any], resources: set[str]) -> FrontierEvent:
        _exact_keys(
            value,
            {"event_id", "trigger", "patches", "observation", "restore_after"},
            "frontier_event",
        )
        event_id = value.get("event_id")
        trigger = value.get("trigger")
        patches = value.get("patches")
        observation = value.get("observation")
        restore_after = value.get("restore_after")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("frontier_event_id_required")
        if not isinstance(trigger, dict):
            raise ValueError("frontier_event_trigger_required")
        if not isinstance(patches, list):
            raise ValueError("frontier_event_patches_required")
        if not isinstance(observation, dict):
            raise ValueError("frontier_event_observation_required")
        if not isinstance(restore_after, bool):
            raise ValueError("frontier_event_restore_invalid")
        parsed_patches = tuple(
            FrontierPatch.parse(row, resources) for row in patches if isinstance(row, dict)
        )
        if len(parsed_patches) != len(patches):
            raise ValueError("frontier_event_patch_object_required")
        authority = observation.get("authority")
        if authority == "unverified" and parsed_patches:
            raise ValueError("unverified_frontier_event_cannot_mutate_world")
        return cls(
            event_id=event_id,
            trigger=FrontierTrigger.parse(trigger),
            patches=parsed_patches,
            observation=Observation.parse(observation),
            restore_after=restore_after,
        )

    def private_contract(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trigger": self.trigger.as_dict(),
            "patches": [row.as_dict() for row in self.patches],
            "observation": self.observation.public_view(self.event_id),
            "restore_after": self.restore_after,
        }


@dataclass(frozen=True)
class FrontierScenario:
    scenario_id: str
    title: str
    resources: dict[str, dict[str, Any]]
    events: tuple[FrontierEvent, ...]
    synthetic: bool

    @classmethod
    def parse(cls, value: dict[str, Any]) -> FrontierScenario:
        _exact_keys(
            value,
            {"schema", "scenario_id", "title", "resources", "events", "synthetic"},
            "frontier_scenario",
        )
        if value.get("schema") != FRONTIER_SCHEMA:
            raise ValueError("frontier_scenario_schema_unsupported")
        scenario_id = value.get("scenario_id")
        title = value.get("title")
        resources = value.get("resources")
        events = value.get("events")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise ValueError("frontier_scenario_id_required")
        if not isinstance(title, str) or not title:
            raise ValueError("frontier_scenario_title_required")
        if not isinstance(resources, dict) or set(resources) != {
            "applications",
            "policy",
            "capacity",
            "conditions",
            "documents",
            "authority_registry",
        }:
            raise ValueError("frontier_scenario_resources_invalid")
        parsed_resources: dict[str, dict[str, Any]] = {}
        for resource_id, record in resources.items():
            if not isinstance(record, dict):
                raise ValueError("frontier_resource_record_invalid")
            if not isinstance(record.get("source_id"), str) or not isinstance(
                record.get("version"), int
            ):
                raise ValueError("frontier_resource_identity_invalid")
            parsed_resources[resource_id] = deepcopy(record)
        if not isinstance(events, list):
            raise ValueError("frontier_scenario_events_required")
        parsed_events = tuple(
            FrontierEvent.parse(row, set(parsed_resources))
            for row in events
            if isinstance(row, dict)
        )
        if len(parsed_events) != len(events):
            raise ValueError("frontier_scenario_event_object_required")
        ids = [row.event_id for row in parsed_events]
        if len(ids) != len(set(ids)):
            raise ValueError("frontier_scenario_event_ids_not_unique")
        if value.get("synthetic") is not True:
            raise ValueError("frontier_scenario_must_be_synthetic")
        scenario = cls(scenario_id, title, parsed_resources, parsed_events, True)
        _validate_frontier_semantics(scenario)
        return scenario


@dataclass(frozen=True)
class FrontierOccurrence:
    event_id: str
    event_sha256: str
    boundary_act: int
    boundary_tool: str
    before_world_root: str
    after_world_root: str
    visible_projection: dict[str, str]
    visible_projection_sha256: str
    restore_generation: int
    previous_occurrence_sha256: str | None
    occurrence_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_sha256": self.event_sha256,
            "boundary_act": self.boundary_act,
            "boundary_tool": self.boundary_tool,
            "before_world_root": self.before_world_root,
            "after_world_root": self.after_world_root,
            "visible_projection": self.visible_projection,
            "visible_projection_sha256": self.visible_projection_sha256,
            "restore_generation": self.restore_generation,
            "previous_occurrence_sha256": self.previous_occurrence_sha256,
            "occurrence_sha256": self.occurrence_sha256,
        }


class FrontierWorld:
    def __init__(self, scenario: FrontierScenario) -> None:
        self.resources = deepcopy(scenario.resources)
        self.inbox: list[dict[str, str]] = []
        self.restore_generation = 0

    @property
    def root(self) -> str:
        return digest(self.resources)

    def snapshot(self) -> dict[str, Any]:
        return {
            "resources": deepcopy(self.resources),
            "inbox": deepcopy(self.inbox),
            "restore_generation": self.restore_generation,
        }

    @classmethod
    def restore(cls, scenario: FrontierScenario, snapshot: dict[str, Any]) -> FrontierWorld:
        world = cls(scenario)
        world.resources = deepcopy(snapshot["resources"])
        world.inbox = deepcopy(snapshot["inbox"])
        world.restore_generation = int(snapshot["restore_generation"]) + 1
        return world

    def apply(self, event: FrontierEvent) -> tuple[str, str, dict[str, str]]:
        before = self.root
        for patch in event.patches:
            target: Any = self.resources[patch.resource_id]
            for part in patch.path[:-1]:
                target = target[part]
            target[patch.path[-1]] = deepcopy(patch.value)
        projection = event.observation.public_view(event.event_id)
        self.inbox.append(projection)
        return before, self.root, projection


class FrontierEngine:
    def __init__(self, scenario: FrontierScenario) -> None:
        self.scenario = scenario
        self.applied_ids: set[str] = set()
        self.occurrences: list[FrontierOccurrence] = []
        self.tool_counts: Counter[str] = Counter()

    def advance(
        self, act_index: int, tool: str, world: FrontierWorld
    ) -> list[FrontierOccurrence]:
        self.tool_counts[tool] += 1
        fired: list[FrontierOccurrence] = []
        for event in self.scenario.events:
            if event.event_id in self.applied_ids:
                continue
            trigger = event.trigger
            matches = (
                trigger.kind == "after_act" and trigger.act_index == act_index
            ) or (
                trigger.kind == "after_tool"
                and trigger.tool == tool
                and trigger.occurrence == self.tool_counts[tool]
            )
            if not matches:
                continue
            before, after, projection = world.apply(event)
            previous = self.occurrences[-1].occurrence_sha256 if self.occurrences else None
            body: dict[str, Any] = {
                "event_id": event.event_id,
                "event_sha256": digest(event.private_contract()),
                "boundary_act": act_index,
                "boundary_tool": tool,
                "before_world_root": before,
                "after_world_root": after,
                "visible_projection_sha256": digest(projection),
                "restore_generation": world.restore_generation,
                "previous_occurrence_sha256": previous,
            }
            occurrence = FrontierOccurrence(
                **body,
                visible_projection=projection,
                occurrence_sha256=digest(body),
            )
            self.applied_ids.add(event.event_id)
            self.occurrences.append(occurrence)
            fired.append(occurrence)
        return fired

    def snapshot(self) -> dict[str, Any]:
        return {
            "applied_ids": sorted(self.applied_ids),
            "occurrences": [row.as_dict() for row in self.occurrences],
            "tool_counts": dict(self.tool_counts),
        }

    @classmethod
    def restore(
        cls, scenario: FrontierScenario, snapshot: dict[str, Any]
    ) -> FrontierEngine:
        engine = cls(scenario)
        engine.applied_ids = set(snapshot["applied_ids"])
        engine.occurrences = [FrontierOccurrence(**row) for row in snapshot["occurrences"]]
        engine.tool_counts = Counter(snapshot["tool_counts"])
        engine.verify_chain()
        return engine

    def verify_chain(self) -> None:
        previous: str | None = None
        seen: set[str] = set()
        for row in self.occurrences:
            if row.event_id in seen:
                raise ValueError("frontier_duplicate_occurrence")
            body = {
                "event_id": row.event_id,
                "event_sha256": row.event_sha256,
                "boundary_act": row.boundary_act,
                "boundary_tool": row.boundary_tool,
                "before_world_root": row.before_world_root,
                "after_world_root": row.after_world_root,
                "visible_projection_sha256": row.visible_projection_sha256,
                "restore_generation": row.restore_generation,
                "previous_occurrence_sha256": row.previous_occurrence_sha256,
            }
            if row.previous_occurrence_sha256 != previous:
                raise ValueError("frontier_occurrence_previous_mismatch")
            if digest(row.visible_projection) != row.visible_projection_sha256:
                raise ValueError("frontier_occurrence_projection_mismatch")
            if digest(body) != row.occurrence_sha256:
                raise ValueError("frontier_occurrence_digest_mismatch")
            previous = row.occurrence_sha256
            seen.add(row.event_id)


class FrontierBackend(Protocol):
    provider: str
    model: str
    adapter_version: str

    def complete(self, prompt: str) -> Any: ...


def load_frontier_scenarios(fixtures_dir: Path) -> list[FrontierScenario]:
    directory = fixtures_dir / "frontier"
    base = load_json(directory / "base-resources.json")
    if set(base) != {"schema", "resources"} or base.get("schema") != (
        "gradia-frontier-universe-resources.v1"
    ):
        raise ValueError("frontier_base_resources_invalid")
    resources = base.get("resources")
    if not isinstance(resources, dict):
        raise ValueError("frontier_base_resources_missing")
    base_sha256 = digest(base)
    paths = sorted(directory.glob("[0-9][0-9]_*.json"))
    if not paths:
        raise ValueError("no_frontier_scenarios_found")
    rows: list[FrontierScenario] = []
    for path in paths:
        raw = load_json(path)
        _exact_keys(
            raw,
            {
                "schema",
                "scenario_id",
                "title",
                "base_resources_sha256",
                "events",
                "synthetic",
            },
            "frontier_scenario_file",
        )
        if raw.get("base_resources_sha256") != base_sha256:
            raise ValueError(f"frontier_base_resources_digest_mismatch:{path.name}")
        rows.append(
            FrontierScenario.parse(
                {
                    "schema": raw.get("schema"),
                    "scenario_id": raw.get("scenario_id"),
                    "title": raw.get("title"),
                    "resources": resources,
                    "events": raw.get("events"),
                    "synthetic": raw.get("synthetic"),
                }
            )
        )
    ids = [row.scenario_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("frontier_scenario_ids_not_unique")
    return rows


def _record_ref(record: dict[str, Any]) -> str:
    return f"{record['source_id']}@{record['version']}"


def _applications(world: FrontierWorld) -> list[dict[str, Any]]:
    rows = world.resources["applications"].get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("frontier_applications_missing")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("frontier_application_invalid")
    return cast(list[dict[str, Any]], rows)


def calculate_metrics(world: FrontierWorld, case_id: str) -> dict[str, float | str]:
    matches = [row for row in _applications(world) if row.get("case_id") == case_id]
    if len(matches) != 1:
        raise ValueError("frontier_case_unknown")
    row = matches[0]
    income = float(row["verified_monthly_income"])
    if income <= 0 or float(row["collateral_value"]) <= 0:
        raise ValueError("frontier_metric_denominator_invalid")
    return {
        "case_id": case_id,
        "dti": round(float(row["monthly_debt"]) / income, 6),
        "ltv": round(float(row["requested_principal"]) / float(row["collateral_value"]), 6),
        "reserve_months": round(float(row["liquid_reserves"]) / income, 6),
    }


def oracle_packet(world: FrontierWorld) -> dict[str, Any]:
    policy = world.resources["policy"]
    capacity = world.resources["capacity"]
    condition_rows = cast(list[dict[str, Any]], world.resources["conditions"]["records"])
    document_rows = cast(list[dict[str, Any]], world.resources["documents"]["records"])
    baseline = cast(dict[str, Any], policy["baseline"])
    exception = cast(dict[str, Any], policy["exception"])
    provisional: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    for application in _applications(world):
        case_id = cast(str, application["case_id"])
        metrics = calculate_metrics(world, case_id)
        outcome: Outcome
        reasons: list[str]
        has_current_income_document = any(
            row.get("case_id") == case_id
            and row.get("document_kind") == "income_verification"
            and row.get("status") == "verified"
            for row in document_rows
        )
        has_open_approval_condition = any(
            row.get("case_id") == case_id
            and row.get("prior_to") == "approval"
            and row.get("status") == "open"
            for row in condition_rows
        )
        if bool(application["fraud_hold"]):
            outcome, reasons = "DENY", ["FRAUD_HOLD"]
        elif application["income_status"] != "verified" or not has_current_income_document:
            outcome, reasons = "ESCALATE", ["EVIDENCE_NOT_CURRENT"]
        elif has_open_approval_condition:
            outcome, reasons = "ESCALATE", ["OPEN_APPROVAL_CONDITION"]
        elif float(metrics["ltv"]) > float(baseline["hard_max_ltv"]):
            outcome, reasons = "DENY", ["HARD_LTV_LIMIT"]
        elif (
            float(metrics["dti"]) <= float(baseline["max_dti"])
            and float(metrics["ltv"]) <= float(baseline["max_ltv"])
            and float(metrics["reserve_months"]) >= float(baseline["min_reserve_months"])
        ):
            outcome, reasons = "APPROVE", ["BASELINE_ELIGIBLE"]
        elif (
            float(metrics["dti"]) <= float(exception["max_dti"])
            and float(metrics["ltv"]) <= float(exception["max_ltv"])
            and float(metrics["reserve_months"])
            >= float(exception["min_reserve_months"])
        ):
            outcome, reasons = "DENY", ["EXCEPTION_CAPACITY_EXHAUSTED"]
            candidates.append(application)
        else:
            outcome, reasons = "DENY", ["POLICY_LIMIT"]
        provisional[case_id] = {
            "case_id": case_id,
            "outcome": outcome,
            "dti": metrics["dti"],
            "ltv": metrics["ltv"],
            "reserve_months": metrics["reserve_months"],
            "reason_codes": reasons,
        }
    slots = int(capacity["available_exception_slots"])
    ranked = sorted(
        candidates,
        key=lambda row: (
            -int(row["exception_priority"]),
            int(row["submitted_at"]),
            str(row["case_id"]),
        ),
    )
    awarded = [cast(str, row["case_id"]) for row in ranked[: max(0, slots)]]
    for case_id in awarded:
        provisional[case_id]["outcome"] = "APPROVE_EXCEPTION"
        provisional[case_id]["reason_codes"] = ["EXCEPTION_ALLOCATED"]
    decisions = [provisional[key] for key in sorted(provisional)]
    return {
        "decisions": decisions,
        "exception_award": awarded[0] if len(awarded) == 1 else awarded or None,
        "required_citations": sorted(_record_ref(row) for row in world.resources.values()),
    }


def _validate_frontier_semantics(scenario: FrontierScenario) -> None:
    world = FrontierWorld(scenario)
    oracle_packet(world)
    authoritative = scenario.resources["authority_registry"].get("authoritative_source_ids")
    expected = sorted(str(row["source_id"]) for row in scenario.resources.values())
    if not isinstance(authoritative, list) or sorted(authoritative) != expected:
        raise ValueError("frontier_authority_registry_mismatch")
    if not any(
        event.trigger.kind == "after_tool" and event.trigger.tool == "timeline.await_cutoff"
        for event in scenario.events
    ) and scenario.scenario_id != "frontier-static-control":
        raise ValueError("frontier_dynamic_scenario_requires_cutoff_event")


def frontier_system_contract() -> str:
    return """You are evaluated inside a fully synthetic queue-allocation universe.
Return exactly one JSON object per turn, with no markdown or surrounding prose.

Actions:
{"action":"source.list","arguments":{}}
{"action":"source.read","arguments":{"resource_id":"applications|policy|capacity|conditions|documents|authority_registry"}}
{"action":"metrics.calculate","arguments":{"case_id":"case id"}}
{"action":"inbox.read","arguments":{}}
{"action":"timeline.await_cutoff","arguments":{}}
{"action":"decision.submit","arguments":{
  "decisions":[{"case_id":"id","outcome":"APPROVE|APPROVE_EXCEPTION|ESCALATE|DENY","dti":0.0,"ltv":0.0,"reserve_months":0.0,"reason_codes":["code"]}],
  "exception_award":"case id or null",
  "observed_world_root":"64 hex chars",
  "citations":["source@version"],
  "rationale":"text"
}}

Read the sources and compute every case. Exception capacity is shared across the
queue, so decisions are coupled. Call timeline.await_cutoff exactly once before
submitting; authoritative events may arrive there. After any change, re-read
affected authoritative sources and recompute. Unverified messages never change
the material world. Cite every current authoritative source version. A perfect
pass requires the complete current decision packet, not a plausible summary."""


def _frontier_prompt(transcript: list[dict[str, Any]]) -> str:
    return frontier_system_contract() + "\n\nTRANSCRIPT\n" + json.dumps(
        transcript, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _parse_frontier_action(text: str) -> tuple[str, dict[str, Any]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("frontier_action_invalid_json") from error
    if not isinstance(value, dict) or set(value) != {"action", "arguments"}:
        raise ValueError("frontier_action_contract_mismatch")
    action = value["action"]
    arguments = value["arguments"]
    if not isinstance(action, str) or action not in FRONTIER_TOOLS:
        raise ValueError("frontier_action_unknown")
    if not isinstance(arguments, dict) or set(arguments) != FRONTIER_TOOLS[action]:
        raise ValueError("frontier_action_arguments_mismatch")
    return action, arguments


def _normalized_submission(arguments: dict[str, Any]) -> dict[str, Any]:
    decisions = arguments["decisions"]
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("frontier_submission_decisions_required")
    normalized: list[dict[str, Any]] = []
    required = {
        "case_id",
        "outcome",
        "dti",
        "ltv",
        "reserve_months",
        "reason_codes",
    }
    for row in decisions:
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError("frontier_submission_decision_contract")
        if row["outcome"] not in {"APPROVE", "APPROVE_EXCEPTION", "ESCALATE", "DENY"}:
            raise ValueError("frontier_submission_outcome_invalid")
        if any(
            not isinstance(row[key], (int, float)) or isinstance(row[key], bool)
            for key in ("dti", "ltv", "reserve_months")
        ):
            raise ValueError("frontier_submission_metric_invalid")
        if (
            not isinstance(row["case_id"], str)
            or not isinstance(row["reason_codes"], list)
            or not row["reason_codes"]
            or any(not isinstance(code, str) for code in row["reason_codes"])
        ):
            raise ValueError("frontier_submission_decision_invalid")
        normalized.append(deepcopy(row))
    citations = arguments["citations"]
    root = arguments["observed_world_root"]
    rationale = arguments["rationale"]
    award = arguments["exception_award"]
    if award is not None and not isinstance(award, (str, list)):
        raise ValueError("frontier_submission_award_invalid")
    if not isinstance(root, str) or len(root) != 64:
        raise ValueError("frontier_submission_root_invalid")
    if (
        not isinstance(citations, list)
        or not citations
        or any(not isinstance(row, str) for row in citations)
    ):
        raise ValueError("frontier_submission_citations_invalid")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("frontier_submission_rationale_required")
    return {
        "decisions": sorted(normalized, key=lambda row: row["case_id"]),
        "exception_award": deepcopy(award),
        "observed_world_root": root,
        "citations": sorted(set(citations)),
        "rationale": rationale,
    }


def judge_frontier(
    submission: dict[str, Any],
    world: FrontierWorld,
    scenario: FrontierScenario,
    *,
    cutoff_observed: bool,
    occurrences: list[FrontierOccurrence],
    acts: list[dict[str, Any]],
) -> dict[str, Any]:
    expected = oracle_packet(world)
    submitted_citations = set(submission["citations"])
    required_citations = set(expected["required_citations"])
    current_sources = {str(row["source_id"]) for row in world.resources.values()}
    authority_violation = any(
        citation.partition("@")[0] not in current_sources for citation in submitted_citations
    )
    observed_refs = {
        _record_ref(record)
        for act in acts
        if act.get("tool") == "source.read"
        and isinstance(act.get("result"), dict)
        and isinstance((record := act["result"].get("record")), dict)
        and isinstance(record.get("source_id"), str)
        and isinstance(record.get("version"), int)
    }
    decisions_match = submission["decisions"] == expected["decisions"]
    criteria = {
        "complete_decision_packet": decisions_match,
        "exception_allocation_correct": submission["exception_award"]
        == expected["exception_award"],
        "current_world_root": submission["observed_world_root"] == world.root,
        "current_authoritative_evidence": required_citations.issubset(submitted_citations)
        and required_citations.issubset(observed_refs)
        and not authority_violation,
        "cutoff_observed": cutoff_observed,
        "changed_world_adaptation": all(
            {
                str(act["result"].get("resource_id"))
                for act in acts
                if int(act["act_index"]) > occurrence.boundary_act
                and act["tool"] == "source.read"
                and isinstance(act.get("result"), dict)
            }.issuperset({
                patch.resource_id
                for event in scenario.events
                if event.event_id == occurrence.event_id
                for patch in event.patches
            })
            for occurrence in occurrences
            if occurrence.before_world_root != occurrence.after_world_root
        ),
        "output_contract": bool(submission["rationale"].strip()),
    }
    failures: list[str] = []
    mapping = {
        "complete_decision_packet": "decision_packet_error",
        "exception_allocation_correct": "capacity_allocation_error",
        "current_world_root": "stale_world_state",
        "current_authoritative_evidence": "evidence_gap",
        "cutoff_observed": "premature_submission",
        "changed_world_adaptation": "missed_world_change",
        "output_contract": "output_contract_error",
    }
    for criterion, failure in mapping.items():
        if not criteria[criterion]:
            failures.append(failure)
    if authority_violation:
        failures.insert(0, "authority_violation")
    passed = all(criteria.values())
    return {
        "judge": FRONTIER_JUDGE_VERSION,
        "expected_packet_sha256": digest(expected),
        "criteria": criteria,
        "rubric_score": sum(criteria.values()) / len(criteria),
        "passed": passed,
        "failure_classes": failures,
        "environment_failure": False,
    }


def run_frontier_live_episode(
    scenario: FrontierScenario,
    backend: CompletionBackend,
    *,
    attempt_id: int,
    max_model_turns: int = 32,
    max_acts: int = 28,
) -> dict[str, Any]:
    if not 1 <= attempt_id <= 10_000:
        raise ValueError("frontier_attempt_id_invalid")
    if not 1 <= max_model_turns <= 64 or not 1 <= max_acts <= 48:
        raise ValueError("frontier_limits_invalid")
    world = FrontierWorld(scenario)
    engine = FrontierEngine(scenario)
    transcript: list[dict[str, Any]] = [{
        "kind": "task",
        "text": (
            "Resolve the complete synthetic queue under the current sources and shared "
            "exception capacity. Await the cutoff exactly once before final submission."
        ),
    }]
    acts: list[dict[str, Any]] = []
    model_calls: list[dict[str, Any]] = []
    restore_receipts: list[dict[str, Any]] = []
    submission: dict[str, Any] | None = None
    cutoff_observed = False
    backend_stop: CompletionBackendStop | None = None
    for model_turn in range(1, max_model_turns + 1):
        prompt = _frontier_prompt(transcript)
        try:
            completion = backend.complete(prompt)
        except CompletionBackendStop as error:
            backend_stop = error
            break
        model_calls.append({
            "model_turn": model_turn,
            "prompt_sha256": digest(prompt),
            "provider": completion.provider,
            "model": completion.model,
            "adapter_version": completion.adapter_version,
            "response_id": completion.response_id,
            "output_text": completion.output_text,
            "output_text_sha256": digest(completion.output_text),
            "input_tokens": completion.input_tokens,
            "output_tokens": completion.output_tokens,
            "provider_response_sha256": completion.provider_response_sha256,
            "estimated_cost_usd": completion.estimated_cost_usd,
            "cumulative_estimated_cost_usd": completion.cumulative_estimated_cost_usd,
            "budget_policy_sha256": completion.budget_policy_sha256,
        })
        transcript.append(
            {
                "kind": "model_output",
                "model_turn": model_turn,
                "text": completion.output_text,
            }
        )
        try:
            action, arguments = _parse_frontier_action(completion.output_text)
        except ValueError as error:
            transcript.append({
                "kind": "protocol_error",
                "code": str(error),
                "instruction": "Return exactly one valid JSON action object.",
            })
            continue
        if len(acts) >= max_acts:
            break
        act_index = len(acts) + 1
        try:
            if action == "source.list":
                result: dict[str, Any] = {
                    "resources": sorted(world.resources),
                    "world_root": world.root,
                }
            elif action == "source.read":
                resource_id = arguments["resource_id"]
                if not isinstance(resource_id, str) or resource_id not in world.resources:
                    raise ValueError("frontier_resource_unknown")
                result = {
                    "resource_id": resource_id,
                    "record": deepcopy(world.resources[resource_id]),
                    "world_root": world.root,
                }
            elif action == "metrics.calculate":
                case_id = arguments["case_id"]
                if not isinstance(case_id, str):
                    raise ValueError("frontier_case_id_invalid")
                result = {**calculate_metrics(world, case_id), "world_root": world.root}
            elif action == "inbox.read":
                result = {"messages": deepcopy(world.inbox)}
            elif action == "timeline.await_cutoff":
                if cutoff_observed:
                    raise ValueError("frontier_cutoff_already_observed")
                cutoff_observed = True
                result = {"cutoff_observed": True, "world_root": world.root}
            else:
                submission = _normalized_submission(arguments)
                result = {"accepted": True}
        except ValueError as error:
            transcript.append({"kind": "tool_error", "code": str(error), "tool": action})
            continue
        acts.append({
            "act_index": act_index,
            "tool": action,
            "arguments": deepcopy(arguments),
            "result": result,
            "world_root_after_act": world.root,
            "restore_generation": world.restore_generation,
        })
        transcript.append({
            "kind": "tool_result",
            "act_index": act_index,
            "tool": action,
            "result": result,
        })
        fired = engine.advance(act_index, action, world)
        for occurrence in fired:
            transcript.append({
                "kind": "environment_event",
                "after_act": act_index,
                "visible_projection": occurrence.visible_projection,
            })
            event = next(row for row in scenario.events if row.event_id == occurrence.event_id)
            if event.restore_after:
                before_generation = world.restore_generation
                before_root = world.root
                chain_head = engine.occurrences[-1].occurrence_sha256
                world = FrontierWorld.restore(scenario, world.snapshot())
                engine = FrontierEngine.restore(scenario, engine.snapshot())
                if world.root != before_root:
                    raise ValueError("frontier_restore_world_root_mismatch")
                receipt_body = {
                    "event_id": event.event_id,
                    "before_generation": before_generation,
                    "after_generation": world.restore_generation,
                    "world_root": world.root,
                    "occurrence_chain_head": chain_head,
                }
                restore_receipts.append(
                    {**receipt_body, "receipt_sha256": digest(receipt_body)}
                )
                transcript.append({
                    "kind": "environment_restore",
                    "restore_generation": world.restore_generation,
                    "world_root": world.root,
                })
        if submission is not None:
            break
    if submission is None:
        environment_failure = bool(backend_stop and backend_stop.environment_failure)
        failure = "environment_failure" if environment_failure else (
            "budget_stop" if backend_stop else "no_valid_submission"
        )
        verdict: dict[str, Any] = {
            "judge": FRONTIER_JUDGE_VERSION,
            "criteria": {},
            "rubric_score": 0.0,
            "passed": False,
            "failure_classes": [failure],
            "environment_failure": environment_failure,
        }
        stop_reason = str(backend_stop) if backend_stop else "model_turn_limit"
    else:
        verdict = judge_frontier(
            submission,
            world,
            scenario,
            cutoff_observed=cutoff_observed,
            occurrences=engine.occurrences,
            acts=acts,
        )
        stop_reason = "submitted"
    engine.verify_chain()
    scenario_contract = {
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "resources": scenario.resources,
        "events": [row.private_contract() for row in scenario.events],
        "synthetic": scenario.synthetic,
    }
    body = {
        "schema": "gradia-frontier-live-model-receipt.v1",
        "scenario_id": scenario.scenario_id,
        "scenario_sha256": digest(scenario_contract),
        "provider": backend.provider,
        "model": backend.model,
        "adapter_version": backend.adapter_version,
        "scaffold": FRONTIER_SCAFFOLD_VERSION,
        "scaffold_sha256": digest(frontier_system_contract()),
        "attempt_id": attempt_id,
        "sampling_evidence": {
            "attempt_id_is_not_a_provider_seed": True,
            "sampling_distribution": "provider request policy pinned by the panel receipt",
        },
        "limits": {"max_model_turns": max_model_turns, "max_acts": max_acts},
        "stop_reason": stop_reason,
        "model_calls": model_calls,
        "acts": acts,
        "evolution_witness": [row.as_dict() for row in engine.occurrences],
        "restore_receipts": restore_receipts,
        "terminal_world_root": world.root,
        "submission": submission,
        "verdict": verdict,
    }
    return {**body, "receipt_sha256": digest(body)}


def _frontier_admission_state(
    scenario: FrontierScenario,
) -> tuple[FrontierWorld, FrontierEngine, int]:
    world = FrontierWorld(scenario)
    engine = FrontierEngine(scenario)
    # Exercise all declared boundaries deterministically without pretending
    # this is an agent rollout.
    for act_index in range(1, 4):
        engine.advance(act_index, "source.read", world)
    fired = engine.advance(4, "timeline.await_cutoff", world)
    restores = 0
    for occurrence in fired:
        event = next(row for row in scenario.events if row.event_id == occurrence.event_id)
        if event.restore_after:
            world = FrontierWorld.restore(scenario, world.snapshot())
            engine = FrontierEngine.restore(scenario, engine.snapshot())
            restores += 1
    return world, engine, restores


def frontier_admission_report(fixtures_dir: Path) -> dict[str, Any]:
    rows = load_frontier_scenarios(fixtures_dir)
    scenarios: list[dict[str, Any]] = []
    for scenario in rows:
        initial = oracle_packet(FrontierWorld(scenario))
        world, engine, restores = _frontier_admission_state(scenario)
        terminal = oracle_packet(world)
        scenarios.append({
            "scenario_id": scenario.scenario_id,
            "scenario_sha256": digest({
                "scenario_id": scenario.scenario_id,
                "title": scenario.title,
                "resources": scenario.resources,
                "events": [row.private_contract() for row in scenario.events],
                "synthetic": True,
            }),
            "event_count": len(scenario.events),
            "root_changing_event_count": sum(
                1 for row in engine.occurrences if row.before_world_root != row.after_world_root
            ),
            "restore_count": restores,
            "initial_oracle_sha256": digest(initial),
            "terminal_oracle_sha256": digest(terminal),
            "answer_changed": initial != terminal,
            "terminal_world_root": world.root,
        })
    body = {
        "schema": "gradia-frontier-admission-report.v1",
        "claim_boundary": (
            "Solvability and deterministic-oracle admission only; no live-model difficulty "
            "or real underwriting validity is measured."
        ),
        "scenario_count": len(rows),
        "scenarios": scenarios,
    }
    return {**body, "report_sha256": digest(body)}


def frontier_judge_validation_report(fixtures_dir: Path) -> dict[str, Any]:
    """Prove criterion sensitivity with positive and isolated negative controls."""
    scenario_rows: list[dict[str, Any]] = []
    for scenario in load_frontier_scenarios(fixtures_dir):
        world, engine, _restores = _frontier_admission_state(scenario)
        expected = oracle_packet(world)
        positive = {
            "decisions": expected["decisions"],
            "exception_award": expected["exception_award"],
            "observed_world_root": world.root,
            "citations": expected["required_citations"],
            "rationale": "Deterministic positive control.",
        }
        post_change_acts: list[dict[str, Any]] = [
            {
                "act_index": 5 + index,
                "tool": "source.read",
                "result": {
                    "resource_id": resource_id,
                    "record": deepcopy(record),
                },
            }
            for index, (resource_id, record) in enumerate(
                sorted(world.resources.items())
            )
        ]
        positive_verdict = judge_frontier(
            positive,
            world,
            scenario,
            cutoff_observed=True,
            occurrences=engine.occurrences,
            acts=post_change_acts,
        )
        mutations: list[tuple[str, dict[str, Any], bool, list[dict[str, Any]], set[str]]] = []
        wrong_decision = deepcopy(positive)
        current_outcome = wrong_decision["decisions"][0]["outcome"]
        wrong_decision["decisions"][0]["outcome"] = (
            "APPROVE" if current_outcome != "APPROVE" else "DENY"
        )
        mutations.append((
            "wrong_decision_packet",
            wrong_decision,
            True,
            post_change_acts,
            {"complete_decision_packet"},
        ))
        wrong_award = deepcopy(positive)
        wrong_award["exception_award"] = "NOT-A-CASE"
        mutations.append((
            "wrong_capacity_award",
            wrong_award,
            True,
            post_change_acts,
            {"exception_allocation_correct"},
        ))
        stale_root = deepcopy(positive)
        stale_root["observed_world_root"] = "0" * 64
        mutations.append((
            "stale_world_root",
            stale_root,
            True,
            post_change_acts,
            {"current_world_root"},
        ))
        missing_citation = deepcopy(positive)
        missing_citation["citations"] = missing_citation["citations"][1:]
        mutations.append((
            "missing_current_citation",
            missing_citation,
            True,
            post_change_acts,
            {"current_authoritative_evidence"},
        ))
        citation_without_access = [
            act
            for act in post_change_acts
            if act["result"]["resource_id"] != "authority_registry"
        ]
        mutations.append((
            "citation_without_source_access",
            deepcopy(positive),
            True,
            citation_without_access,
            {"current_authoritative_evidence"},
        ))
        mutations.append((
            "premature_submission",
            deepcopy(positive),
            False,
            post_change_acts,
            {"cutoff_observed"},
        ))
        empty_rationale = deepcopy(positive)
        empty_rationale["rationale"] = ""
        mutations.append((
            "empty_rationale",
            empty_rationale,
            True,
            post_change_acts,
            {"output_contract"},
        ))
        rogue_authority = deepcopy(positive)
        rogue_authority["citations"] = [*rogue_authority["citations"], "rogue@1"]
        mutations.append((
            "undeclared_authority",
            rogue_authority,
            True,
            post_change_acts,
            {"current_authoritative_evidence"},
        ))
        if any(
            row.before_world_root != row.after_world_root for row in engine.occurrences
        ):
            no_recheck_acts = [
                {**deepcopy(act), "act_index": 1}
                for act in post_change_acts
            ]
            mutations.append((
                "no_post_change_recheck",
                deepcopy(positive),
                True,
                no_recheck_acts,
                {"changed_world_adaptation"},
            ))
        probe_rows: list[dict[str, Any]] = []
        for probe_id, submission, cutoff, acts, expected_failures in mutations:
            verdict = judge_frontier(
                submission,
                world,
                scenario,
                cutoff_observed=cutoff,
                occurrences=engine.occurrences,
                acts=acts,
            )
            failed = {
                criterion
                for criterion, passed in verdict["criteria"].items()
                if not passed
            }
            probe_rows.append({
                "probe_id": probe_id,
                "expected_failed_criteria": sorted(expected_failures),
                "observed_failed_criteria": sorted(failed),
                "isolated_detection_passed": failed == expected_failures,
                "failure_classes": verdict["failure_classes"],
            })
        scenario_rows.append({
            "scenario_id": scenario.scenario_id,
            "positive_control_passed": positive_verdict["passed"],
            "probe_count": len(probe_rows),
            "all_isolated_detection_probes_passed": all(
                row["isolated_detection_passed"] for row in probe_rows
            ),
            "probes": probe_rows,
        })
    body = {
        "schema": "gradia-frontier-judge-validation.v1",
        "claim_boundary": (
            "Deterministic criterion sensitivity only. Human agreement, domain validity, "
            "and live-model grading fairness remain empirical gates."
        ),
        "judge": FRONTIER_JUDGE_VERSION,
        "scenario_count": len(scenario_rows),
        "positive_controls_passed": all(
            row["positive_control_passed"] for row in scenario_rows
        ),
        "isolated_detection_passed": all(
            row["all_isolated_detection_probes_passed"] for row in scenario_rows
        ),
        "scenarios": scenario_rows,
    }
    return {**body, "report_sha256": digest(body)}


def _wilson(successes: int, total: int) -> list[float] | None:
    if total <= 0:
        return None
    z = 1.959963984540054
    phat = successes / total
    denominator = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        (phat * (1 - phat) + z * z / (4 * total)) / total
    ) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def analyze_five_attempt_panel(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    if not receipts:
        raise ValueError("frontier_analysis_receipts_required")
    scenario_ids = sorted({str(row["scenario_id"]) for row in receipts})
    task_rows: list[dict[str, Any]] = []
    all_eligible: list[dict[str, Any]] = []
    for scenario_id in scenario_ids:
        cells = [row for row in receipts if row["scenario_id"] == scenario_id]
        attempt_ids = [row["attempt_id"] for row in cells]
        if sorted(attempt_ids) != [1, 2, 3, 4, 5]:
            raise ValueError(f"frontier_analysis_requires_attempts_1_to_5:{scenario_id}")
        eligible = [
            row for row in cells
            if not row["verdict"]["environment_failure"]
            and row["verdict"]["failure_classes"] != ["budget_stop"]
        ]
        all_eligible.extend(eligible)
        successes = sum(bool(row["verdict"]["passed"]) for row in eligible)
        signatures = Counter(
            "PASS" if row["verdict"]["passed"] else "+".join(row["verdict"]["failure_classes"])
            for row in eligible
        )
        if successes == 0:
            classification = "stable_failure_observed"
        elif successes == len(eligible) == 5:
            classification = "stable_pass_observed"
        else:
            classification = "inconsistent_observed"
        task_rows.append({
            "scenario_id": scenario_id,
            "attempts": 5,
            "eligible_attempts": len(eligible),
            "successes": successes,
            "empirical_pass_fraction": successes / len(eligible) if eligible else None,
            "wilson_95_descriptive": _wilson(successes, len(eligible)),
            "any_pass_at_5": successes > 0 if len(eligible) == 5 else None,
            "all_pass_at_5": successes == 5 if len(eligible) == 5 else None,
            "classification": classification,
            "outcome_signatures": dict(sorted(signatures.items())),
        })
    successes = sum(bool(row["verdict"]["passed"]) for row in all_eligible)
    complete_tasks = [row for row in task_rows if row["eligible_attempts"] == 5]
    body = {
        "schema": "gradia-frontier-five-attempt-analysis.v1",
        "estimand_boundary": (
            "Attempt ids denote repeated provider requests, not provider random seeds. "
            "Any-pass@5 measures observed capability coverage; all-pass@5 measures "
            "observed reliability. Neither alone identifies an inherent model capability."
        ),
        "task_count": len(task_rows),
        "eligible_attempts": len(all_eligible),
        "successes": successes,
        "empirical_pass_fraction": successes / len(all_eligible) if all_eligible else None,
        "task_coverage_any_pass_at_5": (
            sum(bool(row["any_pass_at_5"]) for row in complete_tasks) / len(complete_tasks)
            if complete_tasks else None
        ),
        "task_reliability_all_pass_at_5": (
            sum(bool(row["all_pass_at_5"]) for row in complete_tasks) / len(complete_tasks)
            if complete_tasks else None
        ),
        "tasks": task_rows,
    }
    return {**body, "analysis_sha256": digest(body)}
