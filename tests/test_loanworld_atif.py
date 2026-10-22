"""ATIF export of LoanWorld live episodes."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from gradia_universes.loanworld.atif import AtifExportError, episode_to_atif

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "results" / "loanworld" / "live"
PARENT = "loanworld-parent-dev-001"


def _load(fork: str) -> tuple[dict[str, Any], dict[str, Any]]:
    transcript = json.loads((LIVE / "transcripts" / f"{fork}.json").read_text())
    record = json.loads((LIVE / f"{fork}.json").read_text())
    return transcript, record


@pytest.mark.parametrize("fork", ["FK-00", "FK-06", "FK-13"])
def test_every_live_episode_exports_with_bound_tool_results(fork: str) -> None:
    transcript, record = _load(fork)
    atif = episode_to_atif(transcript, record, parent_id=PARENT)

    steps = atif["steps"]
    assert [s["step_id"] for s in steps] == list(range(1, len(steps) + 1))
    calls = sum(len(s.get("tool_calls", [])) for s in steps)
    uses = sum(
        1 for m in transcript["messages"] if m["role"] == "assistant"
        for b in m["content"] if b["type"] == "tool_use"
    )
    assert calls == uses
    for step in steps:
        ids = {c["tool_call_id"] for c in step.get("tool_calls", [])}
        for result in step.get("observation", {}).get("results", []):
            assert result["source_call_id"] in ids
    assert atif["extra"]["provenance_tier"] == "C"
    assert atif["extra"]["reward"] == (1.0 if record["grade"]["terminal_pass"] else 0.0)


def test_thinking_and_signatures_never_leave() -> None:
    transcript, record = _load("FK-00")
    atif = episode_to_atif(transcript, record, parent_id=PARENT)
    text = json.dumps(atif)
    assert '"signature"' not in text
    assert "thinking" not in {s.get("source") for s in atif["steps"]}
    assert atif["extra"]["thinking_blocks_dropped"] > 0


def test_held_out_episodes_are_refused() -> None:
    transcript, record = _load("FK-00")
    with pytest.raises(AtifExportError):
        episode_to_atif(transcript, record, parent_id="loanworld-parent-heldout-001")
    leaked = copy.deepcopy(transcript)
    leaked["messages"][0]["content"][0]["text"] += " loanworld-parent-heldout-002"
    with pytest.raises(AtifExportError):
        episode_to_atif(leaked, record, parent_id=PARENT)


def test_mismatched_record_is_refused() -> None:
    transcript, _ = _load("FK-00")
    _, other = _load("FK-06")
    with pytest.raises(AtifExportError):
        episode_to_atif(transcript, other, parent_id=PARENT)


def test_round_trips_through_gradias_importer() -> None:
    """Skipped where the private Gradia platform is not installed."""
    interop = pytest.importorskip("gradia.benchmark_audit.harbor_interop")
    transcript, record = _load("FK-00")
    raw = json.dumps(episode_to_atif(transcript, record, parent_id=PARENT)).encode()
    receipt = interop.import_harbor_atif(
        raw, expected_native_sha256=hashlib.sha256(raw).hexdigest()
    )
    assert receipt["assurance"]["analysis_eligible"] is True
    assert receipt["normalized"]["schema_version"] == "ATIF-v1.7"
