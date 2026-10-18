from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest

from gradia_universes.canonical import load_json
from gradia_universes.loanworld.adapter import run_python_agent
from gradia_universes.loanworld.forks import fork_by_id
from gradia_universes.loanworld.live import Budget, ModelAgent, tool_definitions
from gradia_universes.loanworld.schema import LoanScenario
from gradia_universes.loanworld.tools import TOOL_SPECS

ROOT = Path(__file__).resolve().parents[1]
LW = ROOT / "fixtures" / "loanworld"


@dataclass
class Usage:
    input_tokens: int = 1000
    cache_creation_input_tokens: int = 2000
    cache_read_input_tokens: int = 5000
    output_tokens: int = 500


@dataclass
class Block:
    type: str
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    text: str = ""


@dataclass
class Response:
    content: list[Block]
    stop_reason: str
    usage: Usage = field(default_factory=Usage)


class FakeMessages:
    """Scripted stand-in for client.messages: no network, no spend."""

    def __init__(self, script: list[Response]) -> None:
        self.script = script
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Response:
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.script.pop(0)


class FakeClient:
    def __init__(self, script: list[Response]) -> None:
        self.messages = FakeMessages(script)


class NoImages:
    manifest_sha256 = "none"

    def block(self, upload_id: str, page: int) -> dict[str, Any] | None:
        return None


def _bundle() -> dict[str, Any]:
    parent = load_json(LW / "parents" / "loanworld-parent-dev-001.json")
    contract = load_json(LW / "counterparts" / "loanworld-parent-dev-001.json")
    return fork_by_id(parent, contract, "FK-00")


def _tool(name: str, args: dict[str, Any], n: int) -> Response:
    return Response([Block("tool_use", id=f"t{n}", name=name, input=args)], "tool_use")


def _run(script: list[Response], cap: float = 5.0, episode_cap: float = 2.0) -> Any:
    bundle = _bundle()
    client = FakeClient(script)
    budget = Budget(cap_usd=cap, model="claude-opus-5-5")
    agent = ModelAgent(
        client,
        "claude-opus-5-5",
        "medium",
        16000,
        bundle["scenario"],
        cast(Any, NoImages()),
        budget,
        "FK-00",
        episode_cap_usd=episode_cap,
    )
    result = run_python_agent(
        LoanScenario.parse(bundle["scenario"]), agent, counterparts=bundle["counterparts"]
    )
    return result, agent, budget, client


def test_tool_definitions_cover_every_tool() -> None:
    names = [t["name"] for t in tool_definitions()]
    assert names == list(TOOL_SPECS)


def test_agent_meters_usage_and_submits() -> None:
    script = [
        _tool("get_conditions", {}, 1),
        _tool(
            "submit", {"recommendation": "ESCALATE", "open_conditions": [], "account": []}, 2
        ),
    ]
    result, _agent, budget, client = _run(script)
    assert result["outcome"] == "terminal"
    expected = (1000 * 4 + 2000 * 5 + 5000 * 0.2 + 500 * 20) / 1e6
    assert budget.spent_usd == pytest.approx(2 * expected)
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert call["output_config"] == {"effort": "medium"}
    assert "fallbacks" not in call
    second = client.messages.calls[1]["messages"]
    assert second[-1]["content"][0]["type"] == "tool_result"


def test_budget_guard_stops_before_crossing_the_cap() -> None:
    script = [_tool("get_conditions", {}, n) for n in range(50)]
    result, agent, budget, _ = _run(script, cap=0.40)
    assert result["outcome"] == "censored"
    assert agent.stop == "budget_cap"
    assert budget.spent_usd <= 0.40


def test_episode_cap_and_refusal_are_censored() -> None:
    result, agent, _, _ = _run(
        [_tool("get_conditions", {}, n) for n in range(50)], episode_cap=0.40
    )
    assert agent.stop == "episode_budget_cap" and result["outcome"] == "censored"
    refused = Response([], "refusal")
    result, agent, _, _ = _run([refused])
    assert agent.stop == "model_refusal" and result["outcome"] == "censored"


def test_text_only_turns_are_nudged_then_censored() -> None:
    chat = Response([Block("text", text="Let me think.")], "end_turn")
    _result, agent, _, client = _run([chat, chat, chat])
    assert agent.stop == "model_stopped_without_submit"
    assert len(client.messages.calls) == 3


def test_budget_ledger_appends_every_request(tmp_path: Path) -> None:
    ledger = tmp_path / "spend-ledger.jsonl"
    budget = Budget(cap_usd=5.0, model="claude-opus-5-5", ledger_path=ledger)
    budget.record("FK-00", Usage(), "tool_use")
    budget.record("FK-00", Usage(), "end_turn")
    lines = ledger.read_text().splitlines()
    assert len(lines) == 2 and '"stop_reason": "end_turn"' in lines[1]


def test_live_regrade_is_bound_to_recorded_proof_packs() -> None:
    from gradia_universes.canonical import canonical_bytes
    from gradia_universes.loanworld.live import regrade_live

    committed = load_json(ROOT / "results" / "loanworld" / "live" / "regrade-oracle-0.4.2.json")
    rerun = regrade_live(ROOT)
    assert canonical_bytes(rerun) == canonical_bytes(committed)
    assert all(e["replay_bound_to_proof_pack"] for e in rerun["episodes"])
    assert rerun["status"].startswith("POST-HOC")
