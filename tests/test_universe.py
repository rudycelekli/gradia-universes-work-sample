from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from gradia_universes.axis_candidates import (
    build_axis_validation,
    generate_axis_candidates,
    render_axis_validation,
    verify_axis_artifacts,
)
from gradia_universes.canonical import canonical_bytes, digest, load_json
from gradia_universes.cli import _verify_release_text_boundary
from gradia_universes.contracts import Scenario
from gradia_universes.frontier import (
    FrontierEngine,
    FrontierScenario,
    FrontierWorld,
    analyze_five_attempt_panel,
    frontier_admission_report,
    frontier_judge_validation_report,
    load_frontier_scenarios,
    oracle_packet,
    run_frontier_live_episode,
)
from gradia_universes.gradia_client import REQUIRED_PATHS, GradiaClient, Response
from gradia_universes.human_review import CRITERIA, agreement, build_packet
from gradia_universes.live_runner import (
    BudgetStop,
    Completion,
    ProviderFailure,
    run_live_episode,
)
from gradia_universes.preregistration import (
    build_frontier_preregistration,
    verify_frontier_preregistration,
)
from gradia_universes.providers import (
    MAX_PROMPT_BYTES,
    CappedProviderBackend,
    ProviderName,
    SpendPolicy,
)
from gradia_universes.public_bundle import build_public_bundle, verify_public_bundle
from gradia_universes.runner import AGENTS, load_scenarios, run_episode, run_panel
from gradia_universes.study_a import build_study_a, render_study_a
from gradia_universes.world import ScenarioEngine, World

ROOT = Path(__file__).resolve().parents[1]


def scenarios() -> dict[str, Scenario]:
    return {row.scenario_id: row for row in load_scenarios(ROOT / "fixtures")}


def test_canonical_numbers_survive_a_javascript_json_round_trip() -> None:
    value = {
        "integer_rate": 1.0,
        "negative_zero": -0.0,
        "fractional_rate": 0.4,
        "nested": [2.0, {"value": 0.25}],
    }
    assert canonical_bytes(value) == (
        b'{"fractional_rate":0.4,"integer_rate":1,"negative_zero":0,'
        b'"nested":[2,{"value":0.25}]}'
    )


def test_five_synthetic_scenarios_are_canonical_and_unique() -> None:
    rows = scenarios()
    assert list(rows) == [
        "static-control",
        "document-addition",
        "policy-revision",
        "retraction-across-restore",
        "authority-conflict",
    ]
    assert all(row.synthetic for row in rows.values())
    for path in sorted((ROOT / "fixtures" / "scenarios").glob("*.json")):
        assert canonical_bytes(load_json(path)) + b"\n" == path.read_bytes()


def test_student_projection_excludes_trigger_and_private_mutation() -> None:
    event = scenarios()["policy-revision"].events[0]
    projection = event.observation.public_view(event.event_id)
    rendered = json.dumps(projection)
    assert "after_act" not in rendered
    assert "max_dti" not in rendered
    assert "updates" not in rendered
    assert projection["authority"] == "authoritative"


def test_root_receipt_distinguishes_mutation_from_notice() -> None:
    rows = scenarios()
    changed = run_episode(rows["document-addition"], "interrupt_safe")
    notice = run_episode(rows["authority-conflict"], "interrupt_safe")
    changed_occurrence = changed["evolution_witness"][0]
    notice_occurrence = notice["evolution_witness"][0]
    assert changed_occurrence["before_world_root"] != changed_occurrence["after_world_root"]
    assert notice_occurrence["before_world_root"] == notice_occurrence["after_world_root"]


def test_retraction_survives_restore_and_occurs_exactly_once() -> None:
    receipt = run_episode(scenarios()["retraction-across-restore"], "interrupt_safe")
    assert [row["event_id"] for row in receipt["evolution_witness"]] == [
        "income-verification-retracted"
    ]
    assert receipt["restore_receipts"] == [
        {
            **receipt["restore_receipts"][0],
            "before_generation": 0,
            "after_generation": 1,
        }
    ]
    assert receipt["verdict"]["passed"] is True
    assert receipt["submission"]["recommendation"] == "ESCALATE"


def test_tampered_occurrence_chain_is_refused() -> None:
    scenario = scenarios()["policy-revision"]
    world = World(scenario)
    engine = ScenarioEngine(scenario)
    engine.advance(2, world)
    state = engine.snapshot()
    state["occurrences"][0]["after_world_root"] = "0" * 64
    with pytest.raises(ValueError, match="occurrence_digest_mismatch"):
        ScenarioEngine.restore(scenario, state)


def test_panel_separates_safe_stale_and_credulous_policies() -> None:
    receipts, panel = run_panel(ROOT / "fixtures")
    assert len(receipts) == 15
    assert [row["agent_policy"] for row in panel["by_agent"]] == list(AGENTS)
    assert [(row["passes"], row["episodes"]) for row in panel["by_agent"]] == [
        (5, 5),
        (2, 5),
        (1, 5),
    ]
    assert panel["environment_failures"] == 0
    assert panel["failure_taxonomy"] == {
        "authority_violation": 1,
        "decision_error": 6,
        "evidence_gap": 7,
        "missed_world_change": 6,
        "stale_world_state": 6,
    }


