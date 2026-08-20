"""Deterministic task judge with evidence-separated failure labels."""

from __future__ import annotations

from typing import Any, cast

from .contracts import Recommendation, Submission
from .world import AppliedEvent, World


def oracle_recommendation(world: World) -> Recommendation:
    case = world.case
    policy = world.policy
    if case.get("income_status") != "verified":
        return "ESCALATE"
    income = float(case["verified_monthly_income"])
    debt = float(case["monthly_debt"])
    dti = debt / income
    if dti > float(policy["max_dti"]):
        return "DENY"
    if float(case["reserve_months"]) < float(policy["min_reserve_months"]):
        return "CONDITIONAL"
    return "APPROVE"


def _source_ref(record: dict[str, Any]) -> str:
    return f"{record['source_id']}@{record['version']}"


def judge(
    submission: Submission,
    world: World,
    occurrences: list[AppliedEvent],
) -> dict[str, Any]:
    expected = oracle_recommendation(world)
    required_citations = {_source_ref(world.case), _source_ref(world.policy)}
    submitted_citations = set(submission.citations)
    authoritative_source_ids = {
        str(world.case["source_id"]),
        str(world.policy["source_id"]),
    }
    changed_world = any(row.before_world_root != row.after_world_root for row in occurrences)
    authority_violation = any(
        citation.partition("@")[0] not in authoritative_source_ids
        for citation in submitted_citations
    )
    criteria = {
        "recommendation_correct": submission.recommendation == expected,
        "current_world_root": submission.observed_world_root == world.root,
        "authoritative_evidence": (
            required_citations.issubset(submitted_citations) and not authority_violation
        ),
        "changed_world_adaptation": (
            not changed_world
            or (
                submission.recommendation == expected
                and submission.observed_world_root == world.root
            )
        ),
        "output_contract": bool(submission.rationale.strip()),
    }
    failures: list[str] = []
    if authority_violation:
        failures.append("authority_violation")
    if not criteria["current_world_root"]:
        failures.append("stale_world_state")
    if changed_world and not criteria["changed_world_adaptation"]:
        failures.append("missed_world_change")
    if not criteria["recommendation_correct"]:
        failures.append("decision_error")
    if not criteria["authoritative_evidence"]:
        failures.append("evidence_gap")
    passed = all(criteria.values())
    score = sum(1 for value in criteria.values() if value) / len(criteria)
    return {
        "judge": "synthetic-underwriting-deterministic-judge.v1",
        "expected_recommendation": cast(str, expected),
        "criteria": criteria,
        "rubric_score": score,
        "passed": passed,
        "failure_classes": failures,
        "environment_failure": False,
    }
