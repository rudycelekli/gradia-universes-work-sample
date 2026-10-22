"""Root-owned LoanWorld state, exactly-once events, and the agent-visible projection.

Semantics deliberately mirror ``gradia_universes.world``: the world root is a
digest of state (not of the agent-visible inbox), snapshot/restore increments a
restore generation, and every applied event becomes an ``AppliedEvent`` in one
hash chain verified by the shared ``verify_occurrence_chain``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..canonical import canonical_bytes, digest
from ..world import AppliedEvent, occurrence_body, verify_occurrence_chain
from .schema import LEDGERS, LoanEvent, LoanScenario

# Fields inside a document or upload that are truth, never shown to the agent.
_PRIVATE_DOCUMENT_KEYS = frozenset({"critical_values", "traps", "truth"})


def _walk(container: Any, path: tuple[str, ...]) -> tuple[Any, str]:
    node = container
    for key in path[:-1]:
        if not isinstance(node, dict) or key not in node:
            raise ValueError(f"loan_path_missing:{'/'.join(path)}")
        node = node[key]
    if not isinstance(node, dict):
        raise ValueError(f"loan_path_parent_not_object:{'/'.join(path)}")
    return node, path[-1]


class LoanWorld:
    def __init__(self, scenario: LoanScenario) -> None:
        self.ledgers: dict[str, Any] = deepcopy(scenario.ledgers)
        self.inbox: list[dict[str, Any]] = []
        self.restore_generation = 0

    @property
    def root(self) -> str:
        return digest({name: self.ledgers[name] for name in LEDGERS})

    def ledger_roots(self) -> dict[str, str]:
        return {name: digest(self.ledgers[name]) for name in LEDGERS}

    def snapshot(self) -> dict[str, Any]:
        return {
            "ledgers": deepcopy(self.ledgers),
            "inbox": deepcopy(self.inbox),
            "restore_generation": self.restore_generation,
        }

    @classmethod
    def restore(cls, scenario: LoanScenario, snapshot: dict[str, Any]) -> LoanWorld:
        world = cls(scenario)
        world.ledgers = deepcopy(snapshot["ledgers"])
        world.inbox = deepcopy(snapshot["inbox"])
        world.restore_generation = int(snapshot["restore_generation"]) + 1
        return world

    def apply(self, event: LoanEvent) -> tuple[str, str, dict[str, Any]]:
        before = self.root
        if event.op != "notice":
            parent, key = _walk(self.ledgers[event.target], event.path)
            if event.op == "set":
                parent[key] = deepcopy(event.value)
            else:
                existing = parent.get(key)
                if not isinstance(existing, list):
                    raise ValueError("loan_append_target_not_list")
                existing.append(deepcopy(event.value))
        projection = event.observation.public_view(event.event_id)
        self.inbox.append(projection)
        return before, self.root, projection

    def projection(self) -> dict[str, Any]:
        """Everything the agent may see right now. Case truth is never included."""
        uploads = []
        for upload in self.ledgers["uploads"].values():
            if upload["status"] == "not_yet_received":
                continue
            uploads.append(
                {
                    "upload_id": upload["upload_id"],
                    "filename": upload["filename"],
                    "media": upload["media"],
                    "pages": len(upload["pages"]),
                    "received_act": upload["received_act"],
                    "from": self.ledgers["authority"]["principals"][upload["from_principal"]][
                        "display_name"
                    ],
                    "status": upload["status"],
                }
            )
        services = {
            kind: {
                "status": service["status"],
                "version": service["version"],
                **(
                    {"result": deepcopy(service["result"])}
                    if service["status"] == "returned"
                    else {}
                ),
            }
            for kind, service in self.ledgers["services"].items()
        }
        los = self.ledgers["los"]
        return {
            "role": "processor",
            "clock": deepcopy(self.ledgers["clock"]),
            "uploads": uploads,
            "inbox": deepcopy(self.inbox),
            "conditions": deepcopy(self.ledgers["conditions"]),
            "services": services,
            "los": {
                "fields": deepcopy(los["fields"]),
                "values": deepcopy(los["values"]),
            },
            "policy": deepcopy(self.ledgers["policy"]),
            "contacts": {
                principal_id: {
                    "display_name": principal["display_name"],
                    "role": principal["role"],
                    "channels": deepcopy(principal["channels"]),
                }
                for principal_id, principal in self.ledgers["authority"]["principals"].items()
            },
        }


def _string_projection(projection: dict[str, Any]) -> dict[str, str]:
    """AppliedEvent projections are string-valued; lists use canonical JSON spelling."""
    return {
        key: value if isinstance(value, str) else canonical_bytes(value).decode("utf-8")
        for key, value in projection.items()
    }


def document_public_view(document: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in document.items()
        if key not in _PRIVATE_DOCUMENT_KEYS
    }


class LoanEngine:
    def __init__(self, scenario: LoanScenario) -> None:
        self.scenario = scenario
        self.applied_ids: set[str] = set()
        self.occurrences: list[AppliedEvent] = []

    def advance(self, act_index: int, world: LoanWorld) -> list[AppliedEvent]:
        fired: list[AppliedEvent] = []
        for event in self.scenario.events:
            if event.event_id in self.applied_ids or event.after_act != act_index:
                continue
            before, after, projection = world.apply(event)
            previous = self.occurrences[-1].occurrence_sha256 if self.occurrences else None
            row = AppliedEvent(
                event_id=event.event_id,
                event_sha256=digest(event.private_contract()),
                boundary_act=act_index,
                before_world_root=before,
                after_world_root=after,
                visible_projection=_string_projection(projection),
                visible_projection_sha256="",
                restore_generation=world.restore_generation,
                previous_occurrence_sha256=previous,
                occurrence_sha256="",
            )
            projection_sha = digest(row.visible_projection)
            row = AppliedEvent(**{**row.as_dict(), "visible_projection_sha256": projection_sha})
            row = AppliedEvent(
                **{**row.as_dict(), "occurrence_sha256": digest(occurrence_body(row))}
            )
            self.applied_ids.add(event.event_id)
            self.occurrences.append(row)
            fired.append(row)
        return fired

    def snapshot(self) -> dict[str, Any]:
        return {
            "applied_ids": sorted(self.applied_ids),
            "occurrences": [row.as_dict() for row in self.occurrences],
        }

    @classmethod
    def restore(cls, scenario: LoanScenario, snapshot: dict[str, Any]) -> LoanEngine:
        engine = cls(scenario)
        engine.applied_ids = set(snapshot["applied_ids"])
        engine.occurrences = [AppliedEvent(**value) for value in snapshot["occurrences"]]
        verify_occurrence_chain(engine.occurrences)
        return engine