def test_stale_authoritative_version_is_not_an_authority_violation() -> None:
    receipt = run_episode(scenarios()["document-addition"], "stale_context")
    failures = receipt["verdict"]["failure_classes"]
    assert "stale_world_state" in failures
    assert "evidence_gap" in failures
    assert "authority_violation" not in failures


def test_committed_panel_is_exactly_recomputable() -> None:
    _, panel = run_panel(ROOT / "fixtures")
    committed = json.loads((ROOT / "results" / "reference" / "panel.json").read_bytes())
    assert canonical_bytes(panel) == canonical_bytes(committed)
    claimed = committed["report_sha256"]
    body = {key: value for key, value in committed.items() if key != "report_sha256"}
    assert claimed == digest(body)


def test_human_packet_is_blinded_to_policy_and_machine_verdict() -> None:
    receipts, _ = run_panel(ROOT / "fixtures")
    packet = build_packet(receipts)
    rendered = json.dumps(packet)
    assert "agent_policy" not in rendered
    assert '"verdict"' not in rendered
    assert '"scenario_id"' not in rendered
    assert len(packet["items"]) == 15


def test_two_distinct_human_files_produce_an_agreement_receipt(tmp_path: Path) -> None:
    receipts, _ = run_panel(ROOT / "fixtures")
    packet = build_packet(receipts)
    by_digest = {row["receipt_sha256"]: row for row in receipts}
    for reviewer_id in ("reviewer-a", "reviewer-b"):
        path = tmp_path / f"{reviewer_id}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["review_item_id", "reviewer_id", *CRITERIA, "reason"],
            )
            writer.writeheader()
            for item in packet["items"]:
                verdict = by_digest[item["receipt_sha256"]]["verdict"]["criteria"]
                writer.writerow(
                    {
                        "review_item_id": item["review_item_id"],
                        "reviewer_id": reviewer_id,
                        **{
                            criterion: "yes" if verdict[criterion] else "no"
                            for criterion in CRITERIA
                        },
                        "reason": "Independent fixture assessment.",
                    }
                )
    result = agreement(
        receipts,
        [tmp_path / "reviewer-a.csv", tmp_path / "reviewer-b.csv"],
    )
    assert result["reviewer_count"] == 2
    assert result["adjudication_required"] == []
    for reviewer in result["reviewers"]:
        assert all(
            row["raw_agreement"] == 1.0
            for row in reviewer["criteria"].values()
        )


class ScriptedBackend:
    provider = "fixture"
    model = "scripted-live-model"
    adapter_version = "fixture-adapter.v1"

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = iter(outputs)
        self.calls = 0

    def complete(self, prompt: str) -> Completion:
        self.calls += 1
        output = next(self.outputs)
        return Completion(
            provider=self.provider,
            model=self.model,
            adapter_version=self.adapter_version,
            response_id=f"fixture-{self.calls}",
            output_text=output,
            input_tokens=len(prompt.split()),
            output_tokens=len(output.split()),
            provider_response_sha256=digest({"prompt": prompt, "output": output}),
        )


def test_live_scaffold_delivers_event_and_accepts_current_evidence() -> None:
    scenario = scenarios()["document-addition"]
    final_world = World(scenario)
    final_engine = ScenarioEngine(scenario)
    final_engine.advance(2, final_world)
    submit = json.dumps(
        {
            "action": "recommendation.submit",
            "arguments": {
                "recommendation": "APPROVE",
                "observed_world_root": final_world.root,
                "citations": ["case-system@2", "policy-registry@1"],
                "rationale": "Current DTI and reserves satisfy the current policy.",
            },
        }
    )
    backend = ScriptedBackend(
        [
            '{"action":"case.read","arguments":{}}',
            '{"action":"policy.read","arguments":{}}',
            '{"action":"inbox.read","arguments":{}}',
            '{"action":"case.read","arguments":{}}',
            '{"action":"policy.read","arguments":{}}',
            submit,
        ]
    )
    receipt = run_live_episode(scenario, backend, seed=11)
    assert receipt["verdict"]["passed"] is True
    assert receipt["submission"]["recommendation"] == "APPROVE"
    assert len(receipt["evolution_witness"]) == 1
    assert any(
        row["tool"] == "inbox.read" and row["act_index"] == 3
        for row in receipt["acts"]
    )


def test_live_scaffold_keeps_protocol_errors_separate_from_environment_failure() -> None:
    backend = ScriptedBackend(["not-json", "still not json"])
    receipt = run_live_episode(
        scenarios()["static-control"],
        backend,
        seed=11,
        max_model_turns=2,
    )
    assert receipt["verdict"]["passed"] is False
    assert receipt["verdict"]["environment_failure"] is False
    assert receipt["verdict"]["failure_classes"] == ["no_valid_submission"]
    assert receipt["acts"] == []


def frontier_scenarios() -> dict[str, FrontierScenario]:
    return {
        row.scenario_id: row
        for row in load_frontier_scenarios(ROOT / "fixtures")
    }


