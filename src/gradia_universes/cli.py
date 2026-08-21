"""Command-line entry point for the public work sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, digest, write_canonical
from .frontier import (
    FRONTIER_SCAFFOLD_VERSION,
    analyze_five_attempt_panel,
    analyze_frontier_diagnostic,
    frontier_admission_report,
    frontier_judge_validation_report,
    load_frontier_scenarios,
    run_frontier_live_episode,
)
from .gradia_client import GradiaClient
from .human_review import agreement, write_packet
from .live_runner import SCAFFOLD_VERSION, run_live_episode
from .preregistration import (
    build_frontier_preregistration,
    clean_git_sha,
    load_frontier_preregistration,
    write_frontier_preregistration,
)
from .providers import CappedProviderBackend, SpendPolicy
from .public_bundle import verify_public_bundle, write_public_bundle
from .report import render_markdown
from .runner import load_scenarios, run_panel
from .study_a import build_study_a, render_study_a, write_study_a

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(
        r"(?:api[_-]?key|authorization)[\"']?\s*[:=]\s*[\"']"
        r"(?:bearer\s+)?[A-Za-z0-9._-]{16,}[\"']",
        re.IGNORECASE,
    ),
    re.compile("/" + r"(?:Users|home)/[^/\s]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\", re.IGNORECASE),
)

# Local execution products are not release inputs. In particular, an editable
# virtualenv embeds the machine path and contains third-party registries whose
# example strings resemble credentials. The release scanner must inspect our
# source and evidence, rather than report dependencies that will never be
# committed or packaged with the sample.
PUBLIC_SCAN_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
    }
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_results(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipts, panel = run_panel(root / "fixtures")
    target = root / "results" / "reference"
    for receipt in receipts:
        name = f"{receipt['scenario_id']}--{receipt['agent_policy']}.json"
        write_canonical(target / "receipts" / name, receipt)
    write_canonical(target / "panel.json", panel)
    (target / "REPORT.md").write_text(render_markdown(panel), encoding="utf-8")
    return receipts, panel


def _verify_receipt(receipt: dict[str, Any]) -> None:
    claimed = receipt.get("receipt_sha256")
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if claimed != digest(body):
        raise ValueError(f"receipt_digest_mismatch:{receipt.get('scenario_id')}")
    previous: str | None = None
    for occurrence in receipt["evolution_witness"]:
        if occurrence["previous_occurrence_sha256"] != previous:
            raise ValueError("occurrence_previous_mismatch")
        projection = occurrence["visible_projection"]
        if digest(projection) != occurrence["visible_projection_sha256"]:
            raise ValueError("occurrence_projection_mismatch")
        occurrence_body = {
            key: value
            for key, value in occurrence.items()
            if key not in {"visible_projection", "occurrence_sha256"}
        }
        if digest(occurrence_body) != occurrence["occurrence_sha256"]:
            raise ValueError("occurrence_digest_mismatch")
        previous = occurrence["occurrence_sha256"]


def command_run(args: argparse.Namespace) -> int:
    receipts, panel = _write_results(args.root)
    print(f"wrote {len(receipts)} replayable receipts; panel_sha256={panel['report_sha256']}")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    receipts, panel = run_panel(args.root / "fixtures")
    target = args.root / "results" / "reference"
    expected_panel = json.loads((target / "panel.json").read_bytes())
    if canonical_bytes(panel) != canonical_bytes(expected_panel):
        raise ValueError("panel_replay_mismatch")
    for receipt in receipts:
        _verify_receipt(receipt)
        path = (
            target / "receipts" / (f"{receipt['scenario_id']}--{receipt['agent_policy']}.json")
        )
        expected = json.loads(path.read_bytes())
        if canonical_bytes(receipt) != canonical_bytes(expected):
            raise ValueError(f"receipt_replay_mismatch:{path.name}")
    expected_report = (target / "REPORT.md").read_text(encoding="utf-8")
    if render_markdown(panel) != expected_report:
        raise ValueError("markdown_report_replay_mismatch")
    print(f"verified {len(receipts)} receipts by replay; panel_sha256={panel['report_sha256']}")
    return 0


def _verify_release_text_boundary(root: Path) -> None:
    refused: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        ignored_local_env = False
        if path.name == ".env" or (
            path.name.startswith(".env.") and path.name != ".env.example"
        ):
            try:
                ignored_local_env = (
                    subprocess.run(
                        ["git", "check-ignore", "--quiet", "--", str(relative)],
                        cwd=root,
                        check=False,
                        capture_output=True,
                    ).returncode
                    == 0
                )
            except OSError:
                ignored_local_env = False
        if (
            not path.is_file()
            or any(part in PUBLIC_SCAN_EXCLUDED_PARTS for part in relative.parts)
            or path.suffix in {".pyc", ".png"}
            or ignored_local_env
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                refused.append(f"{relative}:{pattern.pattern}")
    if refused:
        raise ValueError("public_boundary_refused:" + ";".join(refused))


def command_verify_public(args: argparse.Namespace) -> int:
    _verify_release_text_boundary(args.root)
    bundle = verify_public_bundle(args.root)
    print("public-boundary scan passed: no known secret or local-path shapes")
    print(f"public Universe bundle replayed: bundle_sha256={bundle['bundle_sha256']}")
    return 0


def command_build_public(args: argparse.Namespace) -> int:
    bundle = write_public_bundle(args.root)
    print(f"wrote public Universe release candidate: bundle_sha256={bundle['bundle_sha256']}")
    return 0


def command_study_a_build(args: argparse.Namespace) -> int:
    corpus, report = write_study_a(args.root)
    print(
        f"wrote {report['invalid_fork_count']} isolated engineering forks; "
        f"corpus_sha256={corpus['corpus_sha256']}"
    )
    return 0


def command_study_a_verify(args: argparse.Namespace) -> int:
    corpus, report = build_study_a(args.root / "fixtures")
    target = args.root / "results" / "reference" / "study-a-engineering"
    expected_corpus = json.loads((target / "corpus.json").read_bytes())
    expected_report = json.loads((target / "report.json").read_bytes())
    if canonical_bytes(corpus) != canonical_bytes(expected_corpus):
        raise ValueError("study_a_corpus_replay_mismatch")
    if canonical_bytes(report) != canonical_bytes(expected_report):
        raise ValueError("study_a_report_replay_mismatch")
    expected_markdown = (target / "REPORT.md").read_text(encoding="utf-8")
    if render_study_a(report) != expected_markdown:
        raise ValueError("study_a_markdown_replay_mismatch")
    print(
        f"verified {report['invalid_fork_count']} isolated engineering forks; "
        f"report_sha256={report['report_sha256']}"
    )
    return 0


def command_frontier_build(args: argparse.Namespace) -> int:
    report = frontier_admission_report(args.root / "fixtures")
    target = args.root / "results" / "reference" / "frontier-admission.json"
    write_canonical(target, report)
    judge_report = frontier_judge_validation_report(args.root / "fixtures")
    judge_target = args.root / "results" / "reference" / "frontier-judge-validation.json"
    write_canonical(judge_target, judge_report)
    print(
        f"wrote {report['scenario_count']} frontier-candidate admissions; "
        f"report_sha256={report['report_sha256']}; "
        f"judge_report_sha256={judge_report['report_sha256']}"
    )
    return 0


def command_frontier_verify(args: argparse.Namespace) -> int:
    report = frontier_admission_report(args.root / "fixtures")
    target = args.root / "results" / "reference" / "frontier-admission.json"
    expected = json.loads(target.read_bytes())
    if canonical_bytes(report) != canonical_bytes(expected):
        raise ValueError("frontier_admission_replay_mismatch")
    judge_report = frontier_judge_validation_report(args.root / "fixtures")
    judge_target = args.root / "results" / "reference" / "frontier-judge-validation.json"
    expected_judge = json.loads(judge_target.read_bytes())
    if canonical_bytes(judge_report) != canonical_bytes(expected_judge):
        raise ValueError("frontier_judge_validation_replay_mismatch")
    if not judge_report["positive_controls_passed"]:
        raise ValueError("frontier_judge_positive_control_failed")
    if not judge_report["isolated_detection_passed"]:
        raise ValueError("frontier_judge_isolation_failed")
    print(
        f"verified {report['scenario_count']} frontier-candidate admissions; "
        f"report_sha256={report['report_sha256']}; "
        f"judge_report_sha256={judge_report['report_sha256']}"
    )
    return 0


def command_gradia_contract(args: argparse.Namespace) -> int:
    evidence = GradiaClient(args.base_url).verify_contract()
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


def command_human_packet(args: argparse.Namespace) -> int:
    receipts, _ = run_panel(args.root / "fixtures")
    json_path, csv_path = write_packet(receipts, args.output)
    print(f"wrote blinded packet {json_path} and template {csv_path}")
    return 0


def command_human_agreement(args: argparse.Namespace) -> int:
    receipts, _ = run_panel(args.root / "fixtures")
    result = agreement(receipts, args.reviews)
    write_canonical(args.output, result)
    print(
        f"wrote agreement receipt for {result['reviewer_count']} reviewers; "
        f"agreement_sha256={result['agreement_sha256']}"
    )
    return 0


def _private_response_sink(directory: Path) -> Callable[[bytes], None]:
    counter = 0

    def retain(raw: bytes) -> None:
        nonlocal counter
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        counter += 1
        sha = hashlib.sha256(raw).hexdigest()
        target = directory / f"response-{counter:04d}--{sha[:16]}.json"
        target.write_bytes(raw)
        target.chmod(0o600)

    return retain


def command_live_panel(args: argparse.Namespace) -> int:
    if not args.confirm_live_spend:
        raise ValueError("live_spend_confirmation_required")
    if not args.confirm_private_response_retention:
        raise ValueError("private_response_retention_confirmation_required")
    if not args.confirm_provider_account_spend_limit:
        raise ValueError("provider_account_spend_limit_confirmation_required")
    run_id = args.run_id
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise ValueError("live_run_id_invalid")
    if len(args.seeds) != len(set(args.seeds)) or not 1 <= len(args.seeds) <= 16:
        raise ValueError("live_seed_set_invalid")
    if any(seed < 0 or seed > 2**31 - 1 for seed in args.seeds):
        raise ValueError("live_seed_out_of_bounds")
    root = args.root.resolve()
    output = (root / "results" / "local" / run_id).resolve()
    expected_parent = (root / "results" / "local").resolve()
    if output.parent != expected_parent:
        raise ValueError("live_output_boundary_invalid")
    if output.exists():
        raise ValueError("live_result_edition_exists")
    scenarios = load_scenarios(root / "fixtures")
    selected_ids = args.scenario or [row.scenario_id for row in scenarios]
    by_id = {row.scenario_id: row for row in scenarios}
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("live_scenario_set_duplicate")
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ValueError("live_scenario_unknown:" + ",".join(missing))
    if len(selected_ids) * len(args.seeds) > 100:
        raise ValueError("live_episode_count_out_of_bounds")
    policy = SpendPolicy(
        max_requests=args.max_provider_requests,
        max_output_tokens_per_request=args.max_output_tokens,
        max_total_output_tokens=args.max_total_output_tokens,
        max_cost_usd=args.max_cost_usd,
        input_usd_per_million_tokens=args.input_usd_per_million,
        output_usd_per_million_tokens=args.output_usd_per_million,
    )
    private_dir = output / "private-provider-responses"
    backend = CappedProviderBackend(
        args.provider,
        args.model,
        policy,
        timeout_seconds=args.timeout_seconds,
        response_sink=_private_response_sink(private_dir),
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
    )
    receipts: list[dict[str, Any]] = []
    for scenario_id in selected_ids:
        for seed in args.seeds:
            receipts.append(
                run_live_episode(
                    by_id[scenario_id],
                    backend,
                    seed=seed,
                    max_model_turns=args.max_model_turns,
                    max_acts=args.max_acts,
                )
            )
    eligible = [
        row
        for row in receipts
        if not row["verdict"]["environment_failure"]
        and row["verdict"]["failure_classes"] != ["budget_stop"]
    ]
    passes = sum(1 for row in eligible if row["verdict"]["passed"])
    panel_body = {
        "schema": "gradia-public-live-model-panel.v1",
        "run_id": run_id,
        "provider": args.provider,
        "model": args.model,
        "adapter_version": backend.adapter_version,
        "scaffold": SCAFFOLD_VERSION,
        "scenario_ids": selected_ids,
        "seeds": args.seeds,
        "spend_policy": policy.as_dict(),
        "spend_policy_sha256": backend.policy_sha256,
        "sampling_policy": backend.sampling_policy,
        "sampling_policy_sha256": backend.sampling_policy_sha256,
        "estimated_cost_usd": backend.estimated_cost_usd,
        "conservative_reserved_cost_usd": backend.reserved_cost_usd,
        "conservative_reserved_output_tokens": backend.reserved_output_tokens,
        "cost_is_user_supplied_price_estimate_not_invoice": True,
        "rights": {
            "operator_attests_private_raw_response_retention_permitted": True,
        },
        "operator_controls": {
            "operator_attests_provider_account_spend_limit_enabled": True,
            "live_spend_confirmed_at_execution": True,
        },
        "episodes": len(receipts),
        "eligible_episodes": len(eligible),
        "environment_failures": sum(
            1 for row in receipts if row["verdict"]["environment_failure"]
        ),
        "budget_stops": sum(
            1 for row in receipts if row["verdict"]["failure_classes"] == ["budget_stop"]
        ),
        "passes": passes,
        "pass_rate": passes / len(eligible) if eligible else None,
        "receipt_sha256s": [row["receipt_sha256"] for row in receipts],
    }
    panel = {**panel_body, "panel_sha256": digest(panel_body)}
    output.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    receipts_dir = output / "receipts"
    for row in receipts:
        filename = f"{row['scenario_id']}--seed-{row['seed']}.json"
        write_canonical(receipts_dir / filename, row)
    write_canonical(output / "panel.json", panel)
    print(
        f"wrote local live panel {run_id}: {passes}/{len(eligible)} eligible passes; "
        f"estimated_cost_usd={backend.estimated_cost_usd:.6f}; "
        f"panel_sha256={panel['panel_sha256']}"
    )
    return 0


def command_provider_smoke(args: argparse.Namespace) -> int:
    """Verify one provider protocol/identity/usage cell without a benchmark task."""
    if not args.confirm_live_spend:
        raise ValueError("live_spend_confirmation_required")
    if not args.confirm_private_response_retention:
        raise ValueError("private_response_retention_confirmation_required")
    if not args.confirm_provider_account_spend_limit:
        raise ValueError("provider_account_spend_limit_confirmation_required")
    run_id = args.run_id
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise ValueError("provider_smoke_run_id_invalid")
    root = args.root.resolve()
    output = (root / "results" / "local" / run_id).resolve()
    if output.parent != (root / "results" / "local").resolve():
        raise ValueError("provider_smoke_output_boundary_invalid")
    if output.exists():
        raise ValueError("provider_smoke_result_edition_exists")
    policy = SpendPolicy(
        max_requests=1,
        max_output_tokens_per_request=args.max_output_tokens,
        max_total_output_tokens=args.max_output_tokens,
        max_cost_usd=args.max_cost_usd,
        input_usd_per_million_tokens=args.input_usd_per_million,
        output_usd_per_million_tokens=args.output_usd_per_million,
    )
    private_dir = output / "private-provider-responses"
    backend = CappedProviderBackend(
        args.provider,
        args.model,
        policy,
        timeout_seconds=args.timeout_seconds,
        response_sink=_private_response_sink(private_dir),
        temperature=None,
        reasoning_effort="high",
    )
    prompt = (
        "This is a provider-protocol smoke, not a benchmark task. Return exactly "
        '{"status":"ok"} with no markdown or additional text.'
    )
    completion = backend.complete(prompt)
    body = {
        "schema": "gradia-provider-protocol-smoke.v1",
        "claim_status": "private_protocol_only",
        "run_id": run_id,
        "provider": args.provider,
        "requested_model": args.model,
        "resolved_model": completion.resolved_model,
        "adapter_version": backend.adapter_version,
        "sampling_policy": backend.sampling_policy,
        "sampling_policy_sha256": backend.sampling_policy_sha256,
        "spend_policy": policy.as_dict(),
        "spend_policy_sha256": backend.policy_sha256,
        "response_id": completion.response_id,
        "response_text_sha256": digest(completion.output_text),
        "provider_response_sha256": completion.provider_response_sha256,
        "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens,
        "estimated_cost_usd": completion.estimated_cost_usd,
        "conservative_reserved_cost_usd": backend.reserved_cost_usd,
        "operator_attests_private_raw_response_retention_permitted": True,
        "operator_attests_provider_account_spend_limit_enabled": True,
        "benchmark_task_or_score_present": False,
    }
    receipt = {**body, "receipt_sha256": digest(body)}
    output.mkdir(parents=True, exist_ok=True)
    write_canonical(output / "provider-smoke.json", receipt)
    print(
        f"provider protocol smoke passed for {args.provider}/{args.model}; "
        f"estimated_cost_usd={backend.estimated_cost_usd:.6f}; "
        f"receipt_sha256={receipt['receipt_sha256']}"
    )
    return 0


def _command_frontier_preregister(args: argparse.Namespace, study_kind: str) -> int:
    """Freeze one exact paid frontier-model cell before model outcomes exist."""
    if not args.confirm_private_response_retention:
        raise ValueError("preregistration_response_retention_unconfirmed")
    if not args.confirm_provider_account_spend_limit:
        raise ValueError("preregistration_account_limit_unconfirmed")
    root = args.root.resolve()
    all_scenario_ids = [row.scenario_id for row in load_frontier_scenarios(root / "fixtures")]
    scenario_ids = (
        all_scenario_ids if study_kind == "confirmatory_panel" else list(args.scenario or [])
    )
    policy = SpendPolicy(
        max_requests=args.max_provider_requests,
        max_output_tokens_per_request=args.max_output_tokens,
        max_total_output_tokens=args.max_total_output_tokens,
        max_cost_usd=args.max_cost_usd,
        input_usd_per_million_tokens=args.input_usd_per_million,
        output_usd_per_million_tokens=args.output_usd_per_million,
    )
    registration = build_frontier_preregistration(
        root,
        run_id=args.run_id,
        created_at=args.created_at,
        git_sha=clean_git_sha(root),
        provider=args.provider,
        requested_model=args.model,
        scenario_ids=scenario_ids,
        max_model_turns=args.max_model_turns,
        max_acts=args.max_acts,
        timeout_seconds=args.timeout_seconds,
        spend_policy=policy,
        temperature=None,
        reasoning_effort=args.reasoning_effort,
        price_source_url=args.price_source_url,
        price_checked_at=args.price_checked_at,
        retention_terms_url=args.retention_terms_url,
        retention_checked_at=args.retention_checked_at,
        derived_publication_posture=args.derived_publication_posture,
        study_kind=study_kind,
    )
    path = write_frontier_preregistration(root, registration)
    print(
        f"wrote frontier preregistration {registration['run_id']}: "
        f"sha256={registration['preregistration_sha256']}; "
        f"path={path.relative_to(root)}"
    )
    return 0


def command_frontier_preregister(args: argparse.Namespace) -> int:
    return _command_frontier_preregister(args, "confirmatory_panel")


def command_frontier_diagnostic_preregister(args: argparse.Namespace) -> int:
    return _command_frontier_preregister(args, "development_diagnostic")


def _command_frontier_registered_run(args: argparse.Namespace, expected_study_kind: str) -> int:
    """Run one exact preregistered frontier cell under its frozen study posture."""
    if not args.confirm_live_spend:
        raise ValueError("live_spend_confirmation_required")
    root = args.root.resolve()
    registration = load_frontier_preregistration(root, args.preregistration)
    if registration["study_kind"] != expected_study_kind:
        raise ValueError("frontier_run_study_kind_mismatch")
    run_id = registration["run_id"]
    cell = registration["cell"]
    execution = registration["execution"]
    output = (root / "results" / "local" / run_id).resolve()
    expected_parent = (root / "results" / "local").resolve()
    if output.parent != expected_parent:
        raise ValueError("live_output_boundary_invalid")
    if output.exists():
        raise ValueError("live_result_edition_exists")
    scenarios = load_frontier_scenarios(root / "fixtures")
    selected_ids = registration["frontier"]["scenario_ids"]
    by_id = {row.scenario_id: row for row in scenarios}
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("live_scenario_set_duplicate")
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ValueError("live_scenario_unknown:" + ",".join(missing))
    if len(selected_ids) > 20:
        raise ValueError("live_episode_count_out_of_bounds")
    policy = SpendPolicy(**registration["spend_policy"])
    private_dir = output / "private-provider-responses"
    backend = CappedProviderBackend(
        cell["provider"],
        cell["requested_model"],
        policy,
        timeout_seconds=execution["timeout_seconds"],
        response_sink=_private_response_sink(private_dir),
        temperature=cell["temperature"],
        reasoning_effort=cell["reasoning_effort"],
    )
    receipts: list[dict[str, Any]] = []
    attempt_ids = registration["frontier"]["attempt_ids_per_scenario"]
    for scenario_id in selected_ids:
        for attempt_id in attempt_ids:
            receipts.append(
                run_frontier_live_episode(
                    by_id[scenario_id],
                    backend,
                    attempt_id=attempt_id,
                    max_model_turns=execution["max_model_turns"],
                    max_acts=execution["max_acts"],
                )
            )
    if expected_study_kind == "confirmatory_panel":
        analysis = analyze_five_attempt_panel(receipts)
        artifact_schema = "gradia-frontier-live-model-panel.v2"
        artifact_filename = "panel.json"
    else:
        analysis = analyze_frontier_diagnostic(receipts)
        artifact_schema = "gradia-frontier-development-diagnostic.v1"
        artifact_filename = "diagnostic.json"
    panel_body = {
        "schema": artifact_schema,
        "study_kind": expected_study_kind,
        "claim_status": registration["claim_status"],
        "run_id": run_id,
        "preregistration_sha256": registration["preregistration_sha256"],
        "provider": cell["provider"],
        "model": cell["requested_model"],
        "adapter_version": backend.adapter_version,
        "scaffold": FRONTIER_SCAFFOLD_VERSION,
        "scenario_ids": selected_ids,
        "attempt_ids_per_scenario": attempt_ids,
        "attempt_ids_are_not_provider_seeds": True,
        "sampling_policy": backend.sampling_policy,
        "sampling_policy_sha256": backend.sampling_policy_sha256,
        "spend_policy": policy.as_dict(),
        "spend_policy_sha256": backend.policy_sha256,
        "price_evidence": registration["price_evidence"],
        "rights": registration["rights"],
        "estimated_cost_usd": backend.estimated_cost_usd,
        "conservative_reserved_cost_usd": backend.reserved_cost_usd,
        "conservative_reserved_output_tokens": backend.reserved_output_tokens,
        "cost_is_user_supplied_price_estimate_not_invoice": True,
        "operator_controls": {
            **registration["operator_controls"],
            "live_spend_confirmed_at_execution": True,
        },
        "analysis": analysis,
        "receipt_sha256s": [row["receipt_sha256"] for row in receipts],
    }
    panel = {**panel_body, "panel_sha256": digest(panel_body)}
    output.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    receipts_dir = output / "receipts"
    for row in receipts:
        filename = f"{row['scenario_id']}--attempt-{row['attempt_id']}.json"
        write_canonical(receipts_dir / filename, row)
    write_canonical(output / artifact_filename, panel)
    print(
        f"wrote local frontier {expected_study_kind} {run_id}: "
        f"estimated_cost_usd={backend.estimated_cost_usd:.6f}; "
        f"reserved_cost_usd={backend.reserved_cost_usd:.6f}; "
        f"panel_sha256={panel['panel_sha256']}"
    )
    return 0


def command_frontier_live_panel(args: argparse.Namespace) -> int:
    """Run exactly five independent requests for every candidate task."""
    return _command_frontier_registered_run(args, "confirmatory_panel")


def command_frontier_diagnostic_run(args: argparse.Namespace) -> int:
    """Run exactly one private diagnostic request for every candidate task."""
    return _command_frontier_registered_run(args, "development_diagnostic")


def _add_frontier_preregistration_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--run-id", required=True)
    command.add_argument("--created-at", required=True)
    command.add_argument(
        "--provider", choices=("openai", "anthropic", "xai", "gemini"), required=True
    )
    command.add_argument("--model", required=True)
    command.add_argument("--max-model-turns", type=int, default=32)
    command.add_argument("--max-acts", type=int, default=28)
    command.add_argument("--max-provider-requests", type=int, required=True)
    command.add_argument("--max-output-tokens", type=int, required=True)
    command.add_argument("--max-total-output-tokens", type=int, required=True)
    command.add_argument("--max-cost-usd", type=float, required=True)
    command.add_argument("--input-usd-per-million", type=float, required=True)
    command.add_argument("--output-usd-per-million", type=float, required=True)
    command.add_argument("--reasoning-effort", choices=("high",), required=True)
    command.add_argument("--timeout-seconds", type=float, default=60.0)
    command.add_argument("--price-source-url", required=True)
    command.add_argument("--price-checked-at", required=True)
    command.add_argument("--retention-terms-url", required=True)
    command.add_argument("--retention-checked-at", required=True)
    command.add_argument(
        "--derived-publication-posture",
        choices=("unknown", "not_permitted", "derived_only_permitted"),
        required=True,
    )
    command.add_argument("--confirm-private-response-retention", action="store_true")
    command.add_argument("--confirm-provider-account-spend-limit", action="store_true")


def parser() -> argparse.ArgumentParser:
    root = repository_root()
    cli = argparse.ArgumentParser(prog="gradia-universe")
    cli.add_argument("--root", type=Path, default=root, help=argparse.SUPPRESS)
    sub = cli.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run all public reference episodes")
    run.set_defaults(func=command_run)
    verify = sub.add_parser("verify", help="replay and verify committed results")
    verify.set_defaults(func=command_verify)
    public = sub.add_parser("verify-public", help="scan the release boundary")
    public.set_defaults(func=command_verify_public)
    build_public = sub.add_parser(
        "build-public", help="regenerate the deterministic public Explorer bundle"
    )
    build_public.set_defaults(func=command_build_public)
    study_build = sub.add_parser(
        "study-a-build", help="regenerate the isolated Study A engineering corpus"
    )
    study_build.set_defaults(func=command_study_a_build)
    study_verify = sub.add_parser(
        "study-a-verify", help="replay the Study A engineering corpus and report"
    )
    study_verify.set_defaults(func=command_study_a_verify)
    frontier_build = sub.add_parser(
        "frontier-build", help="regenerate frontier-candidate solvability admissions"
    )
    frontier_build.set_defaults(func=command_frontier_build)
    frontier_verify = sub.add_parser(
        "frontier-verify", help="replay frontier-candidate solvability admissions"
    )
    frontier_verify.set_defaults(func=command_frontier_verify)
    contract = sub.add_parser("gradia-contract", help="check a live Gradia API safely")
    contract.add_argument("--base-url", required=True)
    contract.set_defaults(func=command_gradia_contract)
    packet = sub.add_parser("human-packet", help="create a blinded human-review packet")
    packet.add_argument("--output", type=Path, default=root / "results" / "local")
    packet.set_defaults(func=command_human_packet)
    human = sub.add_parser("human-agreement", help="score two or more frozen reviews")
    human.add_argument("--reviews", type=Path, nargs="+", required=True)
    human.add_argument(
        "--output", type=Path, default=root / "results" / "local" / "agreement.json"
    )
    human.set_defaults(func=command_human_agreement)
    live = sub.add_parser(
        "live-panel", help="run one capped provider/model cell into ignored local evidence"
    )
    live.add_argument("--run-id", required=True)
    live.add_argument(
        "--provider", choices=("openai", "anthropic", "xai", "gemini"), required=True
    )
    live.add_argument("--model", required=True)
    live.add_argument("--scenario", action="append")
    live.add_argument("--seeds", type=int, nargs="+", default=[11])
    live.add_argument("--max-model-turns", type=int, default=12)
    live.add_argument("--max-acts", type=int, default=10)
    live.add_argument("--max-provider-requests", type=int, required=True)
    live.add_argument("--max-output-tokens", type=int, required=True)
    live.add_argument("--max-total-output-tokens", type=int, required=True)
    live.add_argument("--max-cost-usd", type=float, required=True)
    live.add_argument("--input-usd-per-million", type=float, required=True)
    live.add_argument("--output-usd-per-million", type=float, required=True)
    live.add_argument("--temperature", type=float)
    live.add_argument("--reasoning-effort", choices=("high",))
    live.add_argument("--timeout-seconds", type=float, default=60.0)
    live.add_argument("--confirm-live-spend", action="store_true")
    live.add_argument("--confirm-private-response-retention", action="store_true")
    live.add_argument("--confirm-provider-account-spend-limit", action="store_true")
    live.set_defaults(func=command_live_panel)
    smoke = sub.add_parser(
        "provider-smoke",
        help="make one capped non-benchmark request to verify a provider adapter",
    )
    smoke.add_argument("--run-id", required=True)
    smoke.add_argument(
        "--provider", choices=("openai", "anthropic", "xai", "gemini"), required=True
    )
    smoke.add_argument("--model", required=True)
    smoke.add_argument("--max-output-tokens", type=int, default=512)
    smoke.add_argument("--max-cost-usd", type=float, required=True)
    smoke.add_argument("--input-usd-per-million", type=float, required=True)
    smoke.add_argument("--output-usd-per-million", type=float, required=True)
    smoke.add_argument("--timeout-seconds", type=float, default=60.0)
    smoke.add_argument("--confirm-live-spend", action="store_true")
    smoke.add_argument("--confirm-private-response-retention", action="store_true")
    smoke.add_argument("--confirm-provider-account-spend-limit", action="store_true")
    smoke.set_defaults(func=command_provider_smoke)
    preregister = sub.add_parser(
        "frontier-preregister",
        help="freeze one clean-tree, price-capped frontier-model cell",
    )
    _add_frontier_preregistration_arguments(preregister)
    preregister.set_defaults(func=command_frontier_preregister)
    diagnostic_preregister = sub.add_parser(
        "frontier-diagnostic-preregister",
        help="freeze a one-attempt private diagnostic over one or two selected tasks",
    )
    _add_frontier_preregistration_arguments(diagnostic_preregister)
    diagnostic_preregister.add_argument("--scenario", action="append", required=True)
    diagnostic_preregister.set_defaults(func=command_frontier_diagnostic_preregister)
    frontier_live = sub.add_parser(
        "frontier-live-panel",
        help="run one preregistered provider/model cell through five attempts per task",
    )
    frontier_live.add_argument("--preregistration", type=Path, required=True)
    frontier_live.add_argument("--confirm-live-spend", action="store_true")
    frontier_live.set_defaults(func=command_frontier_live_panel)
    diagnostic_run = sub.add_parser(
        "frontier-diagnostic-run",
        help="run one preregistered private attempt on every frontier task",
    )
    diagnostic_run.add_argument("--preregistration", type=Path, required=True)
    diagnostic_run.add_argument("--confirm-live-spend", action="store_true")
    diagnostic_run.set_defaults(func=command_frontier_diagnostic_run)
    return cli


def main() -> None:
    args = parser().parse_args()
    try:
        raise SystemExit(args.func(args))
    except (OSError, ValueError) as error:
        print(f"refused: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
