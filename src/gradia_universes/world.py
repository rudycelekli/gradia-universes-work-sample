"""Root-owned mutable world and tamper-evident occurrence chain."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .canonical import digest
from .contracts import Event, Scenario


@dataclass(frozen=True)
class AppliedEvent:
    event_id: str
    event_sha256: str
    boundary_act: int
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
            "before_world_root": self.before_world_root,
            "after_world_root": self.after_world_root,
            "visible_projection": self.visible_projection,
            "visible_projection_sha256": self.visible_projection_sha256,
            "restore_generation": self.restore_generation,
            "previous_occurrence_sha256": self.previous_occurrence_sha256,
            "occurrence_sha256": self.occurrence_sha256,
        }


class World:
    def __init__(self, scenario: Scenario) -> None:
        self.case = deepcopy(scenario.case)
        self.policy = deepcopy(scenario.policy)
        self.inbox: list[dict[str, str]] = []
        self.restore_generation = 0

    @property
    def root(self) -> str:
        return digest({"case": self.case, "policy": self.policy})

    def snapshot(self) -> dict[str, Any]:
        return {
            "case": deepcopy(self.case),
            "policy": deepcopy(self.policy),
            "inbox": deepcopy(self.inbox),
            "restore_generation": self.restore_generation,
        }

    @classmethod
    def restore(cls, scenario: Scenario, snapshot: dict[str, Any]) -> World:
        world = cls(scenario)
        world.case = deepcopy(snapshot["case"])
        world.policy = deepcopy(snapshot["policy"])
        world.inbox = deepcopy(snapshot["inbox"])
        world.restore_generation = int(snapshot["restore_generation"]) + 1
        return world

    def apply(self, event: Event) -> tuple[str, str, dict[str, str]]:
        before = self.root
        if event.target == "case":
            self.case.update(deepcopy(event.updates))
        elif event.target == "policy":
            self.policy.update(deepcopy(event.updates))
        projection = event.observation.public_view(event.event_id)
        self.inbox.append(projection)
        return before, self.root, projection


class ScenarioEngine:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.applied_ids: set[str] = set()
        self.occurrences: list[AppliedEvent] = []

    def advance(self, act_index: int, world: World) -> list[AppliedEvent]:
        fired: list[AppliedEvent] = []
        for event in self.scenario.events:
            if event.event_id in self.applied_ids or event.after_act != act_index:
                continue
            before, after, projection = world.apply(event)
            event_sha = digest(event.private_contract())
            projection_sha = digest(projection)
            previous = self.occurrences[-1].occurrence_sha256 if self.occurrences else None
            body: dict[str, Any] = {
                "event_id": event.event_id,
                "event_sha256": event_sha,
                "boundary_act": act_index,
                "before_world_root": before,
                "after_world_root": after,
                "visible_projection_sha256": projection_sha,
                "restore_generation": world.restore_generation,
                "previous_occurrence_sha256": previous,
            }
            occurrence = AppliedEvent(
                event_id=event.event_id,
                event_sha256=event_sha,
                boundary_act=act_index,
                before_world_root=before,
                after_world_root=after,
                visible_projection=projection,
                visible_projection_sha256=projection_sha,
                restore_generation=world.restore_generation,
                previous_occurrence_sha256=previous,
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
        }

    @classmethod
    def restore(cls, scenario: Scenario, snapshot: dict[str, Any]) -> ScenarioEngine:
        engine = cls(scenario)
        engine.applied_ids = set(snapshot["applied_ids"])
        rows = []
        for value in snapshot["occurrences"]:
            rows.append(AppliedEvent(**value))
        engine.occurrences = rows
        engine.verify_chain()
        return engine

    def verify_chain(self) -> None:
        previous: str | None = None
        seen: set[str] = set()
        for row in self.occurrences:
            if row.event_id in seen:
                raise ValueError("duplicate_event_occurrence")
            body = {
                "event_id": row.event_id,
                "event_sha256": row.event_sha256,
                "boundary_act": row.boundary_act,
                "before_world_root": row.before_world_root,
                "after_world_root": row.after_world_root,
                "visible_projection_sha256": row.visible_projection_sha256,
                "restore_generation": row.restore_generation,
                "previous_occurrence_sha256": row.previous_occurrence_sha256,
            }
            if row.previous_occurrence_sha256 != previous:
                raise ValueError("occurrence_chain_previous_mismatch")
            if digest(row.visible_projection) != row.visible_projection_sha256:
                raise ValueError("occurrence_projection_digest_mismatch")
            if digest(body) != row.occurrence_sha256:
                raise ValueError("occurrence_digest_mismatch")
            previous = row.occurrence_sha256
            seen.add(row.event_id)
