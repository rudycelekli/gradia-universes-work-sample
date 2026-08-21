"""Fail-closed preregistration for paid frontier-model cells."""

from __future__ import annotations

import re
import subprocess
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .canonical import digest, load_json, write_canonical
from .frontier import (
    FRONTIER_ANALYSIS_VERSION,
    FRONTIER_JUDGE_VERSION,
    FRONTIER_SCAFFOLD_VERSION,
    FrontierScenario,
    frontier_admission_report,
    frontier_judge_validation_report,
    load_frontier_scenarios,
)
from .providers import ADAPTER_VERSIONS, ProviderName, SpendPolicy, validate_model_pin

SCHEMA = "gradia-frontier-live-preregistration.v3"
_SHA = re.compile(r"[0-9a-f]{40}")
_RFC3339_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_OFFICIAL_HOSTS: dict[ProviderName, frozenset[str]] = {
    "openai": frozenset(
        {"developers.openai.com", "openai.com", "platform.openai.com"}
    ),
    "anthropic": frozenset({"platform.claude.com", "privacy.claude.com"}),
    "xai": frozenset({"docs.x.ai", "x.ai"}),
    "gemini": frozenset({"ai.google.dev", "policies.google.com"}),
}
_INTERPRETATION = (
    "Five repeated requests are descriptive observations under this exact cell. "
    "They do not establish universal model capability or research novelty."
)


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"preregistration_{label}_keys_invalid")


