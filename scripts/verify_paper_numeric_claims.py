#!/usr/bin/env python3
# ruff: noqa: E501
"""Bind every empirical number in the branded paper to released evidence.

This is deliberately stricter than an arithmetic check.  The cost-capped index,
scripted-control receipts, projection-ablation report, and four-judge summary are
verified first; then exact, derived manuscript fragments are required.  A number
cannot drift in prose or a table merely because the underlying JSON still adds up.

Bibliographic years, section/equation labels, model/version names, timestamps,
hash identifiers, and prospectively declared design parameters are not empirical
outcomes.  They remain reviewable in source, but do not enter this result ledger.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from gradia_universes.canonical import digest
from gradia_universes.cost_capped_results import verify_cost_capped_public_index

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "CONDITIONALLY-APPROVED-PAPER-DRAFT.md"
PDF = ROOT / "output" / "pdf" / "CONDITIONALLY-APPROVED-PRELIMINARY-RESULTS.pdf"
ALIGNMENT = (
    ROOT / "results" / "pre-results" / "conditionally-approved-four-judge-alignment.json"
)
PANEL = ROOT / "results" / "reference" / "panel.json"
RECEIPTS = ROOT / "results" / "reference" / "receipts"
STUDY_A = ROOT / "results" / "reference" / "study-a-engineering" / "report.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def normalized(value: str) -> str:
    value = value.replace("**", "").replace("`", "")
    return re.sub(
        r"\s+",
        " ",
        value.replace("\N{EN DASH}", "-").replace("\N{EM DASH}", "-"),
    ).strip()


def require_fragment(text: str, fragment: str, claim_id: str) -> None:
    require(normalized(fragment) in normalized(text), f"paper numeric claim drift:{claim_id}")


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def money(value: object) -> str:
    return f"${Decimal(str(value)):.2f}"


def load_alignment() -> dict[str, Any]:
    payload = json.loads(ALIGNMENT.read_text(encoding="utf-8"))
    n = payload["assignment_count"]
    require(payload["judge_count"] == 4, "alignment judge-count mismatch")
    require(sum(payload["consensus"].values()) == n, "alignment consensus mismatch")
    require(
        sum(payload["consensus_disposition"].values()) == n, "alignment disposition mismatch"
    )
    require(sum(payload["human_review_priority"].values()) == n, "alignment priority mismatch")
    require(
        sum(row["red"] for row in payload["criterion_family_distribution"]) == n,
        "alignment family mismatch",
    )
    require(
        sum(row["red"] for row in payload["task_distribution"]) == n, "alignment task mismatch"
    )
    require(
        payload["score_mutations"] == 0 and payload["advisory_only"],
        "alignment claim-boundary drift",
    )
    require(not any(payload["claim_boundary"].values()), "unsupported alignment claim enabled")
    return payload


def verify_reference_reports() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    panel_body = {key: value for key, value in panel.items() if key != "report_sha256"}
    require(panel["report_sha256"] == digest(panel_body), "scripted panel digest mismatch")
    receipts = [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(RECEIPTS.glob("*.json"))
    ]
    require(len(receipts) == panel["episode_count"], "scripted receipt count mismatch")
    require(
        {row["receipt_sha256"] for row in receipts} == set(panel["receipt_chain"]),
        "scripted receipt set mismatch",
    )

    study_a = json.loads(STUDY_A.read_text(encoding="utf-8"))
    study_body = {key: value for key, value in study_a.items() if key != "report_sha256"}
    require(study_a["report_sha256"] == digest(study_body), "projection report digest mismatch")
    require(
        study_a["confirmatory_study_status"] == "NOT_YET_RUN", "projection claim-boundary drift"
    )
    return panel, study_a, receipts


def main() -> None:
    index = verify_cost_capped_public_index(ROOT)
    summary = index["recomputed_summary"]
    alignment = load_alignment()
    panel, study_a, receipts = verify_reference_reports()
    source = PAPER.read_text(encoding="utf-8")

    physical = summary["physical_attempt_count"]
    gradable = summary["gradable_attempt_count"]
    excluded = summary["infrastructure_exclusion_count"]
    red = summary["machine_red_assignment_count"]
    green = summary["machine_green_assignment_count"]
    total = summary["machine_diagnostic_assignment_count"]
    usage = summary["usage"]

    claims: list[tuple[str, str]] = [
        (
            "execution_partition",
            f"{physical} physical attempts across four identity-pinned providers: {gradable} were gradable and {excluded} were infrastructure exclusions",
        ),
        (
            "perfect_reward",
            f"None of the {gradable} gradable attempts satisfied the exact perfect-rubric conjunction",
        ),
        (
            "usage_ledger",
            f"{usage['provider_call_count']:,} provider calls, {usage['input_token_count']:,} input tokens, {usage['output_token_count']:,} output tokens, and {money(usage['recorded_spend_usd'])}",
        ),
        (
            "gradable_trajectory_ledger",
            f"{usage['tool_action_count']:,} official tool actions and {usage['transcript_turn_count']:,} official transcript turns",
        ),
        (
            "engagement_partition",
            f"{summary['low_engagement_gradable_attempt_count']}/{gradable} gradable traces, including {summary['low_engagement_selected_primary_attempt_count']}/{summary['selected_primary_gradable_attempt_count']} selected primary attempts",
        ),
        (
            "diagnostic_partition",
            f"{total:,} applicable machine-diagnostic criterion assignments",
        ),
        ("diagnostic_green_red", f"Of these, {green} were green and {red} were red"),
        ("diagnostic_rate", f"This {100 * green / total:.1f}% diagnostic coverage"),
        (
            "four_judge_global",
            f"{alignment['unanimous_assignment_count']}/{red} ({pct(alignment['unanimous_assignment_rate'])}) assignments were unanimous",
        ),
        ("four_judge_kappa", f"kappa was {alignment['descriptive_fleiss_kappa']:.3f}"),
    ]

    coverage = index["recomputed_summary"]
    require(coverage["disclosed_overage_gradable_attempt_count"] == 16, "overage count drift")
    require_fragment(
        source,
        "Six of 20 provider-by-task cells contained an eligible same-runtime pair",
        "same_runtime_cells",
    )
    require_fragment(
        source,
        "Nine cells had only one gradable attempt and five were unobserved",
        "cell_missingness",
    )
    require_fragment(source, "Sixteen additional gradable executions", "overage_attempts")
    require_fragment(source, "Three runtime cohorts were present", "runtime_cohorts")

    cause_counts = Counter(
        row["infrastructure"]["category"]
        for row in index["attempts"]
        if row["disposition"] == "infrastructure_exclusion"
    )
    expected_causes = {
        "provider_authentication_refusal_before_admitted_response": 7,
        "provider_retryable_overload_refusal": 2,
        "provider_read_timeout": 6,
        "provider_read_error": 1,
        "provider_response_without_admitted_text": 2,
    }
    require(cause_counts == expected_causes, "infrastructure cause partition drift")
    require_fragment(
        source,
        "seven OpenAI HTTP 401 authentication refusals, two Anthropic HTTP 529 overload failures after bounded retries, six read timeouts, one OpenAI read error, and two xAI responses that completed transport but did not yield an admitted text payload",
        "infrastructure_causes",
    )
    require_fragment(
        source,
        f"accounted for **{money(usage['excluded_recorded_spend_usd'])}**",
        "excluded_spend",
    )

    provider_names = {
        "anthropic": "Opus 5",
        "gemini": "Gemini 3.1 Pro",
        "openai": "GPT-5.6-sol",
        "xai": "Grok 4.6",
    }
    for provider, display in provider_names.items():
        row = summary["providers"][provider]
        require_fragment(
            source,
            f"| {display} | {row['physical_attempt_count']} | {row['gradable_attempt_count']} | {row['infrastructure_exclusion_count']} | {row['perfect_rubric_pass_count']} | {money(row['recorded_spend_usd'])} |",
            f"provider_inventory:{provider}",
        )

    primary = [row for row in index["attempts"] if row["analysis_role"] == "selected_primary"]
    paired: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in primary:
        paired.setdefault((row["provider"], row["construct"]), []).append(row)
    paired = {
        key: sorted(rows, key=lambda row: row["ordinal"])
        for key, rows in paired.items()
        if len(rows) == 2
    }
    require(len(paired) == 6, "selected pair count drift")
    construct_names = {"document_truth": "Document", "epistemic_residue": "Residue"}
    tool_counts: list[int] = []
    for (provider, construct), rows in paired.items():
        sums = {
            key: sum(int(row["usage"][key]) for row in rows)
            for key in (
                "provider_call_count",
                "tool_action_count",
                "transcript_turn_count",
                "input_token_count",
                "output_token_count",
            )
        }
        spend = sum(
            (Decimal(row["usage"]["recorded_spend_usd"]) for row in rows), start=Decimal("0")
        )
        tool_counts.append(sums["tool_action_count"])
        require_fragment(
            source,
            f"| {provider_names[provider].replace(' Pro', '').replace('-sol', '')} / {construct_names[construct]} | {sums['provider_call_count']:,} | {sums['tool_action_count']:,} | {sums['transcript_turn_count']:,} | {sums['input_token_count']:,} | {sums['output_token_count']:,} | {money(spend)} |",
            f"selected_pair_usage:{provider}:{construct}",
        )
    ratio = max(tool_counts) / min(tool_counts)
    require_fragment(
        source, f"a {ratio:.1f}x range in selected-pair tool use", "tool_use_range"
    )

    task_names = {
        "document_truth": "Document truth under pushback",
        "epistemic_residue": "Epistemic residue",
        "authority_provenance": "Authority and fair judgment",
        "interruption_phase_response": "Temporal portfolio control",
        "successor_measured_handoff": "Honest handoff",
    }
    attempts_by_task = Counter(
        row["construct"] for row in index["attempts"] if row["disposition"] == "gradable"
    )
    green_by_task: Counter[str] = Counter()
    red_by_task: Counter[str] = Counter()
    for row in index["attempts"]:
        if row["disposition"] != "gradable":
            continue
        green_by_task[row["construct"]] += row["machine_diagnostics"]["green_criterion_count"]
        red_by_task[row["construct"]] += len(row["machine_diagnostics"]["red_criterion_ids"])
    for task, display in task_names.items():
        require_fragment(
            source,
            f"| {display} | {attempts_by_task[task]} | {green_by_task[task]} | {red_by_task[task]} | {green_by_task[task] + red_by_task[task]} |",
            f"task_diagnostics:{task}",
        )

    family_names = {
        "document_truth": "Document truth",
        "temporal_control": "Temporal control",
        "derived_state_freshness": "Derived-state freshness",
        "belief_revision": "Belief revision",
        "authority": "Authority",
        "evidence_provenance": "Evidence provenance",
        "terminal_integrity": "Terminal integrity",
        "portfolio_reasoning": "Portfolio reasoning",
        "action_safety": "Action safety",
        "completion": "Completion",
        "handoff_continuity": "Handoff continuity",
        "fairness_safety": "Fairness safety",
    }
    for family, count in summary["machine_red_family_counts"].items():
        require_fragment(
            source, f"| {family_names[family]} | {count} |", f"red_family:{family}"
        )

    red_criteria = Counter()
    for row in index["attempts"]:
        if row["disposition"] == "gradable":
            red_criteria.update(row["machine_diagnostics"]["red_criterion_ids"])
    near_universal = {
        criterion: count for criterion, count in red_criteria.items() if count >= 34
    }
    require(len(near_universal) == 8, "near-universal criterion count drift")
    require_fragment(source, "These eight denominators", "near_universal_count")
    require_fragment(
        source,
        "Eight exact criteria red on 34-37/37 attempts",
        "analytics_near_universal_count",
    )

    consensus = alignment["consensus"]
    dispositions = alignment["consensus_disposition"]
    priority = alignment["human_review_priority"]
    priority_total = priority["critical"] + priority["high"]
    require_fragment(
        source,
        f"{consensus['majority']} had a 3-1 majority, {consensus['plurality']} had a 2-1-1 plurality, and {consensus['tie']} tied 2-2",
        "judge_consensus_partition",
    )
    require_fragment(
        source,
        f"{priority_total}/{red} ({pct(priority_total / red)}) remained priority review work",
        "judge_priority_partition",
    )
    require_fragment(
        source,
        f"{dispositions['model_failure']} assignments, while {dispositions['measurement_defect']} favored a measurement defect, {dispositions['unresolved']} favored unresolved, and {dispositions['no_unique_disposition']} had no unique disposition",
        "judge_disposition_partition",
    )

    judge_names = {
        "claude-opus-5": "Claude Opus 5",
        "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview",
        "grok-4.6": "Grok 4.6",
        "gpt-5.6-sol": "GPT-5.6-sol",
    }
    for judge in alignment["judges"]:
        require_fragment(
            source,
            f"| {judge_names[judge['model_pin']]} | {judge['model_failure']} | {judge['measurement_defect']} | {judge['unresolved']} | {judge['mean_confidence']:.3f} |",
            f"judge_profile:{judge['model_pin']}",
        )
    shares = [row["model_failure"] / red for row in alignment["judges"]]
    require_fragment(
        source, f"ranged from {pct(min(shares))} to {pct(max(shares))}", "judge_share_range"
    )

    pair_names = {
        "claude-opus-5 :: gemini-3.1-pro-preview": "Claude-Gemini",
        "claude-opus-5 :: grok-4.6": "Claude-Grok",
        "claude-opus-5 :: gpt-5.6-sol": "Claude-GPT",
        "gemini-3.1-pro-preview :: grok-4.6": "Gemini-Grok",
        "gemini-3.1-pro-preview :: gpt-5.6-sol": "Gemini-GPT",
        "grok-4.6 :: gpt-5.6-sol": "Grok-GPT",
    }
    for row in alignment["pairwise"]:
        require_fragment(
            source,
            f"| {pair_names[row['judge_pair']]} | {pct(row['exact_label_agreement'])} | {row['evidence_anchor_jaccard']:.3f} | {pct(row['zero_shared_anchor_among_label_agreements'])} |",
            f"judge_pair:{row['judge_pair']}",
        )

    for row in alignment["criterion_family_distribution"]:
        require_fragment(
            source,
            f"| {family_names[row['family']]} | {row['red']} | {pct(row['red_share'])} | {pct(row['unanimity_rate'])} | {pct(row['no_unique_model_failure_rate'])} | {pct(row['critical_or_high_priority_rate'])} |",
            f"judge_family:{row['family']}",
        )

    task_alignment_names = {
        "document_truth": "Document truth",
        "epistemic_residue": "Epistemic residue",
        "authority": "Authority",
        "temporal_control": "Temporal control",
        "honest_handoff": "Honest handoff",
    }
    for row in alignment["task_distribution"]:
        require_fragment(
            source,
            f"| {task_alignment_names[row['task']]} | {row['red']}/{row['applicable']} | {pct(row['diagnostic_red_rate'])} | {row['red_per_attempt']:.1f} | {pct(row['unanimity_rate'])} | {pct(row['critical_or_high_priority_rate'])} |",
            f"judge_task:{row['task']}",
        )

    for claim_id, fragment in claims:
        require_fragment(source, fragment, claim_id)

    by_agent = {row["agent_policy"]: row for row in panel["by_agent"]}
    for policy, display in (
        ("interrupt_safe", "`interrupt_safe`"),
        ("stale_context", "`stale_context`"),
        ("message_credulous", "`message_credulous`"),
    ):
        row = by_agent[policy]
        require_fragment(
            source,
            f"| {display} | {row['passes']} | {row['episodes']} |",
            f"scripted_policy:{policy}",
        )
    require_fragment(
        source,
        f"The {len(receipts)} episodes contain {sum(len(row['acts']) for row in receipts)} recorded acts, {sum(len(row['evolution_witness']) for row in receipts)} event occurrences, three restore",
        "scripted_receipt_totals",
    )
    for row in study_a["policy_rows"]:
        require_fragment(
            source,
            f"| `{row['evidence_policy']}` | {row['invalid_forks']} | {row['projection_sensitive']} | {row['projection_insensitive']} | {row['faithful_parent_projection_changes']} |",
            f"projection_policy:{row['evidence_policy']}",
        )

    require(PDF.exists(), "branded paper PDF missing")
    pdf_text = subprocess.run(
        ["pdftotext", "-layout", str(PDF), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for claim_id, fragment in (
        ("rendered_execution", f"{physical} physical attempts"),
        ("rendered_usage", f"{usage['provider_call_count']:,} provider calls"),
        ("rendered_diagnostics", f"{green} were green and {red} were red"),
        (
            "rendered_judges",
            f"{alignment['unanimous_assignment_count']}/{red} ({pct(alignment['unanimous_assignment_rate'])})",
        ),
        ("rendered_tool_range", f"{ratio:.1f}x range"),
    ):
        require_fragment(pdf_text, fragment, claim_id)

    print(
        "verified branded-paper numeric claims; "
        f"attempts={physical}; gradable={gradable}; exclusions={excluded}; "
        f"diagnostics={total}; red={red}; judge_assignments={alignment['assignment_count']}; "
        f"scripted_receipts={len(receipts)}; projection_forks={study_a['invalid_fork_count']}"
    )


if __name__ == "__main__":
    main()