def _frontier_safe_outputs(scenario: FrontierScenario) -> list[str]:
    actions: list[tuple[str, dict[str, str]]] = [
        ("source.list", {}),
        ("source.read", {"resource_id": "applications"}),
        ("source.read", {"resource_id": "policy"}),
        ("source.read", {"resource_id": "capacity"}),
        ("source.read", {"resource_id": "conditions"}),
        ("source.read", {"resource_id": "documents"}),
        ("source.read", {"resource_id": "authority_registry"}),
        ("timeline.await_cutoff", {}),
        ("source.read", {"resource_id": "applications"}),
        ("source.read", {"resource_id": "policy"}),
        ("source.read", {"resource_id": "capacity"}),
        ("source.read", {"resource_id": "conditions"}),
        ("source.read", {"resource_id": "documents"}),
        ("source.read", {"resource_id": "authority_registry"}),
        ("metrics.calculate", {"case_id": "ALDER"}),
        ("metrics.calculate", {"case_id": "BIRCH"}),
        ("metrics.calculate", {"case_id": "CEDAR"}),
        ("metrics.calculate", {"case_id": "DOGWOOD"}),
    ]
    world = FrontierWorld(scenario)
    engine = FrontierEngine(scenario)
    for act_index, (tool, _arguments) in enumerate(actions, start=1):
        fired = engine.advance(act_index, tool, world)
        for occurrence in fired:
            event = next(
                row for row in scenario.events if row.event_id == occurrence.event_id
            )
            if event.restore_after:
                world = FrontierWorld.restore(scenario, world.snapshot())
                engine = FrontierEngine.restore(scenario, engine.snapshot())
    expected = oracle_packet(world)
    submit = {
        "action": "decision.submit",
        "arguments": {
            "decisions": expected["decisions"],
            "exception_award": expected["exception_award"],
            "observed_world_root": world.root,
            "citations": expected["required_citations"],
            "rationale": "Current sources, shared capacity, and cutoff events reconciled.",
        },
    }
    return [
        json.dumps({"action": tool, "arguments": arguments})
        for tool, arguments in actions
    ] + [json.dumps(submit)]


def test_frontier_candidate_suite_is_canonical_solvable_and_answer_changing() -> None:
    rows = frontier_scenarios()
    assert list(rows) == [
        "frontier-static-control",
        "frontier-policy-supersession",
        "frontier-document-retraction-restore",
        "frontier-capacity-conflict",
        "frontier-chained-cutoff",
    ]
    for path in sorted((ROOT / "fixtures" / "frontier").glob("*.json")):
        assert canonical_bytes(load_json(path)) + b"\n" == path.read_bytes()
    report = frontier_admission_report(ROOT / "fixtures")
    assert report["scenario_count"] == 5
    assert [row["answer_changed"] for row in report["scenarios"]] == [
        False,
        True,
        True,
        True,
        True,
    ]
    committed = json.loads(
        (ROOT / "results" / "reference" / "frontier-admission.json").read_bytes()
    )
    assert canonical_bytes(report) == canonical_bytes(committed)
    judge_report = frontier_judge_validation_report(ROOT / "fixtures")
    committed_judge = json.loads(
        (ROOT / "results" / "reference" / "frontier-judge-validation.json").read_bytes()
    )
    assert judge_report["positive_controls_passed"] is True
    assert judge_report["isolated_detection_passed"] is True
    assert canonical_bytes(judge_report) == canonical_bytes(committed_judge)


@pytest.mark.parametrize("scenario_id", list(frontier_scenarios()))
def test_frontier_safe_script_can_solve_every_candidate(scenario_id: str) -> None:
    scenario = frontier_scenarios()[scenario_id]
    receipt = run_frontier_live_episode(
        scenario,
        ScriptedBackend(_frontier_safe_outputs(scenario)),
        attempt_id=1,
    )
    assert receipt["verdict"]["passed"] is True
    assert receipt["verdict"]["rubric_score"] == 1.0
    assert any(row["tool"] == "timeline.await_cutoff" for row in receipt["acts"])
    assert len(receipt["acts"]) == 19


def test_frontier_premature_submission_is_distinct_from_world_failure() -> None:
    scenario = frontier_scenarios()["frontier-static-control"]
    world = FrontierWorld(scenario)
    expected = oracle_packet(world)
    output = json.dumps({
        "action": "decision.submit",
        "arguments": {
            "decisions": expected["decisions"],
            "exception_award": expected["exception_award"],
            "observed_world_root": world.root,
            "citations": expected["required_citations"],
            "rationale": "Submitted without waiting.",
        },
    })
    source_reads = [
        json.dumps({
            "action": "source.read",
            "arguments": {"resource_id": resource_id},
        })
        for resource_id in sorted(scenario.resources)
    ]
    receipt = run_frontier_live_episode(
        scenario,
        ScriptedBackend([*source_reads, output]),
        attempt_id=1,
    )
    assert receipt["verdict"]["passed"] is False
    assert receipt["verdict"]["environment_failure"] is False
    assert receipt["verdict"]["failure_classes"] == ["premature_submission"]


