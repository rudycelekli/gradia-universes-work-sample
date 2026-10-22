"""Strict contracts for the LoanWorld scenario (``gradia-loanworld-scenario.v1``).

A scenario is one gold-parent loan universe: typed ledgers, a declared event
schedule and a private truth block. Parsing fails closed on unknown keys, the
same way the public universe contracts do.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from . import SCENARIO_SCHEMA

# Ledgers that make up world state. The world root is the digest of all of them;
# the inbox (agent-visible event log) is a projection and is excluded, exactly as
# in the public engine.
LEDGERS: tuple[str, ...] = (
    "case",
    "documents",
    "uploads",
    "conditions",
    "clock",
    "authority",
    "services",
    "los",
    "policy",
    "outbox",
    "agent_record",
)
# Ledgers an environment event may mutate. Agent effects (outbox, agent_record,
# LOS values, condition status) are written only through the tool API.
EVENT_TARGETS: frozenset[str] = frozenset(
    {"case", "documents", "uploads", "conditions", "clock", "authority", "services", "policy"}
)
EventOp = Literal["set", "append", "notice"]
CHANNELS: frozenset[str] = frozenset({"portal", "email", "sms", "phone", "los_note"})
CONDITION_CATEGORIES: frozenset[str] = frozenset({"PTD", "PTC", "PTF"})
OWNER_ROLES: frozenset[str] = frozenset({"processor", "underwriter", "closer", "funder"})
CAPTURE_CONDITIONS: frozenset[str] = frozenset(
    {"K0", "K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"}
)


def exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unknown = sorted(set(value) - expected)
        raise ValueError(f"{context}_keys_invalid:missing={missing}:unknown={unknown}")


def _str(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class LoanObservation:
    """What the agent sees when an event fires, plus the private authenticity truth."""

    source_label: str
    channel: str
    message: str
    attachments: tuple[str, ...]
    principal_id: str | None
    authentic: bool

    @classmethod
    def parse(cls, value: dict[str, Any]) -> LoanObservation:
        exact_keys(
            value,
            {"source_label", "channel", "message", "attachments", "principal_id", "authentic"},
            "loan_observation",
        )
        channel = _str(value["channel"], "loan_observation_channel_required")
        if channel not in CHANNELS:
            raise ValueError("loan_observation_channel_invalid")
        attachments = value["attachments"]
        if not isinstance(attachments, list) or not all(
            isinstance(item, str) and item for item in attachments
        ):
            raise ValueError("loan_observation_attachments_invalid")
        principal = value["principal_id"]
        if principal is not None and not isinstance(principal, str):
            raise ValueError("loan_observation_principal_invalid")
        if not isinstance(value["authentic"], bool):
            raise ValueError("loan_observation_authentic_required")
        return cls(
            source_label=_str(value["source_label"], "loan_observation_source_required"),
            channel=channel,
            message=_str(value["message"], "loan_observation_message_required"),
            attachments=tuple(attachments),
            principal_id=principal,
            authentic=value["authentic"],
        )

    def public_view(self, event_id: str) -> dict[str, Any]:
        # principal_id and authentic are truth; the agent must establish them itself.
        return {
            "event_id": event_id,
            "from": self.source_label,
            "channel": self.channel,
            "message": self.message,
            "attachments": list(self.attachments),
        }

    def contract(self) -> dict[str, Any]:
        return {
            "source_label": self.source_label,
            "channel": self.channel,
            "message": self.message,
            "attachments": list(self.attachments),
            "principal_id": self.principal_id,
            "authentic": self.authentic,
        }


@dataclass(frozen=True)
class LoanEvent:
    event_id: str
    after_act: int
    target: str
    op: EventOp
    path: tuple[str, ...]
    value: Any
    observation: LoanObservation

    @classmethod
    def parse(cls, value: dict[str, Any]) -> LoanEvent:
        exact_keys(
            value,
            {"event_id", "after_act", "target", "op", "path", "value", "observation"},
            "loan_event",
        )
        after_act = value["after_act"]
        if not isinstance(after_act, int) or isinstance(after_act, bool) or after_act < 1:
            raise ValueError("loan_event_after_act_invalid")
        op = value["op"]
        if op not in {"set", "append", "notice"}:
            raise ValueError("loan_event_op_invalid")
        target = _str(value["target"], "loan_event_target_required")
        path = value["path"]
        if not isinstance(path, list) or not all(isinstance(p, str) and p for p in path):
            raise ValueError("loan_event_path_invalid")
        if op == "notice":
            if target != "notice" or path or value["value"] is not None:
                raise ValueError("loan_notice_cannot_mutate_world")
        else:
            if target not in EVENT_TARGETS:
                raise ValueError("loan_event_target_invalid")
            if not path:
                raise ValueError("loan_event_path_required")
        observation = value["observation"]
        if not isinstance(observation, dict):
            raise ValueError("loan_event_observation_required")
        return cls(
            event_id=_str(value["event_id"], "loan_event_id_required"),
            after_act=after_act,
            target=target,
            op=op,
            path=tuple(path),
            value=value["value"],
            observation=LoanObservation.parse(observation),
        )

    def private_contract(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "after_act": self.after_act,
            "target": self.target,
            "op": self.op,
            "path": list(self.path),
            "value": self.value,
            "observation": self.observation.contract(),
        }


@dataclass(frozen=True)
class LoanScenario:
    scenario_id: str
    title: str
    generator: dict[str, Any]
    ledgers: dict[str, Any]
    events: tuple[LoanEvent, ...]
    private: dict[str, Any]
    synthetic: bool

    @classmethod
    def parse(cls, value: dict[str, Any]) -> LoanScenario:
        exact_keys(
            value,
            {
                "schema",
                "scenario_id",
                "title",
                "synthetic",
                "generator",
                "ledgers",
                "events",
                "private",
            },
            "loan_scenario",
        )
        if value["schema"] != SCENARIO_SCHEMA:
            raise ValueError("loan_scenario_schema_unsupported")
        if value["synthetic"] is not True:
            raise ValueError("public_fixture_must_be_synthetic")
        generator = value["generator"]
        if not isinstance(generator, dict):
            raise ValueError("loan_scenario_generator_required")
        exact_keys(generator, {"name", "version", "seed"}, "loan_scenario_generator")
        ledgers = value["ledgers"]
        if not isinstance(ledgers, dict):
            raise ValueError("loan_scenario_ledgers_required")
        exact_keys(ledgers, set(LEDGERS), "loan_scenario_ledgers")
        validate_ledgers(ledgers)
        raw_events = value["events"]
        if not isinstance(raw_events, list) or not all(isinstance(e, dict) for e in raw_events):
            raise ValueError("loan_scenario_events_invalid")
        events = tuple(LoanEvent.parse(row) for row in raw_events)
        ids = [event.event_id for event in events]
        if len(ids) != len(set(ids)):
            raise ValueError("loan_scenario_event_ids_not_unique")
        private = value["private"]
        if not isinstance(private, dict):
            raise ValueError("loan_scenario_private_required")
        return cls(
            scenario_id=_str(value["scenario_id"], "loan_scenario_id_required"),
            title=_str(value["title"], "loan_scenario_title_required"),
            generator=dict(generator),
            ledgers=dict(ledgers),
            events=events,
            private=dict(private),
            synthetic=True,
        )


def validate_ledgers(ledgers: dict[str, Any]) -> None:
    """Structural checks that keep every ledger answerable by the oracle later."""
    for name in (
        "case",
        "documents",
        "uploads",
        "conditions",
        "clock",
        "authority",
        "services",
        "los",
        "policy",
        "outbox",
        "agent_record",
    ):
        if not isinstance(ledgers[name], dict):
            raise ValueError(f"ledger_{name}_object_required")
    uploads: dict[str, Any] = ledgers["uploads"]
    for upload_id, upload in uploads.items():
        exact_keys(
            upload,
            {
                "upload_id",
                "filename",
                "media",
                "from_principal",
                "received_act",
                "status",
                "page_size",
                "pages",
                "capture",
                "text_layer_overrides",
            },
            f"upload_{upload_id}",
        )
        if upload["upload_id"] != upload_id:
            raise ValueError("upload_id_mismatch")
        if upload["media"] not in {"pdf", "image"}:
            raise ValueError("upload_media_invalid")
        if upload["capture"]["condition"] not in CAPTURE_CONDITIONS:
            raise ValueError("upload_capture_condition_invalid")
        if upload["media"] == "image" and upload["capture"]["condition"] == "K0":
            raise ValueError("image_upload_cannot_be_native_pdf")
    for doc_id, document in ledgers["documents"].items():
        if document["doc_id"] != doc_id:
            raise ValueError("document_id_mismatch")
        if document["upload_id"] not in uploads:
            raise ValueError("document_upload_unknown")
        page_count = len(uploads[document["upload_id"]]["pages"])
        for page in document["pages"]:
            if not 1 <= page <= page_count:
                raise ValueError("document_page_out_of_range")
    for condition in ledgers["conditions"].values():
        if condition["category"] not in CONDITION_CATEGORIES:
            raise ValueError("condition_category_invalid")
        if condition["owner_role"] not in OWNER_ROLES:
            raise ValueError("condition_owner_invalid")
    for principal in ledgers["authority"]["principals"].values():
        for channel in principal["channels"]:
            if channel["channel"] not in CHANNELS:
                raise ValueError("principal_channel_invalid")
