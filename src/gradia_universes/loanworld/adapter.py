"""System-mode adapter: run any agent stack against a LoanWorld episode over stdio.

Protocol ``gradia.loanworld.stdio.v0`` (one JSON object per line):

harness -> agent  {"type": "start", "protocol", "scenario_id", "max_acts", "tools",
                   "projection"}
agent  -> harness {"type": "call", "tool": "<name>", "args": {...}}
harness -> agent  {"type": "result", "act": n, "response": {...}}
harness -> agent  {"type": "end", "outcome": "terminal" | "censored"}

The agent never sees case truth, private trap data or authenticity labels; it
only sees the projection and tool results. Infrastructure failures (timeout,
malformed output, process exit, act budget) are *censored* and reported apart
from model outcomes, never scored as zeros.
"""

from __future__ import annotations

import json
import selectors
import subprocess
import time
from collections.abc import Callable
from typing import Any

from .schema import LoanScenario
from .tools import TOOL_SPECS, LoanWorldSession

PROTOCOL = "gradia.loanworld.stdio.v0"

TOOL_DESCRIPTIONS: dict[str, str] = {
    "get_projection": "Everything visible now: clock, uploads, inbox, conditions, services, "
    "LOS fields and values, policy, contacts.",
    "list_uploads": "Received uploads with page counts, sender and status.",
    "get_page": "One page: size, media, the PDF text layer if any (may disagree with pixels), "
    "and a pixel render reference.",
    "read_inbox": "Messages and notices since an index.",
    "request_document": "Ask a party for a document. External effect.",
    "send_message": "Message a party on a channel. External effect.",
    "order_service": "Order credit, aus, appraisal, title, flood or verbal_voe.",
    "get_conditions": "Current condition ledger.",
    "clear_condition": "Clear a condition; needs citations to current evidence.",
    "add_condition": "Open a new condition with citations.",
    "write_los_field": "Write one LOS field with a citation.",
    "flag": "Raise a coded flag with citations.",
    "escalate": "Hand a question to a human with a reason.",
    "submit": "Terminal: recommendation, open conditions, and an account of cited claims.",
}


def tool_manifest() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": TOOL_DESCRIPTIONS[name],
            "args": {
                arg: {"type": kind, "required": required}
                for arg, (kind, required) in spec.items()
            },
        }
        for name, spec in TOOL_SPECS.items()
    ]


def _start_message(session: LoanWorldSession) -> dict[str, Any]:
    return {
        "type": "start",
        "protocol": PROTOCOL,
        "scenario_id": session.scenario.scenario_id,
        "max_acts": session.max_acts,
        "tools": tool_manifest(),
        "projection": session.world.projection(),
    }


def _parse_call(raw: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(raw, dict) or raw.get("type") != "call":
        return None
    tool, args = raw.get("tool"), raw.get("args", {})
    if not isinstance(tool, str) or not isinstance(args, dict):
        return None
    return tool, args


def _result(session: LoanWorldSession, outcome: str, reason: str | None) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "outcome": outcome,
        "censor_reason": reason,
        "acts": session.act,
        "proof_pack": session.proof_pack(),
        # Harness-side only (never sent to the agent): the oracle binds this to the pack.
        "final_state": session.snapshot(),
    }


def run_python_agent(
    scenario: LoanScenario,
    agent: Callable[[dict[str, Any]], dict[str, Any]],
    max_acts: int = 200,
    counterparts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """In-process variant of the same protocol, for scripted and reference policies."""
    session = LoanWorldSession(scenario, max_acts, counterparts)
    message = _start_message(session)
    while True:
        call = _parse_call(agent(message))
        if call is None:
            return _result(session, "censored", "malformed_agent_message")
        response = session.call(*call)
        if session.terminal is not None:
            return _result(session, "terminal", None)
        if response.get("error") == "act_budget_exhausted":
            return _result(session, "censored", "act_budget_exhausted")
        message = {"type": "result", "act": session.act, "response": response}


def run_stdio_episode(
    scenario: LoanScenario,
    command: list[str],
    *,
    max_acts: int = 200,
    step_timeout_s: float = 30.0,
    total_timeout_s: float = 1800.0,
    counterparts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = LoanWorldSession(scenario, max_acts, counterparts)
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    assert process.stdin is not None and process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    def send(message: dict[str, Any]) -> bool:
        assert process.stdin is not None
        try:
            process.stdin.write(json.dumps(message, sort_keys=True) + "\n")
            process.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            return False

    def finish(outcome: str, reason: str | None) -> dict[str, Any]:
        send({"type": "end", "outcome": outcome})
        try:
            if process.stdin is not None:
                process.stdin.close()
        except (BrokenPipeError, OSError):
            pass  # the agent already went away; that is what is being censored
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        selector.close()
        return _result(session, outcome, reason)

    if not send(_start_message(session)):
        return finish("censored", "agent_not_accepting_input")
    while True:
        remaining = total_timeout_s - (time.monotonic() - started)
        if remaining <= 0:
            return finish("censored", "total_timeout")
        if not selector.select(timeout=min(step_timeout_s, remaining)):
            return finish("censored", "step_timeout")
        line = process.stdout.readline()
        if not line:
            return finish("censored", "agent_exited")
        try:
            call = _parse_call(json.loads(line))
        except json.JSONDecodeError:
            call = None
        if call is None:
            return finish("censored", "malformed_agent_message")
        response = session.call(*call)
        if session.terminal is not None:
            return finish("terminal", None)
        if response.get("error") == "act_budget_exhausted":
            return finish("censored", "act_budget_exhausted")
        if not send({"type": "result", "act": session.act, "response": response}):
            return finish("censored", "agent_not_accepting_input")