def test_five_attempt_analysis_separates_coverage_from_reliability() -> None:
    receipts: list[dict[str, Any]] = []
    conditions = (("stable-fail", 0), ("inconsistent", 2), ("stable-pass", 5))
    for scenario_id, pass_count in conditions:
        for attempt_id in range(1, 6):
            passed = attempt_id <= pass_count
            receipts.append({
                "scenario_id": scenario_id,
                "attempt_id": attempt_id,
                "verdict": {
                    "passed": passed,
                    "environment_failure": False,
                    "failure_classes": [] if passed else ["decision_packet_error"],
                },
            })
    analysis = analyze_five_attempt_panel(receipts)
    by_id = {row["scenario_id"]: row for row in analysis["tasks"]}
    assert by_id["stable-fail"]["classification"] == "stable_failure_observed"
    assert by_id["inconsistent"]["classification"] == "inconsistent_observed"
    assert by_id["stable-pass"]["classification"] == "stable_pass_observed"
    assert by_id["inconsistent"]["any_pass_at_5"] is True
    assert by_id["inconsistent"]["all_pass_at_5"] is False


def test_two_pre_results_axes_each_freeze_five_seed_paired_candidates() -> None:
    corpus = generate_axis_candidates(ROOT / "fixtures" / "axes" / "definitions.json")
    assert corpus["status"] == "PRE-RESULTS"
    assert corpus["exact_witness_exposure"] is True
    assert corpus["seed_pairing"] == {
        "case_seeds": [1103, 1217, 1429, 1699, 1877],
        "control_and_treatment_share_seed": True,
        "control_and_treatment_share_initial_world": True,
        "seed_is_fixture_generation_identity_not_model_sampling_evidence": True,
    }
    assert [axis["axis_id"] for axis in corpus["axes"]] == [
        "interruption_phase_response",
        "authority_ladder",
    ]
    assert [axis["case_count"] for axis in corpus["axes"]] == [5, 5]
    for axis in corpus["axes"]:
        for case in axis["cases"]:
            assert case["synthetic"] is True
            assert case["control"]["seed"] == case["treatment"]["seed"] == case["seed"]
            assert (
                case["control"]["initial_world_root"]
                == case["treatment"]["initial_world_root"]
                == case["pairing_witness"]["paired_initial_world_sha256"]
            )
            assert case["control"]["exact_witness"] == []
            assert len(case["treatment"]["exact_witness"]) == 1


def test_axis_sweeps_cover_each_declared_phase_and_authority_rung_exactly_once() -> None:
    corpus = generate_axis_candidates(ROOT / "fixtures" / "axes" / "definitions.json")
    phase_cases = corpus["axes"][0]["cases"]
    authority_cases = corpus["axes"][1]["cases"]
    assert [row["manipulated_dimension"]["boundary_index"] for row in phase_cases] == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert [row["manipulated_dimension"]["rung"] for row in authority_cases] == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert [row["manipulated_dimension"]["material_effect"] for row in authority_cases] == [
        True,
        False,
        False,
        False,
        False,
    ]
    assert len(
        {row["treatment"]["initial_world_root"] for row in phase_cases}
    ) == 1
    assert len(
        {
            row["treatment"]["exact_witness"][0]["event_sha256"]
            for row in phase_cases
        }
    ) == 1
    assert len(
        {row["treatment"]["initial_world_root"] for row in authority_cases}
    ) == 1
    assert len(
        {
            (
                row["treatment"]["exact_witness"][0]["boundary_phase"],
                row["treatment"]["exact_witness"][0]["boundary_index"],
                row["treatment"]["exact_witness"][0]["boundary_action"],
            )
            for row in authority_cases
        }
    ) == 1


def test_axis_candidate_witnesses_expose_and_bind_projection_boundary_and_roots() -> None:
    corpus = generate_axis_candidates(ROOT / "fixtures" / "axes" / "definitions.json")
    for axis in corpus["axes"]:
        for case in axis["cases"]:
            witness = case["treatment"]["exact_witness"][0]
            assert witness["visible_projection_sha256"] == digest(
                witness["visible_projection"]
            )
            occurrence = {
                key: value
                for key, value in witness.items()
                if key not in {"visible_projection", "occurrence_sha256"}
            }
            assert witness["occurrence_sha256"] == digest(occurrence)
            assert witness["before_world_root"] == case["treatment"]["initial_world_root"]
            assert witness["after_world_root"] == case["treatment"]["terminal_world_root"]


def test_axis_validation_is_pre_results_and_every_mutation_is_isolated() -> None:
    expected = generate_axis_candidates(ROOT / "fixtures" / "axes" / "definitions.json")
    report = build_axis_validation(expected, expected)
    assert report["status"] == "PRE-RESULTS"
    assert report["live_study_status"] == "NOT_YET_RUN"
    assert report["frozen_case_count"] == 10
    assert report["seed_paired_control_count"] == 10
    assert report["exact_witness_count"] == 10
    assert report["mutation_probe_count"] == 100
    assert report["positive_controls_passed"] is True
    assert report["isolated_detection_passed"] is True
    assert "no live-model performance" in report["claim_boundary"]
    assert "frontier difficulty" in report["claim_boundary"]
    assert "research novelty" in report["claim_boundary"]
    public_axis_text = json.dumps(
        {"corpus": expected, "report": report}, sort_keys=True
    ).lower()
    assert "named-company" not in public_axis_text


