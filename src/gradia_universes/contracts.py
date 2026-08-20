"""Strict public fixture contracts.

The contracts are deliberately small enough to audit in one sitting. They are
not copies of Gradia's private schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Recommendation = Literal["APPROVE", "CONDITIONAL", "ESCALATE", "DENY"]
MutationTarget = Literal["case", "policy", "notice"]


def _exact_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{context}_unknown_fields:{','.join(unknown)}")


@dataclass(frozen=True)
class Observation:
    source: str
    authority: Literal["authoritative", "unverified"]
    message: str

    @classmethod
    def parse(cls, value: dict[str, Any]) -> Observation:
        _exact_keys(value, {"source", "authority", "message"}, "observation")
        authority = value.get("authority")
        if authority not in {"authoritative", "unverified"}:
            raise ValueError("observation_authority_invalid")
        source = value.get("source")
        message = value.get("message")
        if not isinstance(source, str) or not source:
            raise ValueError("observation_source_required")
        if not isinstance(message, str) or not message:
            raise ValueError("observation_message_required")
        return cls(source=source, authority=authority, message=message)

    def public_view(self, event_id: str) -> dict[str, str]:
        return {
            "event_id": event_id,
            "source": self.source,
            "authority": self.authority,
            "message": self.message,
        }


@dataclass(frozen=True)
class Event:
    event_id: str
    after_act: int
    target: MutationTarget
    updates: dict[str, Any]
    observation: Observation

    @classmethod
    def parse(cls, value: dict[str, Any]) -> Event:
        _exact_keys(
            value,
            {"event_id", "after_act", "target", "updates", "observation"},
            "event",
        )
        event_id = value.get("event_id")
        after_act = value.get("after_act")
        target = value.get("target")
        updates = value.get("updates")
        observation = value.get("observation")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("event_id_required")
        if not isinstance(after_act, int) or after_act < 1:
            raise ValueError("event_after_act_invalid")
        if target not in {"case", "policy", "notice"}:
            raise ValueError("event_target_invalid")
        if not isinstance(updates, dict):
            raise ValueError("event_updates_object_required")
        if target == "notice" and updates:
            raise ValueError("notice_event_cannot_mutate_world")
        if not isinstance(observation, dict):
            raise ValueError("event_observation_required")
        return cls(
            event_id=event_id,
            after_act=after_act,
            target=target,
            updates=dict(updates),
            observation=Observation.parse(observation),
        )

    def private_contract(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "after_act": self.after_act,
            "target": self.target,
            "updates": self.updates,
            "observation": self.observation.public_view(self.event_id),
        }


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    title: str
    case: dict[str, Any]
    policy: dict[str, Any]
    events: tuple[Event, ...]
    restore_after_event: bool
    synthetic: bool

    @classmethod
    def parse(cls, value: dict[str, Any]) -> Scenario:
        _exact_keys(
            value,
            {
                "schema",
                "scenario_id",
                "title",
                "case",
                "policy",
                "events",
                "restore_after_event",
                "synthetic",
            },
            "scenario",
        )
        if value.get("schema") != "gradia-public-universe-scenario.v1":
            raise ValueError("scenario_schema_unsupported")
        scenario_id = value.get("scenario_id")
        title = value.get("title")
        case = value.get("case")
        policy = value.get("policy")
        raw_events = value.get("events")
        restore = value.get("restore_after_event")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise ValueError("scenario_id_required")
        if not isinstance(title, str) or not title:
            raise ValueError("scenario_title_required")
        if not isinstance(case, dict) or not isinstance(policy, dict):
            raise ValueError("scenario_case_and_policy_required")
        if not isinstance(raw_events, list):
            raise ValueError("scenario_events_array_required")
        if not isinstance(restore, bool):
            raise ValueError("scenario_restore_flag_required")
        if value.get("synthetic") is not True:
            raise ValueError("public_fixture_must_be_synthetic")
        events = tuple(Event.parse(row) for row in raw_events if isinstance(row, dict))
        if len(events) != len(raw_events):
            raise ValueError("scenario_event_object_required")
        ids = [event.event_id for event in events]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario_event_ids_not_unique")
        return cls(
            scenario_id=scenario_id,
            title=title,
            case=dict(case),
            policy=dict(policy),
            events=events,
            restore_after_event=restore,
            synthetic=True,
        )


@dataclass(frozen=True)
class Submission:
    recommendation: Recommendation
    observed_world_root: str
    citations: tuple[str, ...]
    rationale: str

