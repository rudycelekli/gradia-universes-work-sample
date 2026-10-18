"""LoanWorld tool API: every call is one act, one world effect and one chained receipt.

The session owns a ``LoanWorld`` and its ``LoanEngine``. A tool call:

1. validates arguments against ``TOOL_SPECS`` (unknown keys fail closed);
2. applies the effect to root-owned ledgers (outbox, agent_record, LOS, conditions);
3. writes a receipt binding the call, the response, and the world root before and
   after, hash-chained to the previous receipt;
4. advances the scenario engine, which fires any events scheduled after this act.

External effects (messages, document requests) carry an idempotency key. If the
same effect is sent again after a restore, it is recorded with
``duplicate_after_restore: true`` so a grader can count it; the call still
succeeds, because real channels do not refuse duplicates either.

The receipt chain is LoanWorld's own format (``gradia.loanworld.receipt.v1``). It
is designed to map onto Gradia Guard's SDK bundle later; this module does not
claim Guard ABI compatibility.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..canonical import digest
from ..world import verify_occurrence_chain
from .counterparts import CounterpartRuntime
from .schema import LoanScenario
from .world import LoanEngine, LoanWorld

RECEIPT_SCHEMA = "gradia.loanworld.receipt.v1"
PROOF_PACK_SCHEMA = "gradia.loanworld.proof-pack.v1"
RECOMMENDATIONS = frozenset({"PRECHECK_PASS", "CONDITIONAL", "ESCALATE", "DECLINE_RECOMMENDED"})
FLAG_CODES = frozenset(
    {
        "INCOME_VALUE_CONFLICT",
        "INCOMPLETE_DOCUMENT",
        "BORROWER_NAME_MISMATCH",
        "APPRAISED_VALUE_CONFLICT",
        "EMPLOYER_NAME_MISMATCH",
        "DOCUMENT_EXPIRED",
        "CTC_BLOCKING_CONDITION",
        "LOX_REQUIRED",
        "POSSIBLE_WRONG_DOCUMENT",
        "PURCHASE_PRICE_CONFLICT",
        "PAYOFF_CONDITION_MISSING",
        "LIABILITY_PAYMENT_CONFLICT",
        "OCCUPANCY_MISREP",
        "TEXT_LAYER_MISMATCH",
        "POSSIBLE_TAMPERING",
        "ILLEGIBLE_VALUE",
        "UNAUTHORIZED_INSTRUCTION",
        "SUSPECTED_FRAUD",
        "OTHER",
    }
)

# name -> {arg: (type-name, required)}. Types: str, int, list, citations.
TOOL_SPECS: dict[str, dict[str, tuple[str, bool]]] = {
    "get_projection": {},
    "list_uploads": {},
    "get_page": {"upload_id": ("str", True), "page": ("int", True)},
    "read_inbox": {"since": ("int", False)},
    "request_document": {
        "party": ("str", True),
        "doc_type": ("str", True),
        "reason": ("str", True),
    },
    "send_message": {"party": ("str", True), "channel": ("str", True), "text": ("str", True)},
    "order_service": {"kind": ("str", True)},
    "get_conditions": {},
    "clear_condition": {
        "condition_id": ("str", True),
        "citations": ("citations", True),
        "note": ("str", True),
    },
    "add_condition": {
        "category": ("str", True),
        "text": ("str", True),
        "citations": ("citations", True),
    },
    "write_los_field": {
        "key": ("str", True),
        "value": ("str", True),
        "citation": ("citation", True),
    },
    "flag": {
        "code": ("str", True),
        "target": ("str", True),
        "citations": ("citations", True),
        "note": ("str", True),
    },
    "escalate": {"reason": ("str", True)},
    "submit": {
        "recommendation": ("str", True),
        "open_conditions": ("list", True),
        "account": ("list", True),
    },
}


class ToolError(ValueError):
    pass


def _check_args(tool: str, args: dict[str, Any]) -> None:
    spec = TOOL_SPECS.get(tool)
    if spec is None:
        raise ToolError("unknown_tool")
    unknown = set(args) - set(spec)
    if unknown:
        raise ToolError(f"unknown_args:{','.join(sorted(unknown))}")
    for name, (kind, required) in spec.items():
        if name not in args:
            if required:
                raise ToolError(f"missing_arg:{name}")
            continue
        value = args[name]
        ok = {
            "str": isinstance(value, str) and bool(value.strip()),
            "int": isinstance(value, int) and not isinstance(value, bool),
            "list": isinstance(value, list),
            "citations": isinstance(value, list),
            "citation": isinstance(value, dict),
        }[kind]
        if not ok:
            raise ToolError(f"bad_arg_type:{name}")


class LoanWorldSession:
    def __init__(
        self,
        scenario: LoanScenario,
        max_acts: int = 200,
        counterparts: dict[str, Any] | None = None,
    ) -> None:
        self.scenario = scenario
        self.counterparts = CounterpartRuntime(counterparts) if counterparts else None
        self.world = LoanWorld(scenario)
        self.engine = LoanEngine(scenario)
        self.act = 0
        self.max_acts = max_acts
        self.receipts: list[dict[str, Any]] = []
        self.sent_keys: set[str] = set()
        self.terminal: dict[str, Any] | None = None

    # ------------------------------------------------------------ lifecycle

    def snapshot(self) -> dict[str, Any]:
        return {
            "world": self.world.snapshot(),
            "engine": self.engine.snapshot(),
            "act": self.act,
            "receipts": deepcopy(self.receipts),
            "sent_keys": sorted(self.sent_keys),
            "terminal": deepcopy(self.terminal),
        }

    @classmethod
    def restore(
        cls,
        scenario: LoanScenario,
        snapshot: dict[str, Any],
        max_acts: int = 200,
        already_sent: set[str] | None = None,
        counterparts: dict[str, Any] | None = None,
    ) -> LoanWorldSession:
        """Restore a snapshot; ``already_sent`` carries effects that left the world.

        Rolling the ledgers back cannot unsend an email. Pass the idempotency keys
        the abandoned branch already delivered so a re-send is recorded as a
        duplicate external effect.
        """
        session = cls(scenario, max_acts, counterparts)
        session.world = LoanWorld.restore(scenario, snapshot["world"])
        session.engine = LoanEngine.restore(scenario, snapshot["engine"])
        session.act = int(snapshot["act"])
        session.receipts = deepcopy(snapshot["receipts"])
        verify_receipts(session.receipts)
        session.sent_keys = set(snapshot["sent_keys"]) | set(already_sent or ())
        session.terminal = deepcopy(snapshot["terminal"])
        return session

    # ------------------------------------------------------------ dispatch

    def call(self, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        args = dict(args or {})
        if self.terminal is not None:
            return {"ok": False, "error": "episode_already_submitted"}
        if self.act >= self.max_acts:
            return {"ok": False, "error": "act_budget_exhausted"}
        self.act += 1
        before = self.world.root
        try:
            _check_args(tool, args)
            result = getattr(self, f"_tool_{tool}")(**args)
            response: dict[str, Any] = {"ok": True, "result": result}
        except ToolError as error:
            response = {"ok": False, "error": str(error)}
        after_effect = self.world.root
        fired = self.engine.advance(self.act, self.world)
        if fired:
            response["events"] = [
                dict(self.world.inbox[-len(fired) + i]) for i in range(len(fired))
            ]
        previous = self.receipts[-1]["receipt_sha256"] if self.receipts else None
        body = {
            "schema": RECEIPT_SCHEMA,
            "seq": len(self.receipts) + 1,
            "act": self.act,
            "restore_generation": self.world.restore_generation,
            "tool": tool,
            "args_sha256": digest(args),
            "response_sha256": digest(response),
            "world_root_before": before,
            "world_root_after_effect": after_effect,
            "world_root_after_events": self.world.root,
            "occurrence_ids": [row.event_id for row in fired],
            "previous_receipt_sha256": previous,
        }
        self.receipts.append({**body, "args": args, "receipt_sha256": digest(body)})
        return response

    # ------------------------------------------------------------ helpers

    def _principal(self, party: str) -> dict[str, Any]:
        principal = self.world.ledgers["authority"]["principals"].get(party)
        if principal is None:
            raise ToolError("unknown_party")
        assert isinstance(principal, dict)
        return principal

    def _validate_citation(self, citation: Any) -> dict[str, Any]:
        if not isinstance(citation, dict):
            raise ToolError("citation_object_required")
        kinds = [key for key in ("upload_id", "service", "event_id") if key in citation]
        if len(kinds) != 1:
            raise ToolError("citation_needs_exactly_one_source")
        if "upload_id" in citation:
            allowed = {"upload_id", "page", "bbox_cpt", "quote"}
            if set(citation) - allowed or not {"upload_id", "page"} <= set(citation):
                raise ToolError("citation_upload_shape_invalid")
            upload = self.world.ledgers["uploads"].get(citation["upload_id"])
            if upload is None or upload["status"] == "not_yet_received":
                raise ToolError("citation_upload_unknown")
            page = citation["page"]
            if not isinstance(page, int) or not 1 <= page <= len(upload["pages"]):
                raise ToolError("citation_page_out_of_range")
            bbox = citation.get("bbox_cpt")
            if bbox is not None and not (
                isinstance(bbox, list)
                and len(bbox) == 4
                and all(isinstance(v, int) and not isinstance(v, bool) for v in bbox)
                and bbox[0] < bbox[2]
                and bbox[1] < bbox[3]
            ):
                raise ToolError("citation_bbox_invalid")
        elif "service" in citation:
            if set(citation) - {"service", "path"}:
                raise ToolError("citation_service_shape_invalid")
            service = self.world.ledgers["services"].get(citation["service"])
            if service is None or service["status"] != "returned":
                raise ToolError("citation_service_not_returned")
        else:
            if set(citation) != {"event_id"}:
                raise ToolError("citation_event_shape_invalid")
            if citation["event_id"] not in {row["event_id"] for row in self.world.inbox}:
                raise ToolError("citation_event_not_seen")
        return dict(citation)

    def _citations(self, citations: list[Any]) -> list[dict[str, Any]]:
        if not citations:
            raise ToolError("citations_required")
        return [self._validate_citation(item) for item in citations]

    def _effect(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        key = digest({"kind": kind, **payload})
        duplicate = key in self.sent_keys
        self.sent_keys.add(key)
        return {
            **payload,
            "act": self.act,
            "idempotency_key": key,
            "restore_generation": self.world.restore_generation,
            "duplicate_after_restore": duplicate,
        }

    # ------------------------------------------------------------ tools

    def _tool_get_projection(self) -> dict[str, Any]:
        return self.world.projection()

    def _tool_list_uploads(self) -> list[dict[str, Any]]:
        uploads: list[dict[str, Any]] = self.world.projection()["uploads"]
        return uploads

    def _tool_get_page(self, upload_id: str, page: int) -> dict[str, Any]:
        upload = self.world.ledgers["uploads"].get(upload_id)
        if upload is None or upload["status"] == "not_yet_received":
            raise ToolError("upload_unknown")
        if not 1 <= page <= len(upload["pages"]):
            raise ToolError("page_out_of_range")
        text_layer = None
        if upload["media"] == "pdf":
            runs = deepcopy(upload["pages"][page - 1]["runs"])
            for override in upload["text_layer_overrides"].get(str(page), []):
                runs[override["run_index"]]["text"] = override["text"]
            text_layer = [
                {"text": run["text"], "bbox_cpt": run["bbox_cpt"]}
                for run in runs
                if not run["hand"]
            ]
        return {
            "upload_id": upload_id,
            "page": page,
            "page_size_cpt": upload["page_size"],
            "media": upload["media"],
            # Pixels come from the render manifest (render.py); scans and photos have
            # no text layer, so an agent without OCR must escalate rather than guess.
            "text_layer": text_layer,
            "pixels": {"render_ref": f"{self.scenario.scenario_id}/{upload_id}/p{page}"},
        }

    def _tool_read_inbox(self, since: int = 0) -> list[dict[str, Any]]:
        return deepcopy(self.world.inbox[since:])

    def _tool_request_document(self, party: str, doc_type: str, reason: str) -> dict[str, Any]:
        self._principal(party)
        effect = self._effect(
            "document_request", {"party": party, "doc_type": doc_type, "reason": reason}
        )
        self.world.ledgers["outbox"]["document_requests"].append(effect)
        return {
            "queued": True,
            "duplicate_after_restore": effect["duplicate_after_restore"],
            "reply": self._reply(effect, "document_request"),
        }

    def _tool_send_message(self, party: str, channel: str, text: str) -> dict[str, Any]:
        principal = self._principal(party)
        on_file = [c["channel"] for c in principal["channels"]]
        effect = self._effect("message", {"party": party, "channel": channel, "text": text})
        effect["channel_on_file"] = channel in on_file
        self.world.ledgers["outbox"]["messages"].append(effect)
        return {
            "queued": True,
            "duplicate_after_restore": effect["duplicate_after_restore"],
            "reply": self._reply(effect, "message"),
        }

    def _reply(self, effect: dict[str, Any], kind: str) -> dict[str, Any] | None:
        if self.counterparts is None:
            return None
        return self.counterparts.respond(self.world, self.act, effect, kind)

    def _tool_order_service(self, kind: str) -> dict[str, Any]:
        service = self.world.ledgers["services"].get(kind)
        if service is None:
            raise ToolError("unknown_service")
        if service["status"] != "returned":
            service["status"] = "returned"
            service["ordered_act"] = self.act
        return {
            "kind": kind,
            "version": service["version"],
            "result": deepcopy(service["result"]),
        }

    def _tool_get_conditions(self) -> dict[str, Any]:
        return deepcopy(self.world.ledgers["conditions"])

    def _tool_clear_condition(
        self, condition_id: str, citations: list[Any], note: str
    ) -> dict[str, Any]:
        condition = self.world.ledgers["conditions"].get(condition_id)
        if condition is None:
            raise ToolError("unknown_condition")
        cited = self._citations(citations)
        condition["status"] = "cleared"
        condition["cleared_act"] = self.act
        condition["cleared_citations"] = cited
        self.world.ledgers["agent_record"]["condition_actions"].append(
            {
                "act": self.act,
                "action": "clear",
                "condition_id": condition_id,
                "citations": cited,
                "note": note,
            }
        )
        return {"condition_id": condition_id, "status": "cleared"}

    def _tool_add_condition(
        self, category: str, text: str, citations: list[Any]
    ) -> dict[str, Any]:
        if category not in {"PTD", "PTC", "PTF"}:
            raise ToolError("condition_category_invalid")
        cited = self._citations(citations)
        conditions = self.world.ledgers["conditions"]
        condition_id = f"C-A{len(conditions) + 1:02d}"
        conditions[condition_id] = {
            "category": category,
            "owner_role": "processor",
            "text": text,
            "satisfied_by": [],
            "status": "open",
            "source": "agent",
            "cleared_act": None,
            "cleared_citations": [],
            "added_citations": cited,
        }
        self.world.ledgers["agent_record"]["condition_actions"].append(
            {"act": self.act, "action": "add", "condition_id": condition_id, "citations": cited}
        )
        return {"condition_id": condition_id}

    def _tool_write_los_field(
        self, key: str, value: str, citation: dict[str, Any]
    ) -> dict[str, Any]:
        los = self.world.ledgers["los"]
        field = next((row for row in los["fields"] if row["key"] == key), None)
        if field is None:
            raise ToolError("unknown_los_field")
        if not field["writable"]:
            raise ToolError("los_field_read_only")
        cited = self._validate_citation(citation)
        prior = los["values"].get(key)
        los["values"][key] = value
        los["write_log"].append(
            {
                "act": self.act,
                "key": key,
                "prior": prior,
                "value": value,
                "citation": cited,
                "restore_generation": self.world.restore_generation,
            }
        )
        return {"key": key, "prior": prior, "value": value}

    def _tool_flag(
        self, code: str, target: str, citations: list[Any], note: str
    ) -> dict[str, Any]:
        if code not in FLAG_CODES:
            raise ToolError("flag_code_unknown")
        cited = self._citations(citations)
        self.world.ledgers["agent_record"]["flags"].append(
            {"act": self.act, "code": code, "target": target, "citations": cited, "note": note}
        )
        return {"flagged": code}

    def _tool_escalate(self, reason: str) -> dict[str, Any]:
        self.world.ledgers["agent_record"]["escalations"].append(
            {"act": self.act, "reason": reason}
        )
        return {"escalated": True}

    def _tool_submit(
        self, recommendation: str, open_conditions: list[Any], account: list[Any]
    ) -> dict[str, Any]:
        if recommendation not in RECOMMENDATIONS:
            raise ToolError("recommendation_invalid")
        if not all(isinstance(item, str) for item in open_conditions):
            raise ToolError("open_conditions_must_be_ids")
        claims = []
        for row in account:
            if not isinstance(row, dict) or set(row) != {"claim", "citations"}:
                raise ToolError("account_row_shape_invalid")
            if not isinstance(row["claim"], str) or not row["claim"].strip():
                raise ToolError("account_claim_required")
            claims.append(
                {"claim": row["claim"], "citations": self._citations(row["citations"])}
            )
        terminal = {
            "recommendation": recommendation,
            "open_conditions": sorted(open_conditions),
            "account": claims,
            "observed_world_root": self.world.root,
            "act": self.act,
        }
        self.world.ledgers["agent_record"]["terminal"] = terminal
        self.terminal = terminal
        return {"submitted": True, "observed_world_root": terminal["observed_world_root"]}

    # ------------------------------------------------------------ evidence

    def proof_pack(self) -> dict[str, Any]:
        body = {
            "schema": PROOF_PACK_SCHEMA,
            "scenario_id": self.scenario.scenario_id,
            "generator": self.scenario.generator,
            "final_world_root": self.world.root,
            "ledger_roots": self.world.ledger_roots(),
            "receipt_head": self.receipts[-1]["receipt_sha256"] if self.receipts else None,
            "receipt_count": len(self.receipts),
            "occurrence_head": (
                self.engine.occurrences[-1].occurrence_sha256
                if self.engine.occurrences
                else None
            ),
            "terminal": deepcopy(self.terminal),
            "counterparts_sha256": (
                self.counterparts.contract_sha256 if self.counterparts else None
            ),
        }
        return {
            **body,
            "receipts": deepcopy(self.receipts),
            "occurrences": [row.as_dict() for row in self.engine.occurrences],
            "pack_sha256": digest(body),
        }


def verify_receipts(receipts: list[dict[str, Any]]) -> None:
    previous: str | None = None
    for index, receipt in enumerate(receipts, start=1):
        body = {
            key: value
            for key, value in receipt.items()
            if key not in {"args", "receipt_sha256"}
        }
        if receipt["seq"] != index:
            raise ValueError("receipt_sequence_gap")
        if receipt["previous_receipt_sha256"] != previous:
            raise ValueError("receipt_chain_previous_mismatch")
        if digest(receipt["args"]) != receipt["args_sha256"]:
            raise ValueError("receipt_args_digest_mismatch")
        if digest(body) != receipt["receipt_sha256"]:
            raise ValueError("receipt_digest_mismatch")
        previous = receipt["receipt_sha256"]


def verify_proof_pack(pack: dict[str, Any]) -> None:
    """Offline check: receipt chain, occurrence chain and the pack digest."""
    from ..world import AppliedEvent

    verify_receipts(pack["receipts"])
    occurrences = [AppliedEvent(**row) for row in pack["occurrences"]]
    verify_occurrence_chain(occurrences)
    body_keys = {
        "schema",
        "scenario_id",
        "generator",
        "final_world_root",
        "ledger_roots",
        "receipt_head",
        "receipt_count",
        "occurrence_head",
        "terminal",
        "counterparts_sha256",
    }
    body = {key: pack[key] for key in body_keys}
    if pack["receipt_count"] != len(pack["receipts"]):
        raise ValueError("proof_pack_receipt_count_mismatch")
    head = pack["receipts"][-1]["receipt_sha256"] if pack["receipts"] else None
    if pack["receipt_head"] != head:
        raise ValueError("proof_pack_receipt_head_mismatch")
    occ_head = occurrences[-1].occurrence_sha256 if occurrences else None
    if pack["occurrence_head"] != occ_head:
        raise ValueError("proof_pack_occurrence_head_mismatch")
    if digest(body) != pack["pack_sha256"]:
        raise ValueError("proof_pack_digest_mismatch")
