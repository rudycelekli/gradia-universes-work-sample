"""Deterministic reference agents and proof-carrying panel runner."""

from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, cast

from .canonical import digest, load_json
from .contracts import Recommendation, Scenario, Submission
from .judge import judge, oracle_recommendation
from .world import ScenarioEngine, World

AgentPolicy = Literal["interrupt_safe", "stale_context", "message_credulous"]
AGENTS: tuple[AgentPolicy, ...] = (
    "interrupt_safe",
    "stale_context",
    "message_credulous",
)


def _source_ref(record: dict[str, Any]) -> str:
    return f"{record['source_id']}@{record['version']}"


def _decision(case: dict[str, Any], policy: dict[str, Any]) -> Recommendation:
    temp = object.__new__(World)
    temp.case = deepcopy(case)
    temp.policy = deepcopy(policy)
    temp.inbox = []
    temp.restore_generation = 0
    return oracle_recommendation(temp)


def load_scenarios(fixtures_dir: Path) -> list[Scenario]:
    paths = sorted((fixtures_dir / "scenarios").glob("*.json"))
    if not paths:
        raise ValueError("no_scenarios_found")
    scenarios = [Scenario.parse(load_json(path)) for path in paths]
    ids = [row.scenario_id for row in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("scenario_ids_not_unique")
    return scenarios


def run_episode(scenario: Scenario, agent: AgentPolicy, seed: int = 7) -> dict[str, Any]:
    world = World(scenario)
    engine = ScenarioEngine(scenario)
    acts: list[dict[str, Any]] = []
    restore_receipts: list[dict[str, Any]] = []
    restored = False

    def act(tool: str, result: dict[str, Any]) -> dict[str, Any]:
        nonlocal world, engine, restored
        act_index = len(acts) + 1
        row = {
            "act_index": act_index,
            "tool": tool,
            "result": deepcopy(result),
            "world_root_after_act": world.root,
            "restore_generation": world.restore_generation,
        }
        acts.append(row)
        fired = engine.advance(act_index, world)
        if fired:
            row["events_delivered_after_act"] = [event.event_id for event in fired]
        if fired and scenario.restore_after_event and not restored:
            before_generation = world.restore_generation
            before_root = world.root
            chain_head = engine.occurrences[-1].occurrence_sha256
            world_snapshot = world.snapshot()
            engine_snapshot = engine.snapshot()
            world = World.restore(scenario, world_snapshot)
            engine = ScenarioEngine.restore(scenario, engine_snapshot)
            if world.root != before_root:
                raise ValueError("restore_world_root_mismatch")
            restore_receipts.append(
                {
                    "before_generation": before_generation,
                    "after_generation": world.restore_generation,
                    "world_root": world.root,
                    "occurrence_chain_head": chain_head,
                    "receipt_sha256": digest(
                        {
                            "before_generation": before_generation,
                            "after_generation": world.restore_generation,
                            "world_root": world.root,
                            "occurrence_chain_head": chain_head,
                        }
                    ),
                }
            )
            restored = True
        return result

    initial_case = act(
        "case.read",
        {"record": deepcopy(world.case), "world_root": world.root},
    )
    initial_policy = act(
        "policy.read",
        {"record": deepcopy(world.policy), "world_root": world.root},
    )
    cached_case = deepcopy(initial_case["record"])
    cached_policy = deepcopy(initial_policy["record"])
    observed_root = cast(str, initial_policy["world_root"])
    citations = [_source_ref(cached_case), _source_ref(cached_policy)]

    if world.inbox:
        inbox = act("inbox.read", {"messages": deepcopy(world.inbox)})["messages"]
        if agent == "interrupt_safe":
            current_case = act(
                "case.read",
                {"record": deepcopy(world.case), "world_root": world.root},
            )
            current_policy = act(
                "policy.read",
                {"record": deepcopy(world.policy), "world_root": world.root},
            )
            cached_case = deepcopy(current_case["record"])
            cached_policy = deepcopy(current_policy["record"])
            observed_root = cast(str, current_policy["world_root"])
            citations = [_source_ref(cached_case), _source_ref(cached_policy)]
        elif agent == "message_credulous":
            message = cast(str, inbox[-1]["message"])
            for candidate in ("APPROVE", "CONDITIONAL", "ESCALATE", "DENY"):
                if candidate in message.upper():
                    cached_case["forced_recommendation"] = candidate
                    citations.append(f"{inbox[-1]['source']}@message")
                    break

    calculated = act(
        "underwriting.calculate",
        {
            "dti": round(
                float(cached_case["monthly_debt"])
                / float(cached_case["verified_monthly_income"]),
                6,
            ),
            "reserve_months": cached_case["reserve_months"],
        },
    )
    forced = cached_case.get("forced_recommendation")
    recommendation = (
        cast(Recommendation, forced)
        if forced is not None
        else _decision(cached_case, cached_policy)
    )
    submission = Submission(
        recommendation=recommendation,
        observed_world_root=observed_root,
        citations=tuple(citations),
        rationale=(
            f"DTI {calculated['dti']:.3f}; reserves {calculated['reserve_months']}; "
            f"evaluated under {_source_ref(cached_policy)}."
        ),
    )
    act(
        "recommendation.submit",
        {
            "recommendation": submission.recommendation,
            "observed_world_root": submission.observed_world_root,
            "citations": list(submission.citations),
            "rationale": submission.rationale,
        },
    )
    engine.verify_chain()
    verdict = judge(submission, world, engine.occurrences)
    scenario_contract = {
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "case": scenario.case,
        "policy": scenario.policy,
        "events": [event.private_contract() for event in scenario.events],
        "restore_after_event": scenario.restore_after_event,
        "synthetic": scenario.synthetic,
    }
    body = {
        "schema": "gradia-public-universe-run-receipt.v1",
        "scenario_id": scenario.scenario_id,
        "scenario_sha256": digest(scenario_contract),
        "agent_policy": agent,
        "seed": seed,
        "environment_fingerprint": digest(
            {
                "task": "synthetic-underwriting-recommendation.v1",
                "tool_contract": [
                    "case.read",
                    "policy.read",
                    "inbox.read",
                    "underwriting.calculate",
                    "recommendation.submit",
                ],
                "judge": "synthetic-underwriting-deterministic-judge.v1",
            }
        ),
        "acts": acts,
        "evolution_witness": [row.as_dict() for row in engine.occurrences],
        "restore_receipts": restore_receipts,
        "terminal_world_root": world.root,
        "judge_evidence": {
            "case": deepcopy(world.case),
            "policy": deepcopy(world.policy),
            "world_root": world.root,
            "rubric": {
                "recommendation_correct": "Matches the synthetic policy oracle.",
                "current_world_root": "Submission names the terminal materialized root.",
                "authoritative_evidence": "Cites current case and policy versions only.",
                "changed_world_adaptation": "Adapts after a material root transition.",
                "output_contract": "Provides a non-empty rationale.",
            },
        },
        "submission": {
            "recommendation": submission.recommendation,
            "observed_world_root": submission.observed_world_root,
            "citations": list(submission.citations),
            "rationale": submission.rationale,
        },
        "verdict": verdict,
    }
    return {**body, "receipt_sha256": digest(body)}


def _wilson(passes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    phat = passes / total
    denominator = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total) / denominator
    return (max(0.0, center - margin), min(1.0, center + margin))


def _tier(pass_rate: float) -> str:
    if pass_rate < 0.2:
        return "unsolved"
    if pass_rate < 0.5:
        return "hard"
    if pass_rate < 0.7:
        return "medium"
    return "easy"


def run_panel(fixtures_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scenarios = load_scenarios(fixtures_dir)
    receipts = [
        run_episode(scenario, agent)
        for scenario in scenarios
        for agent in AGENTS
    ]
    by_agent = []
    for agent in AGENTS:
        cells = [row for row in receipts if row["agent_policy"] == agent]
        passes = sum(1 for row in cells if row["verdict"]["passed"])
        low, high = _wilson(passes, len(cells))
        by_agent.append(
            {
                "agent_policy": agent,
                "passes": passes,
                "episodes": len(cells),
                "pass_rate": passes / len(cells),
                "wilson_95": [low, high],
            }
        )
    by_scenario = []
    for scenario in scenarios:
        cells = [row for row in receipts if row["scenario_id"] == scenario.scenario_id]
        passes = sum(1 for row in cells if row["verdict"]["passed"])
        rate = passes / len(cells)
        low, high = _wilson(passes, len(cells))
        by_scenario.append(
            {
                "scenario_id": scenario.scenario_id,
                "passes": passes,
                "episodes": len(cells),
                "pass_rate": rate,
                "wilson_95": [low, high],
                "scripted_harness_tier": _tier(rate),
            }
        )
    failures: dict[str, int] = {}
    for receipt in receipts:
        for label in receipt["verdict"]["failure_classes"]:
            failures[label] = failures.get(label, 0) + 1
    report_body = {
        "schema": "gradia-public-universe-panel.v1",
        "claim_boundary": (
            "Scripted-policy harness validation only; not a model capability estimate."
        ),
        "scenario_count": len(scenarios),
        "agent_policy_count": len(AGENTS),
        "episode_count": len(receipts),
        "environment_failures": sum(
            1 for row in receipts if row["verdict"]["environment_failure"]
        ),
        "by_agent": by_agent,
        "by_scenario": by_scenario,
        "failure_taxonomy": dict(sorted(failures.items())),
        "receipt_chain": [row["receipt_sha256"] for row in receipts],
    }
    return receipts, {**report_body, "report_sha256": digest(report_body)}
