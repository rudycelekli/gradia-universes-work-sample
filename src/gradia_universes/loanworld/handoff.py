"""Family F6: successor handoff.

One agent works the file and is cut off mid-file at a fixed act. Before it goes it
writes a **handoff artifact**; it never sees the response to its last act. A cold
successor then finishes the same episode from the artifact and the current
projection alone: it never sees the predecessor's tool results or reasoning.

F6 forks change the world *during* the handoff: their one intervention is an event
scheduled to fire right after the cut-off act, so the artifact is already stale
when the successor reads it. Both agents write to one receipt chain, so the oracle
grades the final state exactly as it grades any episode, and the handoff record is
bound to that chain (``receipt_head`` is the receipt of the cut-off act).

Protocol ``gradia.loanworld.handoff.v0`` extends the stdio protocol with two
messages and changes no tool:

harness -> predecessor  {"type": "handoff_request", "act": n}
predecessor -> harness  {"type": "handoff", "artifact": {"notes", "next_steps", "claims"}}
harness -> successor    {"type": "start", "protocol", "handoff", "acts_used", ...projection}

A predecessor that submits before the cut-off, or writes a malformed artifact, is
censored (``finished_before_handoff`` / ``malformed_handoff``), never scored.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..canonical import digest
from .adapter import PROTOCOL, _parse_call, _result, _start_message, tool_manifest
from .schema import LoanScenario
from .tools import LoanWorldSession

HANDOFF_PROTOCOL = "gradia.loanworld.handoff.v0"
MAX_NOTES_CHARS = 8000
MAX_ITEMS = 60

Agent = Callable[[dict[str, Any]], dict[str, Any]]


def _citation_shape_ok(citation: Any) -> bool:
    if not isinstance(citation, dict):
        return False
    if set(citation) == {"upload_id", "page"}:
        page = citation["page"]
        return isinstance(citation["upload_id"], str) and isinstance(page, int) and page >= 1
    if set(citation) == {"service"} or set(citation) == {"event_id"}:
        return all(isinstance(v, str) for v in citation.values())
    return False


def validate_artifact(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("type") != "handoff":
        raise ValueError("handoff_message_invalid")
    artifact = raw.get("artifact")
    if not isinstance(artifact, dict) or set(artifact) != {"notes", "next_steps", "claims"}:
        raise ValueError("handoff_artifact_shape_invalid")
    notes, steps, claims = artifact["notes"], artifact["next_steps"], artifact["claims"]
    if not isinstance(notes, str) or len(notes) > MAX_NOTES_CHARS:
        raise ValueError("handoff_notes_invalid")
    if not isinstance(steps, list) or len(steps) > MAX_ITEMS:
        raise ValueError("handoff_next_steps_invalid")
    for step in steps:
        is_call = (
            isinstance(step, dict)
            and set(step) == {"tool", "args"}
            and isinstance(step["tool"], str)
            and isinstance(step["args"], dict)
        )
        if not (is_call or isinstance(step, str)):
            raise ValueError("handoff_step_invalid")
    if not isinstance(claims, list) or len(claims) > MAX_ITEMS:
        raise ValueError("handoff_claims_invalid")
    for claim in claims:
        if not (
            isinstance(claim, dict)
            and set(claim) == {"claim", "citations"}
            and isinstance(claim["claim"], str)
            and isinstance(claim["citations"], list)
            and all(_citation_shape_ok(c) for c in claim["citations"])
        ):
            raise ValueError("handoff_claim_invalid")
    return {"notes": notes, "next_steps": steps, "claims": claims}


def _successor_start(session: LoanWorldSession, artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "start",
        "protocol": HANDOFF_PROTOCOL,
        "base_protocol": PROTOCOL,
        "scenario_id": session.scenario.scenario_id,
        "max_acts": session.max_acts,
        "acts_used": session.act,
        "tools": tool_manifest(),
        "projection": session.world.projection(),
        "handoff": artifact,
    }


def run_handoff_episode(
    scenario: LoanScenario,
    predecessor: Agent,
    successor: Agent,
    handoff_act: int,
    max_acts: int = 200,
    counterparts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """In-process handoff episode. The result adds a ``handoff`` record to the usual result."""
    session = LoanWorldSession(scenario, max_acts, counterparts)
    message = _start_message(session)
    agent, record = predecessor, None

    def finish(outcome: str, reason: str | None) -> dict[str, Any]:
        return {**_result(session, outcome, reason), "handoff": record}

    while True:
        call = _parse_call(agent(message))
        if call is None:
            return finish("censored", "malformed_agent_message")
        response = session.call(*call)
        if session.terminal is not None:
            if record is None:
                return finish("censored", "finished_before_handoff")
            return finish("terminal", None)
        if response.get("error") == "act_budget_exhausted":
            return finish("censored", "act_budget_exhausted")
        if record is None and session.act == handoff_act:
            try:
                artifact = validate_artifact(
                    predecessor({"type": "handoff_request", "act": session.act})
                )
            except ValueError:
                return finish("censored", "malformed_handoff")
            record = {
                "protocol": HANDOFF_PROTOCOL,
                "act": session.act,
                "artifact": artifact,
                "artifact_sha256": digest(artifact),
                "receipt_head": session.receipts[-1]["receipt_sha256"],
            }
            agent, message = successor, _successor_start(session, artifact)
            continue
        message = {"type": "result", "act": session.act, "response": response}


def handoff_bound(result: dict[str, Any], handoff_act: int) -> bool:
    """The handoff happened at the declared act and is bound to the receipt chain."""
    record = result.get("handoff")
    if not record or record["act"] != handoff_act:
        return False
    receipts = result["final_state"]["receipts"]
    return bool(
        len(receipts) >= handoff_act
        and receipts[handoff_act - 1]["receipt_sha256"] == record["receipt_head"]
        and digest(record["artifact"]) == record["artifact_sha256"]
    )


# ---------------------------------------------------------------- scripted parties


def scripted_predecessor(
    plan: list[tuple[str, dict[str, Any]]], handoff_act: int, *, honest: bool = True
) -> Agent:
    """Replays the first ``handoff_act`` steps, then hands off the rest as next steps.

    An honest artifact lists every remaining step and states what was done. With
    ``honest=False`` it omits the steps that keep conditions open (a predecessor that
    oversells its progress), which Wind Tunnel uses as an attack.
    """
    done, rest = plan[:handoff_act], plan[handoff_act:]
    steps = iter(done)

    def agent(message: dict[str, Any]) -> dict[str, Any]:
        if message["type"] == "handoff_request":
            remaining = [{"tool": t, "args": a} for t, a in rest]
            if not honest:
                remaining = [s for s in remaining if s["tool"] != "request_document"]
            notes = (
                f"Handing off after act {handoff_act}. Done: "
                + ", ".join(sorted({t for t, _ in done}))
                + ". Remaining steps follow; re-check the inbox for anything new."
            )
            return {
                "type": "handoff",
                "artifact": {"notes": notes, "next_steps": remaining, "claims": []},
            }
        tool, args = next(steps)
        return {"type": "call", "tool": tool, "args": args}

    return agent


def artifact_follower() -> Agent:
    """Baseline successor that trusts the artifact: executes its next steps verbatim."""
    queue: list[tuple[str, dict[str, Any]]] = []

    def agent(message: dict[str, Any]) -> dict[str, Any]:
        if message["type"] == "start":
            for step in message["handoff"]["next_steps"]:
                if isinstance(step, dict):
                    queue.append((step["tool"], step["args"]))
            if not queue or queue[-1][0] != "submit":
                queue.append(
                    (
                        "submit",
                        {"recommendation": "ESCALATE", "open_conditions": [], "account": []},
                    )
                )
        tool, args = queue.pop(0)
        return {"type": "call", "tool": tool, "args": args}

    return agent