def clean_git_sha(root: Path) -> str:
    """Return HEAD only when the exact repository state is answerable and clean."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("preregistration_git_state_unknown") from error
    if not _SHA.fullmatch(sha):
        raise ValueError("preregistration_git_sha_invalid")
    if status:
        raise ValueError("preregistration_requires_clean_git_tree")
    return sha


def _verify_manifest_only_commit(root: Path, code_sha: str, run_id: str) -> None:
    current_sha = clean_git_sha(root)
    if current_sha == code_sha:
        raise ValueError("preregistration_manifest_not_committed")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", code_sha, current_sha],
            cwd=root,
            check=True,
            capture_output=True,
        )
        commit_count = subprocess.run(
            ["git", "rev-list", "--count", f"{code_sha}..{current_sha}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        changed = subprocess.run(
            ["git", "diff", "--name-only", f"{code_sha}..{current_sha}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("preregistration_git_lineage_invalid") from error
    if commit_count != "1":
        raise ValueError("preregistration_manifest_commit_count_invalid")
    expected = [f"preregistrations/{run_id}.json"]
    if changed != expected:
        raise ValueError("preregistration_commit_contains_nonmanifest_changes")


def _scenario_contract(row: FrontierScenario) -> dict[str, Any]:
    return {
        "scenario_id": row.scenario_id,
        "title": row.title,
        "resources": row.resources,
        "events": [event.private_contract() for event in row.events],
        "synthetic": row.synthetic,
    }


def _timestamp(value: str, field: str) -> datetime:
    if not _RFC3339_UTC.fullmatch(value):
        raise ValueError(f"preregistration_{field}_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"preregistration_{field}_invalid") from error
    if parsed.tzinfo != UTC:
        raise ValueError(f"preregistration_{field}_invalid")
    return parsed


def _official_source(provider: ProviderName, url: str, label: str) -> None:
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"preregistration_official_{label}_source_required") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _OFFICIAL_HOSTS[provider]
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or not parsed.path.startswith("/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"preregistration_official_{label}_source_required")


def build_frontier_preregistration(
    root: Path,
    *,
    run_id: str,
    created_at: str,
    git_sha: str,
    provider: ProviderName,
    requested_model: str,
    scenario_ids: list[str],
    max_model_turns: int,
    max_acts: int,
    timeout_seconds: float,
    spend_policy: SpendPolicy,
    temperature: float | None,
    reasoning_effort: str,
    price_source_url: str,
    price_checked_at: str,
    retention_terms_url: str,
    retention_checked_at: str,
    derived_publication_posture: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise ValueError("preregistration_run_id_invalid")
    created = _timestamp(created_at, "created_at")
    price_checked = _timestamp(price_checked_at, "price_checked_at")
    retention_checked = _timestamp(retention_checked_at, "retention_checked_at")
    for checked, label in (
        (price_checked, "price_checked_at"),
        (retention_checked, "retention_checked_at"),
    ):
        if checked > created or created - checked > timedelta(days=7):
            raise ValueError(f"preregistration_{label}_not_current_at_creation")
    if not _SHA.fullmatch(git_sha):
        raise ValueError("preregistration_git_sha_invalid")
    try:
        validate_model_pin(requested_model)
    except ValueError as error:
        raise ValueError("preregistration_model_invalid") from error
    if (
        not isinstance(max_model_turns, int)
        or isinstance(max_model_turns, bool)
        or not 1 <= max_model_turns <= 64
        or not isinstance(max_acts, int)
        or isinstance(max_acts, bool)
        or not 1 <= max_acts <= 48
    ):
        raise ValueError("preregistration_execution_limits_invalid")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not 1 <= timeout_seconds <= 300
    ):
        raise ValueError("preregistration_timeout_invalid")
    temperature_max = 1 if provider == "anthropic" else 2
    if temperature is not None and (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not 0 <= temperature <= temperature_max
    ):
        raise ValueError("preregistration_temperature_invalid")
    if reasoning_effort != "high":
        raise ValueError("preregistration_reasoning_effort_must_be_high")
    if temperature is not None:
        raise ValueError("preregistration_reasoning_temperature_must_use_default")
    publication_postures = {"unknown", "not_permitted", "derived_only_permitted"}
    if derived_publication_posture not in publication_postures:
        raise ValueError("preregistration_publication_posture_invalid")
    _official_source(provider, price_source_url, "price")
    _official_source(provider, retention_terms_url, "retention")

    rows = load_frontier_scenarios(root / "fixtures")
    by_id = {row.scenario_id: row for row in rows}
    if (
        not 1 <= len(scenario_ids) <= 20
        or any(not isinstance(row, str) for row in scenario_ids)
        or len(scenario_ids) != len(set(scenario_ids))
    ):
        raise ValueError("preregistration_scenario_set_invalid")
    missing = sorted(set(scenario_ids) - set(by_id))
    if missing:
        raise ValueError("preregistration_scenario_unknown:" + ",".join(missing))
    complete_panel = [row.scenario_id for row in rows]
    if scenario_ids != complete_panel:
        raise ValueError("preregistration_requires_complete_frontier_panel")
    admission = frontier_admission_report(root / "fixtures")
    judge_validation = frontier_judge_validation_report(root / "fixtures")
    body = {
        "schema": SCHEMA,
        "claim_status": "private_pre_results",
        "run_id": run_id,
        "created_at": created_at,
        "git": {"sha": git_sha, "dirty": False},
        "frontier": {
            "scenario_ids": scenario_ids,
            "scenario_sha256s": {
                scenario_id: digest(_scenario_contract(by_id[scenario_id]))
                for scenario_id in scenario_ids
            },
            "scaffold_version": FRONTIER_SCAFFOLD_VERSION,
            "judge_version": FRONTIER_JUDGE_VERSION,
            "analysis_version": FRONTIER_ANALYSIS_VERSION,
            "admission_report_sha256": admission["report_sha256"],
            "judge_validation_report_sha256": judge_validation["report_sha256"],
            "attempt_ids_per_scenario": [1, 2, 3, 4, 5],
        },
        "cell": {
            "provider": provider,
            "requested_model": requested_model,
            "adapter_version": ADAPTER_VERSIONS[provider],
            "temperature": temperature,
            "temperature_posture": (
                "explicit" if temperature is not None else "provider_default"
            ),
            "reasoning_effort": reasoning_effort,
            "reasoning_effort_posture": "explicit",
            "provider_seed": None,
            "model_identity_policy": "provider_resolved_must_equal_requested",
        },
        "execution": {
            "max_model_turns": max_model_turns,
            "max_acts": max_acts,
            "timeout_seconds": timeout_seconds,
        },
        "spend_policy": spend_policy.as_dict(),
        "price_evidence": {
            "official_source_url": price_source_url,
            "checked_at": price_checked_at,
            "operator_supplied_not_provider_invoice": True,
        },
        "rights": {
            "operator_attests_private_raw_response_retention_permitted": True,
            "official_terms_url": retention_terms_url,
            "checked_at": retention_checked_at,
            "operator_assessed_derived_publication_posture": derived_publication_posture,
        },
        "operator_controls": {
            "operator_attests_provider_account_spend_limit_enabled": True,
            "live_spend_confirmation_required": True,
        },
        "interpretation": _INTERPRETATION,
    }
    return {**body, "preregistration_sha256": digest(body)}


def verify_frontier_preregistration(
    root: Path, value: dict[str, Any], *, verify_git: bool = True
) -> dict[str, Any]:
    _exact_keys(
        value,
        {
            "schema",
            "claim_status",
            "run_id",
            "created_at",
            "git",
            "frontier",
            "cell",
            "execution",
            "spend_policy",
            "price_evidence",
            "rights",
            "operator_controls",
            "interpretation",
            "preregistration_sha256",
        },
        "top_level",
    )
    body = deepcopy(value)
    claimed = body.pop("preregistration_sha256", None)
    if body.get("schema") != SCHEMA or claimed != digest(body):
        raise ValueError("preregistration_digest_invalid")
    if body.get("claim_status") != "private_pre_results":
        raise ValueError("preregistration_claim_status_invalid")
    run_id = body.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise ValueError("preregistration_run_id_invalid")
    created = _timestamp(str(body.get("created_at", "")), "created_at")
    git = body.get("git")
    if (
        not isinstance(git, dict)
        or git.get("dirty") is not False
        or not _SHA.fullmatch(str(git.get("sha", "")))
    ):
        raise ValueError("preregistration_git_contract_invalid")
    _exact_keys(git, {"sha", "dirty"}, "git")
    if verify_git:
        _verify_manifest_only_commit(root, git["sha"], run_id)

    cell = body.get("cell")
    frontier = body.get("frontier")
    execution = body.get("execution")
    rights = body.get("rights")
    controls = body.get("operator_controls")
    price = body.get("price_evidence")
    spend = body.get("spend_policy")
    sections = (cell, frontier, execution, rights, controls, price, spend)
    if not all(isinstance(row, dict) for row in sections):
        raise ValueError("preregistration_contract_invalid")
    assert isinstance(cell, dict) and isinstance(frontier, dict)
    assert isinstance(execution, dict) and isinstance(rights, dict)
    assert isinstance(controls, dict) and isinstance(price, dict)
    assert isinstance(spend, dict)
    _exact_keys(
        frontier,
        {
            "scenario_ids",
            "scenario_sha256s",
            "scaffold_version",
            "judge_version",
            "analysis_version",
            "admission_report_sha256",
            "judge_validation_report_sha256",
            "attempt_ids_per_scenario",
        },
        "frontier",
    )
    _exact_keys(
        cell,
        {
            "provider",
            "requested_model",
            "adapter_version",
            "temperature",
            "temperature_posture",
            "reasoning_effort",
            "reasoning_effort_posture",
            "provider_seed",
            "model_identity_policy",
        },
        "cell",
    )
    _exact_keys(
        execution,
        {"max_model_turns", "max_acts", "timeout_seconds"},
        "execution",
    )
    _exact_keys(
        spend,
        {
            "max_requests",
            "max_output_tokens_per_request",
            "max_total_output_tokens",
            "max_cost_usd",
            "input_usd_per_million_tokens",
            "output_usd_per_million_tokens",
        },
        "spend_policy",
    )
    _exact_keys(
        price,
        {"official_source_url", "checked_at", "operator_supplied_not_provider_invoice"},
        "price_evidence",
    )
    _exact_keys(
        rights,
        {
            "operator_attests_private_raw_response_retention_permitted",
            "official_terms_url",
            "checked_at",
            "operator_assessed_derived_publication_posture",
        },
        "rights",
    )
    _exact_keys(
        controls,
        {
            "operator_attests_provider_account_spend_limit_enabled",
            "live_spend_confirmation_required",
        },
        "operator_controls",
    )
    provider = cell.get("provider")
    if (
        provider not in ADAPTER_VERSIONS
        or cell.get("adapter_version") != ADAPTER_VERSIONS[provider]
    ):
        raise ValueError("preregistration_adapter_drift")
    _official_source(provider, str(price.get("official_source_url", "")), "price")
    price_checked = _timestamp(str(price.get("checked_at", "")), "price_checked_at")
    if price.get("operator_supplied_not_provider_invoice") is not True:
        raise ValueError("preregistration_price_posture_invalid")
    if rights.get("operator_attests_private_raw_response_retention_permitted") is not True:
        raise ValueError("preregistration_response_retention_not_permitted")
    _official_source(provider, str(rights.get("official_terms_url", "")), "retention")
    retention_checked = _timestamp(
        str(rights.get("checked_at", "")), "retention_checked_at"
    )
    for checked, label in (
        (price_checked, "price_checked_at"),
        (retention_checked, "retention_checked_at"),
    ):
        if checked > created or created - checked > timedelta(days=7):
            raise ValueError(f"preregistration_{label}_not_current_at_creation")
    if rights.get("operator_assessed_derived_publication_posture") not in {
        "unknown",
        "not_permitted",
        "derived_only_permitted",
    }:
        raise ValueError("preregistration_publication_posture_invalid")
    if controls.get("operator_attests_provider_account_spend_limit_enabled") is not True:
        raise ValueError("preregistration_account_limit_unconfirmed")
    if controls.get("live_spend_confirmation_required") is not True:
        raise ValueError("preregistration_live_confirmation_invalid")
    try:
        SpendPolicy(**spend)
    except (TypeError, ValueError) as error:
        raise ValueError("preregistration_spend_policy_invalid") from error
    requested_model = cell.get("requested_model")
    if not isinstance(requested_model, str):
        raise ValueError("preregistration_model_invalid")
    try:
        validate_model_pin(requested_model)
    except ValueError as error:
        raise ValueError("preregistration_model_invalid") from error
    temperature = cell.get("temperature")
    if temperature is not None and (
        isinstance(temperature, bool) or not isinstance(temperature, (int, float))
    ):
        raise ValueError("preregistration_temperature_invalid")
    expected_temperature_posture = "explicit" if temperature is not None else "provider_default"
    if cell.get("temperature_posture") != expected_temperature_posture:
        raise ValueError("preregistration_temperature_posture_invalid")
    if cell.get("reasoning_effort") != "high":
        raise ValueError("preregistration_reasoning_effort_must_be_high")
    if cell.get("reasoning_effort_posture") != "explicit":
        raise ValueError("preregistration_reasoning_effort_posture_invalid")
    if temperature is not None:
        raise ValueError("preregistration_reasoning_temperature_must_use_default")
    if cell.get("provider_seed") is not None:
        raise ValueError("preregistration_provider_seed_invalid")
    if cell.get("model_identity_policy") != "provider_resolved_must_equal_requested":
        raise ValueError("preregistration_model_identity_policy_invalid")
    max_temperature = 1 if provider == "anthropic" else 2
    if temperature is not None and not 0 <= temperature <= max_temperature:
        raise ValueError("preregistration_temperature_invalid")
    max_turns = execution.get("max_model_turns")
    max_acts = execution.get("max_acts")
    timeout_seconds = execution.get("timeout_seconds")
    if (
        not isinstance(max_turns, int)
        or isinstance(max_turns, bool)
        or not 1 <= max_turns <= 64
    ):
        raise ValueError("preregistration_execution_limits_invalid")
    if (
        not isinstance(max_acts, int)
        or isinstance(max_acts, bool)
        or not 1 <= max_acts <= 48
    ):
        raise ValueError("preregistration_execution_limits_invalid")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not 1 <= timeout_seconds <= 300
    ):
        raise ValueError("preregistration_timeout_invalid")

    rows = load_frontier_scenarios(root / "fixtures")
    by_id = {row.scenario_id: row for row in rows}
    scenario_ids = frontier.get("scenario_ids")
    if (
        not isinstance(scenario_ids, list)
        or not 1 <= len(scenario_ids) <= 20
        or any(not isinstance(row, str) for row in scenario_ids)
        or len(scenario_ids) != len(set(scenario_ids))
    ):
        raise ValueError("preregistration_scenario_set_invalid")
    expected_scenarios = {
        scenario_id: digest(_scenario_contract(by_id[scenario_id]))
        for scenario_id in scenario_ids
        if scenario_id in by_id
    }
    if (
        len(expected_scenarios) != len(scenario_ids)
        or frontier.get("scenario_sha256s") != expected_scenarios
    ):
        raise ValueError("preregistration_scenario_drift")
    if scenario_ids != [row.scenario_id for row in rows]:
        raise ValueError("preregistration_requires_complete_frontier_panel")
    if frontier.get("scaffold_version") != FRONTIER_SCAFFOLD_VERSION:
        raise ValueError("preregistration_scaffold_drift")
    if frontier.get("judge_version") != FRONTIER_JUDGE_VERSION:
        raise ValueError("preregistration_judge_drift")
    if frontier.get("analysis_version") != FRONTIER_ANALYSIS_VERSION:
        raise ValueError("preregistration_analysis_drift")
    if frontier.get("attempt_ids_per_scenario") != [1, 2, 3, 4, 5]:
        raise ValueError("preregistration_attempts_invalid")
    admission_sha = frontier_admission_report(root / "fixtures")["report_sha256"]
    if frontier.get("admission_report_sha256") != admission_sha:
        raise ValueError("preregistration_admission_drift")
    judge_validation_sha = frontier_judge_validation_report(root / "fixtures")[
        "report_sha256"
    ]
    if frontier.get("judge_validation_report_sha256") != judge_validation_sha:
        raise ValueError("preregistration_judge_validation_drift")
    if body.get("interpretation") != _INTERPRETATION:
        raise ValueError("preregistration_interpretation_invalid")
    return value


def load_frontier_preregistration(root: Path, path: Path) -> dict[str, Any]:
    expected = (root / "preregistrations").resolve()
    resolved = path.resolve()
    if resolved.parent != expected:
        raise ValueError("preregistration_path_outside_local_boundary")
    return verify_frontier_preregistration(root, load_json(resolved))


def write_frontier_preregistration(root: Path, value: dict[str, Any]) -> Path:
    target = root / "preregistrations" / f"{value['run_id']}.json"
    if target.exists():
        raise ValueError("preregistration_edition_exists")
    write_canonical(target, value)
    return target
