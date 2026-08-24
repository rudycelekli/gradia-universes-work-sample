"""Verify the redacted public evidence index for the cost-capped live panel.

The raw provider payloads and full transcripts are deliberately not public.  This
module makes the released aggregate independently recomputable from a smaller,
digest-bound projection: attempt identity, disposition, runtime cohort, usage,
diagnostic criterion states, and non-reward engagement descriptors.
"""

from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from .canonical import digest

SCHEMA = "conditionally-approved-public-evidence-index.v1"
DEFAULT_INDEX = Path("results/pre-results/conditionally-approved-cost-capped-index.json")


def _decimal_sum(values: list[object]) -> str:
    total = sum((Decimal(str(value)) for value in values), start=Decimal("0"))
    return format(total.quantize(Decimal("0.000001")), "f")


def engagement_annotation(attempt: dict[str, Any]) -> str:
    """Return the deterministic, post-hoc engagement descriptor.

    This annotation is never a score and never changes denominator eligibility.
    It only marks a trace that used under ten percent of the scripted reference
    control's actions while observing no source, attachment, or world event.
    """

    if attempt["disposition"] != "gradable":
        return "not_applicable_infrastructure_exclusion"
    engagement = attempt["engagement"]
    low_action = (
        10 * engagement["tool_action_count"]
        < engagement["scripted_reference_control_action_count"]
    )
    no_bound_work = all(
        engagement[key] == 0
        for key in (
            "observed_source_reference_count",
            "inspected_attachment_count",
            "applied_world_event_count",
        )
    )
    if low_action and no_bound_work:
        return "low_engagement_no_sources_attachments_or_events"
    return "substantive_trace_evidence_present"


def recompute_cost_capped_summary(index: dict[str, Any]) -> dict[str, Any]:
    attempts = index["attempts"]
    registry = index["criterion_registry"]
    gradable = [row for row in attempts if row["disposition"] == "gradable"]
    excluded = [row for row in attempts if row["disposition"] == "infrastructure_exclusion"]
    primary = [row for row in gradable if row["analysis_role"] == "selected_primary"]
    overage = [row for row in gradable if row["analysis_role"] == "disclosed_overage"]

    family_counts: Counter[str] = Counter()
    red_count = 0
    diagnostic_total = 0
    diagnostic_passed = 0
    low_engagement = 0
    low_engagement_primary = 0
    for row in attempts:
        expected = engagement_annotation(row)
        if row["engagement"]["annotation"] != expected:
            raise ValueError(f"engagement_annotation_mismatch:{row['attempt_id']}")
        if row["engagement"]["affects_reward_or_disposition"]:
            raise ValueError(f"engagement_descriptor_may_not_score:{row['attempt_id']}")
        if expected == "low_engagement_no_sources_attachments_or_events":
            low_engagement += 1
            if row["analysis_role"] == "selected_primary":
                low_engagement_primary += 1

        if row["disposition"] == "gradable":
            red = row["machine_diagnostics"]["red_criterion_ids"]
            if len(red) != len(set(red)):
                raise ValueError(f"duplicate_red_criterion:{row['attempt_id']}")
            unknown = sorted(set(red) - set(registry))
            if unknown:
                raise ValueError(f"unknown_red_criterion:{row['attempt_id']}:{unknown}")
            total = row["machine_diagnostics"]["applicable_criterion_count"]
            passed = row["machine_diagnostics"]["green_criterion_count"]
            if passed + len(red) != total:
                raise ValueError(f"diagnostic_count_mismatch:{row['attempt_id']}")
            red_count += len(red)
            diagnostic_total += total
            diagnostic_passed += passed
            family_counts.update(registry[criterion]["family"] for criterion in red)
        elif row["machine_diagnostics"] is not None:
            raise ValueError(f"infrastructure_has_machine_diagnostics:{row['attempt_id']}")

    usage_fields = (
        "provider_call_count",
        "input_token_count",
        "output_token_count",
        "tool_action_count",
        "transcript_turn_count",
    )
    usage_totals: dict[str, Any] = {
        key: sum(int(row["usage"][key]) for row in attempts) for key in usage_fields
    }
    usage_totals["recorded_spend_usd"] = _decimal_sum(
        [row["usage"]["recorded_spend_usd"] for row in attempts]
    )
    usage_totals["excluded_recorded_spend_usd"] = _decimal_sum(
        [row["usage"]["recorded_spend_usd"] for row in excluded]
    )

    providers: dict[str, dict[str, Any]] = {}
    for provider in sorted({row["provider"] for row in attempts}):
        rows = [row for row in attempts if row["provider"] == provider]
        provider_gradable = [row for row in rows if row["disposition"] == "gradable"]
        providers[provider] = {
            "physical_attempt_count": len(rows),
            "gradable_attempt_count": len(provider_gradable),
            "infrastructure_exclusion_count": len(rows) - len(provider_gradable),
            "perfect_rubric_pass_count": sum(
                row["official_binary_reward"] == 1 for row in provider_gradable
            ),
            "recorded_spend_usd": _decimal_sum(
                [row["usage"]["recorded_spend_usd"] for row in rows]
            ),
        }

    return {
        "physical_attempt_count": len(attempts),
        "gradable_attempt_count": len(gradable),
        "infrastructure_exclusion_count": len(excluded),
        "perfect_rubric_pass_count": sum(
            row["official_binary_reward"] == 1 for row in gradable
        ),
        "selected_primary_gradable_attempt_count": len(primary),
        "disclosed_overage_gradable_attempt_count": len(overage),
        "machine_diagnostic_assignment_count": diagnostic_total,
        "machine_green_assignment_count": diagnostic_passed,
        "machine_red_assignment_count": red_count,
        "machine_red_family_counts": dict(sorted(family_counts.items())),
        "low_engagement_gradable_attempt_count": low_engagement,
        "low_engagement_selected_primary_attempt_count": low_engagement_primary,
        "usage": usage_totals,
        "providers": providers,
    }


def verify_cost_capped_public_index(root: Path) -> dict[str, Any]:
    path = root / DEFAULT_INDEX
    index = json.loads(path.read_bytes())
    if index.get("schema_version") != SCHEMA:
        raise ValueError("cost_capped_index_schema_mismatch")
    claimed = index.get("index_sha256")
    body = {key: value for key, value in index.items() if key != "index_sha256"}
    if claimed != digest(body):
        raise ValueError("cost_capped_index_digest_mismatch")
    attempts = index.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError("cost_capped_attempts_missing")
    attempt_ids = [row["attempt_id"] for row in attempts]
    if len(attempt_ids) != len(set(attempt_ids)):
        raise ValueError("cost_capped_attempt_id_duplicate")
    expected_summary = recompute_cost_capped_summary(index)
    if index.get("recomputed_summary") != expected_summary:
        raise ValueError("cost_capped_summary_mismatch")
    if expected_summary["physical_attempt_count"] != 55:
        raise ValueError("cost_capped_physical_count_mismatch")
    if expected_summary["gradable_attempt_count"] != 37:
        raise ValueError("cost_capped_gradable_count_mismatch")
    if expected_summary["infrastructure_exclusion_count"] != 18:
        raise ValueError("cost_capped_exclusion_count_mismatch")
    if expected_summary["machine_red_assignment_count"] != 889:
        raise ValueError("cost_capped_red_assignment_count_mismatch")
    return cast(dict[str, Any], index)