def test_axis_candidates_and_validation_are_exact_replays() -> None:
    corpus, report = verify_axis_artifacts(ROOT)
    stored_corpus = json.loads(
        (ROOT / "fixtures" / "axes" / "frozen-candidates.json").read_bytes()
    )
    stored_report = json.loads(
        (ROOT / "results" / "reference" / "axis-candidates" / "validation.json").read_bytes()
    )
    stored_markdown = (
        ROOT / "results" / "reference" / "axis-candidates" / "REPORT.md"
    ).read_text(encoding="utf-8")
    assert canonical_bytes(corpus) == canonical_bytes(stored_corpus)
    assert canonical_bytes(report) == canonical_bytes(stored_report)
    assert render_axis_validation(report) == stored_markdown


def _spend_policy(*, max_requests: int = 8) -> SpendPolicy:
    return SpendPolicy(
        max_requests=max_requests,
        max_output_tokens_per_request=256,
        max_total_output_tokens=2_048,
        max_cost_usd=1.0,
        input_usd_per_million_tokens=1.0,
        output_usd_per_million_tokens=2.0,
    )


@pytest.mark.parametrize(
    ("provider", "response", "expected_url", "key_header"),
    [
        (
            "openai",
            {
                "id": "resp-openai",
                "model": "pinned-model",
                "output": [{"content": [{"type": "output_text", "text": "{}"}]}],
                "usage": {"input_tokens": 4, "output_tokens": 2},
            },
            "https://api.openai.com/v1/responses",
            "Authorization",
        ),
        (
            "xai",
            {
                "id": "resp-xai",
                "model": "pinned-model",
                "output": [{"content": [{"type": "output_text", "text": "{}"}]}],
                "usage": {"input_tokens": 4, "output_tokens": 2},
            },
            "https://api.x.ai/v1/responses",
            "Authorization",
        ),
        (
            "anthropic",
            {
                "id": "msg-anthropic",
                "model": "pinned-model",
                "content": [{"type": "text", "text": "{}"}],
                "usage": {"input_tokens": 4, "output_tokens": 2},
            },
            "https://api.anthropic.com/v1/messages",
            "x-api-key",
        ),
        (
            "gemini",
            {
                "responseId": "gemini-response",
                "modelVersion": "pinned-model",
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 4,
                    "candidatesTokenCount": 2,
                    "thoughtsTokenCount": 3,
                    "totalTokenCount": 9,
                },
            },
            "https://generativelanguage.googleapis.com/v1beta/models/pinned-model:generateContent",
            "x-goog-api-key",
        ),
    ],
)
def test_provider_adapters_pin_contracts_and_never_put_keys_in_receipts(
    provider: ProviderName,
    response: dict[str, Any],
    expected_url: str,
    key_header: str,
) -> None:
    calls: list[tuple[str, dict[str, str], dict[str, Any]]] = []
    test_key = "private-test-key"

    def transport(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> tuple[int, bytes]:
        assert timeout_seconds == 10
        calls.append((url, headers, payload))
        return 200, json.dumps(response).encode()

    backend = CappedProviderBackend(
        provider,
        "pinned-model",
        _spend_policy(),
        transport=transport,
        timeout_seconds=10,
        api_key=test_key,
        temperature=0.4,
    )
    completion = backend.complete("one prompt")
    assert completion.output_text == "{}"
    assert completion.input_tokens == 4
    expected_output_tokens = 5 if provider == "gemini" else 2
    assert completion.output_tokens == expected_output_tokens
    assert completion.estimated_cost_usd == pytest.approx(
        (4 + (2 * expected_output_tokens)) / 1_000_000
    )
    assert completion.resolved_model == "pinned-model"
    assert completion.cumulative_reserved_cost_usd is not None
    assert completion.estimated_cost_usd is not None
    assert completion.cumulative_reserved_cost_usd >= completion.estimated_cost_usd
    assert backend.reserved_output_tokens == _spend_policy().max_output_tokens_per_request
    assert test_key not in repr(completion)
    assert calls[0][0] == expected_url
    assert calls[0][1][key_header].endswith(test_key)
    if provider != "gemini":
        assert calls[0][2]["model"] == "pinned-model"
        assert calls[0][2]["temperature"] == 0.4
        if provider in {"openai", "xai"}:
            assert calls[0][2]["store"] is False
    else:
        assert calls[0][2]["generationConfig"]["temperature"] == 0.4
        assert "store" not in calls[0][2]
    assert backend.sampling_policy == {
        "temperature": 0.4,
        "temperature_posture": "explicit",
        "provider_seed": None,
        "repeat_semantics": "independent_provider_request",
    }


def test_provider_request_budget_stops_before_network() -> None:
    calls = 0
    test_key = "private-test-key"

    def transport(
        _url: str,
        _headers: dict[str, str],
        payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        nonlocal calls
        assert "temperature" not in payload
        calls += 1
        return 200, json.dumps(
            {
                "id": f"response-{calls}",
                "model": "pinned-model",
                "output": [{"content": [{"type": "output_text", "text": "{}"}]}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        ).encode()

    backend = CappedProviderBackend(
        "openai",
        "pinned-model",
        _spend_policy(max_requests=1),
        transport=transport,
        api_key=test_key,
    )
    backend.complete("first")
    with pytest.raises(RuntimeError, match="provider_request_budget_exhausted"):
        backend.complete("second")
    assert calls == 1


def test_provider_output_reservation_is_cumulative_before_network() -> None:
    calls = 0

    def transport(
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 200, json.dumps(
            {
                "id": f"response-{calls}",
                "model": "pinned-model",
                "output": [{"content": [{"type": "output_text", "text": "{}"}]}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        ).encode()

    policy = SpendPolicy(
        max_requests=8,
        max_output_tokens_per_request=256,
        max_total_output_tokens=256,
        max_cost_usd=1.0,
        input_usd_per_million_tokens=1.0,
        output_usd_per_million_tokens=2.0,
    )
    backend = CappedProviderBackend(
        "openai",
        "pinned-model",
        policy,
        transport=transport,
        api_key="test-key",
    )
    backend.complete("first")
    with pytest.raises(BudgetStop, match="provider_output_token_budget_exhausted"):
        backend.complete("second")
    assert backend.reserved_output_tokens == 256
    assert calls == 1


def test_provider_prompt_size_stops_before_network() -> None:
    calls = 0

    def transport(
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 500, b""

    backend = CappedProviderBackend(
        "openai",
        "pinned-model",
        _spend_policy(),
        transport=transport,
        api_key="test-key",
    )
    with pytest.raises(BudgetStop, match="provider_prompt_bytes_limit_exhausted"):
        backend.complete("x" * (MAX_PROMPT_BYTES + 1))
    assert calls == 0
    assert backend.reserved_output_tokens == 0


def test_provider_refuses_response_without_resolved_model_identity() -> None:
    def transport(
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        return 200, json.dumps(
            {
                "id": "response-without-model",
                "output": [{"content": [{"type": "output_text", "text": "{}"}]}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        ).encode()

    backend = CappedProviderBackend(
        "openai",
        "requested-model",
        _spend_policy(),
        transport=transport,
        api_key="test-key",
    )
    with pytest.raises(ProviderFailure, match="provider_resolved_model_missing"):
        backend.complete("one prompt")
    with pytest.raises(ProviderFailure, match="provider_cell_latched_after_failure"):
        backend.complete("another prompt")


def test_provider_refuses_resolved_model_mismatch_and_latches_cell() -> None:
    calls = 0

    def transport(
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 200, json.dumps(
            {
                "id": "response-with-wrong-model",
                "model": "different-model",
                "output": [{"content": [{"type": "output_text", "text": "{}"}]}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        ).encode()

    backend = CappedProviderBackend(
        "openai",
        "requested-model",
        _spend_policy(),
        transport=transport,
        api_key="test-key",
    )
    with pytest.raises(ProviderFailure, match="provider_resolved_model_mismatch"):
        backend.complete("one prompt")
    assert backend.estimated_cost_usd > 0
    with pytest.raises(ProviderFailure, match="provider_cell_latched_after_failure"):
        backend.complete("another prompt")
    assert calls == 1


def test_gemini_usage_falls_back_to_candidates_plus_thinking_tokens() -> None:
    def transport(
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        return 200, json.dumps(
            {
                "responseId": "gemini-response",
                "modelVersion": "requested-model",
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 4,
                    "candidatesTokenCount": 2,
                    "thoughtsTokenCount": 7,
                },
            }
        ).encode()

    backend = CappedProviderBackend(
        "gemini",
        "requested-model",
        _spend_policy(),
        transport=transport,
        api_key="test-key",
    )
    assert backend.complete("one prompt").output_tokens == 9


def test_gemini_refuses_missing_provider_response_id() -> None:
    def transport(
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        return 200, json.dumps(
            {
                "modelVersion": "requested-model",
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 4,
                    "candidatesTokenCount": 2,
                },
            }
        ).encode()

    backend = CappedProviderBackend(
        "gemini",
        "requested-model",
        _spend_policy(),
        transport=transport,
        api_key="test-key",
    )
    with pytest.raises(ProviderFailure, match="provider_response_id_missing"):
        backend.complete("one prompt")


def test_provider_failure_consumes_reservation_and_latches_cell() -> None:
    calls = 0

    def transport(
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
        _timeout_seconds: float,
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1
        return 503, b""

    backend = CappedProviderBackend(
        "openai",
        "requested-model",
        _spend_policy(),
        transport=transport,
        api_key="test-key",
    )
    with pytest.raises(ProviderFailure, match="provider_http_status:503"):
        backend.complete("one prompt")
    assert backend.reserved_cost_usd > 0
    assert backend.reserved_output_tokens == _spend_policy().max_output_tokens_per_request
    with pytest.raises(ProviderFailure, match="provider_cell_latched_after_failure"):
        backend.complete("another prompt")
    assert calls == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_requests", True),
        ("max_cost_usd", float("nan")),
        ("input_usd_per_million_tokens", float("inf")),
    ],
)
def test_spend_policy_refuses_boolean_or_nonfinite_limits(
    field: str, value: object
) -> None:
    values: dict[str, object] = {
        "max_requests": 8,
        "max_output_tokens_per_request": 256,
        "max_total_output_tokens": 2_048,
        "max_cost_usd": 1.0,
        "input_usd_per_million_tokens": 1.0,
        "output_usd_per_million_tokens": 2.0,
    }
    values[field] = value
    with pytest.raises(ValueError, match="spend_policy_"):
        SpendPolicy(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("model", ["latest", "model-latest", " model-v1", "model v1"])
def test_provider_refuses_unstable_or_ambiguous_model_pins(model: str) -> None:
    with pytest.raises(ValueError, match="provider_model_"):
        CappedProviderBackend(
            "openai", model, _spend_policy(), api_key="test-key"
        )


def test_frontier_preregistration_binds_tasks_judge_analysis_and_spend() -> None:
    registration = build_frontier_preregistration(
        ROOT,
        run_id="frozen-cell-001",
        created_at="2032-04-18T16:00:00Z",
        git_sha="a" * 40,
        provider="openai",
        requested_model="pinned-model",
        scenario_ids=["frontier-chained-cutoff"],
        max_model_turns=32,
        max_acts=28,
        timeout_seconds=60,
        spend_policy=_spend_policy(max_requests=160),
        temperature=0,
        price_source_url="https://platform.openai.com/docs/pricing",
        price_checked_at="2032-04-18T15:55:00Z",
        retention_terms_url="https://platform.openai.com/docs/data-usage-policies",
        retention_checked_at="2032-04-18T15:56:00Z",
        derived_publication_posture="unknown",
    )
    verified = verify_frontier_preregistration(ROOT, registration, verify_git=False)
    assert verified["frontier"]["attempt_ids_per_scenario"] == [1, 2, 3, 4, 5]
    assert verified["frontier"]["judge_validation_report_sha256"] == (
        frontier_judge_validation_report(ROOT / "fixtures")["report_sha256"]
    )
    assert verified["spend_policy"]["max_requests"] == 160
    assert verified["cell"]["model_identity_policy"] == (
        "provider_resolved_must_equal_requested"
    )
    assert (
        verified["rights"][
            "operator_attests_private_raw_response_retention_permitted"
        ]
        is True
    )

    tampered = deepcopy(registration)
    tampered["cell"]["requested_model"] = "different-model"
    with pytest.raises(ValueError, match="preregistration_digest_invalid"):
        verify_frontier_preregistration(ROOT, tampered, verify_git=False)


def test_frontier_preregistration_requires_official_price_source() -> None:
    with pytest.raises(ValueError, match="official_price_source_required"):
        build_frontier_preregistration(
            ROOT,
            run_id="frozen-cell-002",
            created_at="2032-04-18T16:00:00Z",
            git_sha="a" * 40,
            provider="gemini",
            requested_model="pinned-model",
            scenario_ids=["frontier-static-control"],
            max_model_turns=32,
            max_acts=28,
            timeout_seconds=60,
            spend_policy=_spend_policy(max_requests=160),
            temperature=None,
            price_source_url="https://example.com/prices",
            price_checked_at="2032-04-18T15:55:00Z",
            retention_terms_url="https://ai.google.dev/terms",
            retention_checked_at="2032-04-18T15:56:00Z",
            derived_publication_posture="not_permitted",
        )


@pytest.mark.parametrize(
    "price_url",
    [
        "https://platform.openai.com/docs/pricing?token=secret",
        "https://operator@platform.openai.com/docs/pricing",
        "https://platform.openai.com:443/docs/pricing",
    ],
)
def test_frontier_preregistration_refuses_nonpublic_source_url_shapes(
    price_url: str,
) -> None:
    with pytest.raises(ValueError, match="official_price_source_required"):
        build_frontier_preregistration(
            ROOT,
            run_id="frozen-cell-003",
            created_at="2032-04-18T16:00:00Z",
            git_sha="a" * 40,
            provider="openai",
            requested_model="pinned-model",
            scenario_ids=["frontier-static-control"],
            max_model_turns=32,
            max_acts=28,
            timeout_seconds=60,
            spend_policy=_spend_policy(max_requests=160),
            temperature=None,
            price_source_url=price_url,
            price_checked_at="2032-04-18T15:55:00Z",
            retention_terms_url="https://platform.openai.com/docs/data-usage-policies",
            retention_checked_at="2032-04-18T15:56:00Z",
            derived_publication_posture="unknown",
        )


def test_frontier_preregistration_refuses_stale_or_future_evidence_checks() -> None:
    with pytest.raises(ValueError, match="price_checked_at_not_current_at_creation"):
        build_frontier_preregistration(
            ROOT,
            run_id="frozen-cell-004",
            created_at="2032-04-18T16:00:00Z",
            git_sha="a" * 40,
            provider="openai",
            requested_model="pinned-model",
            scenario_ids=["frontier-static-control"],
            max_model_turns=32,
            max_acts=28,
            timeout_seconds=60,
            spend_policy=_spend_policy(max_requests=160),
            temperature=None,
            price_source_url="https://platform.openai.com/docs/pricing",
            price_checked_at="2032-04-19T15:55:00Z",
            retention_terms_url="https://platform.openai.com/docs/data-usage-policies",
            retention_checked_at="2032-04-18T15:56:00Z",
            derived_publication_posture="unknown",
        )


class StubClient(GradiaClient):
    def __init__(self, paths: set[str], anonymous_status: int = 401) -> None:
        super().__init__("https://example.invalid")
        self.paths = paths
        self.anonymous_status = anonymous_status

    def request(
        self, method: str, path: str, body: dict[str, object] | None = None
    ) -> Response:
        del method, body
        if path == "/v1/health":
            return Response(200, b'{"status":"ok"}')
        if path == "/openapi.json":
            payload = json.dumps({"paths": {name: {} for name in self.paths}}).encode()
            return Response(200, payload)
        return Response(self.anonymous_status, b'{"detail":"unauthorized"}')


def test_gradia_external_contract_checks_paths_and_anonymous_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = StubClient(REQUIRED_PATHS)
    monkeypatch.setattr(
        "gradia_universes.gradia_client.GradiaClient",
        lambda _base_url: StubClient(REQUIRED_PATHS),
    )
    evidence = client.verify_contract()
    assert evidence["health_status"] == 200
    assert evidence["anonymous_project_scenario_status"] == 401


def test_gradia_external_contract_refuses_a_missing_path() -> None:
    missing = deepcopy(REQUIRED_PATHS)
    missing.remove("/v1/runs/{run_id}/scenario-occurrences")
    with pytest.raises(ValueError, match="gradia_contract_paths_missing"):
        StubClient(missing).verify_contract()


def test_public_scan_ignores_local_execution_products(tmp_path: Path) -> None:
    local = tmp_path / ".venv" / "bin"
    local.mkdir(parents=True)
    local_path = "/" + "Users/local-user/private-path\n"
    (local / "activate").write_text(local_path, encoding="utf-8")
    (tmp_path / "README.md").write_text("release-safe\n", encoding="utf-8")
    _verify_release_text_boundary(tmp_path)


def test_public_scan_refuses_a_release_file_with_a_local_path(tmp_path: Path) -> None:
    local_path = "/" + "Users/local-user/private-path\n"
    (tmp_path / "README.md").write_text(
        local_path, encoding="utf-8"
    )
    with pytest.raises(ValueError, match="public_boundary_refused"):
        _verify_release_text_boundary(tmp_path)


@pytest.mark.parametrize(
    "local_path",
    [
        "/" + "home/local-user/private-path\n",
        "C:" + "\\Users\\local-user\\private-path\n",
    ],
)
def test_public_scan_refuses_cross_platform_local_paths(
    tmp_path: Path, local_path: str
) -> None:
    (tmp_path / "README.md").write_text(local_path, encoding="utf-8")
    with pytest.raises(ValueError, match="public_boundary_refused"):
        _verify_release_text_boundary(tmp_path)


def test_public_scan_refuses_a_literal_api_key(tmp_path: Path) -> None:
    secret = "api_key=" + '"' + ("A" * 32) + '"\n'
    (tmp_path / "config.py").write_text(secret, encoding="utf-8")
    with pytest.raises(ValueError, match="public_boundary_refused"):
        _verify_release_text_boundary(tmp_path)


def test_public_bundle_is_a_full_replayable_episode_dossier() -> None:
    bundle = verify_public_bundle(ROOT)
    assert bundle == build_public_bundle(ROOT)
    assert bundle["public_release_status"] == "candidate_not_authorized"
    assert bundle["measurement_status"]["live_model_performance"] == "not_measured"
    assert len(bundle["episodes"]) == 15
    featured = next(
        row
        for row in bundle["episodes"]
        if row["receipt_sha256"] == bundle["featured_receipt_sha256"]
    )
    assert featured["verdict"]["failure_classes"] == [
        "stale_world_state",
        "missed_world_change",
        "decision_error",
        "evidence_gap",
    ]


def test_public_bundle_digest_refuses_a_mutated_claim() -> None:
    bundle = build_public_bundle(ROOT)
    bundle["claim_boundary"] = "model performance"
    claimed = bundle.pop("bundle_sha256")
    assert digest(bundle) != claimed


def test_study_a_engineering_corpus_is_isolated_and_replayable() -> None:
    corpus, report = build_study_a(ROOT / "fixtures")
    assert report["parent_count"] == 5
    assert report["invalid_fork_count"] == 26
    assert report["confirmatory_study_status"] == "NOT_YET_RUN"
    assert len(corpus["forks"]) == 26
    for fork in corpus["forks"]:
        assert fork["primary_changed_paths"]
        assert fork["all_changed_paths"]
        assert fork["fork_receipt_sha256"] != fork["parent_receipt_sha256"]
        for primary in fork["primary_changed_paths"]:
            assert any(
                changed == primary or changed.startswith(primary + "/")
                for changed in fork["all_changed_paths"]
            )


def test_study_a_projection_matrix_preserves_the_claim_boundary() -> None:
    _corpus, report = build_study_a(ROOT / "fixtures")
    rows = {row["evidence_policy"]: row for row in report["policy_rows"]}
    assert rows["T"]["projection_sensitive"] == 0
    assert rows["P+T*"]["projection_sensitive"] == 15
    assert rows["W"]["projection_sensitive"] == 26
    assert all(row["faithful_parent_projection_changes"] == 0 for row in rows.values())
    assert "not a confirmatory detector result" in report["claim_boundary"]


def test_study_a_committed_artifacts_are_exactly_recomputable() -> None:
    corpus, report = build_study_a(ROOT / "fixtures")
    target = ROOT / "results" / "reference" / "study-a-engineering"
    assert canonical_bytes(corpus) == canonical_bytes(
        json.loads((target / "corpus.json").read_bytes())
    )
    assert canonical_bytes(report) == canonical_bytes(
        json.loads((target / "report.json").read_bytes())
    )
    assert render_study_a(report) == (target / "REPORT.md").read_text(encoding="utf-8")
