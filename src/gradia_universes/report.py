"""Generate a human-readable report from exact panel receipts."""

from __future__ import annotations

from typing import Any


def _pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def render_markdown(panel: dict[str, Any]) -> str:
    lines = [
        "# Synthetic Underwriting Universe — reference results",
        "",
        "> Scripted-policy harness validation only; not a model capability estimate.",
        "",
        "These numbers are generated from the committed receipts by `gradia-universe run`.",
        "The verification command reruns all cells and requires byte-identical output.",
        "",
        "## Panel",
        "",
        f"- Scenarios: {panel['scenario_count']}",
        f"- Deterministic agent policies: {panel['agent_policy_count']}",
        f"- Episodes: {panel['episode_count']}",
        f"- Environment failures: {panel['environment_failures']}",
        "",
        "| Agent policy | Perfect passes | Episodes | Pass rate | Wilson 95% interval |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in panel["by_agent"]:
        low, high = row["wilson_95"]
        lines.append(
            f"| `{row['agent_policy']}` | {row['passes']} | {row['episodes']} | "
            f"{_pct(row['pass_rate'])} | {_pct(low)} to {_pct(high)} |"
        )
    lines.extend(
        [
            "",
            "## Condition sensitivity",
            "",
            "The tier below is diagnostic for these three scripted policies only. It is not an",
            "empirical model-difficulty label.",
            "",
            "| Scenario | Perfect passes | Episodes | Pass rate | Harness tier |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in panel["by_scenario"]:
        lines.append(
            f"| `{row['scenario_id']}` | {row['passes']} | {row['episodes']} | "
            f"{_pct(row['pass_rate'])} | {row['scripted_harness_tier']} |"
        )
    lines.extend(
        [
            "",
            "## Failure taxonomy",
            "",
            "A receipt may carry more than one evidence-preserving label.",
            "",
            "| Failure class | Episode count |",
            "|---|---:|",
        ]
    )
    for label, count in panel["failure_taxonomy"].items():
        lines.append(f"| `{label}` | {count} |")
    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"Panel report SHA-256: `{panel['report_sha256']}`",
            "",
            "Each episode also binds the frozen scenario, environment fingerprint, action",
            "ledger, visible event projection, before/after world roots, restore lineage,",
            "terminal submission, criterion verdict and failure labels into its own receipt",
            "digest. `gradia-universe verify` replays rather than trusting those hashes.",
            "",
        ]
    )
    return "\n".join(lines)
