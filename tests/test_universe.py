from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

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
from gradia_universes.live_runner import Completion, run_live_episode
from gradia_universes.providers import CappedProviderBackend, ProviderName, SpendPolicy
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
    receipt = run_frontier_live_episode(
        scenario,
        ScriptedBackend([output]),
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
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
                "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2},
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
    assert completion.output_tokens == 2
    assert completion.estimated_cost_usd == pytest.approx(0.000008)
    assert test_key not in repr(completion)
    assert calls[0][0] == expected_url
    assert calls[0][1][key_header].endswith(test_key)
    if provider != "gemini":
        assert calls[0][2]["model"] == "pinned-model"
        assert calls[0][2]["temperature"] == 0.4
    else:
        assert calls[0][2]["generationConfig"]["temperature"] == 0.4
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
