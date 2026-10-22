"""Export a LoanWorld live episode as an ATIF trajectory.

ATIF is Harbor's Agent Trajectory Interchange Format.

The input is the pair the live runner writes: ``results/loanworld/live/transcripts/<fork>.json``
(Anthropic Messages, ``{"episode", "messages"}``) and ``results/loanworld/live/<fork>.json``
(the graded episode record, schema ``gradia.loanworld.live-episode.v0``).

Mapping:

* each assistant message becomes one ``agent`` step; its ``text`` blocks are the message and its
  ``tool_use`` blocks are ``tool_calls``;
* the ``tool_result`` blocks in the next user message become that step's ``observation``, each
  bound to its call by ``source_call_id``;
* any other user text (the opening file snapshot) becomes a ``user`` step;
* token usage, cost and the oracle grade go in ``final_metrics`` and ``extra``.

Refusals, not redactions:

* only dev parents export. A held-out episode is evaluation access, never a file, so an episode
  whose parent or transcript names a held-out parent is refused;
* thinking blocks and their signatures are dropped and only counted. Model reasoning is not
  ours to license, and a provider's terms may restrict using it for training.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ATIF_VERSION = "ATIF-v1.7"
EPISODE_SCHEMA = "gradia.loanworld.live-episode.v0"
DEV_PARENT_PREFIX = "loanworld-parent-dev-"
HELDOUT_MARKER = "loanworld-parent-heldout"


class AtifExportError(ValueError):
    """The episode cannot be exported."""


def _blocks(message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        raise AtifExportError("message content must be a string or a list of blocks")
    return content


def _result_content(block: dict[str, Any]) -> str:
    """Flatten a tool_result's content. Images are kept as a reference to their digest."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content or []:
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
        elif item.get("type") == "image":
            parts.append(f"[image sha256={item.get('sha256', 'unknown')}]")
    return "\n".join(parts)


def episode_to_atif(
    transcript: dict[str, Any],
    record: dict[str, Any],
    *,
    parent_id: str,
    agent_name: str = "gradia-loanworld-stdio",
    agent_version: str = "0.1.0",
) -> dict[str, Any]:
    """Build one ATIF trajectory. Raises AtifExportError rather than export anything unsafe."""

    if record.get("schema") != EPISODE_SCHEMA:
        raise AtifExportError(f"record schema must be {EPISODE_SCHEMA}")
    if not parent_id.startswith(DEV_PARENT_PREFIX):
        raise AtifExportError(
            "only dev parents export; held-out episodes are evaluation access"
        )
    if transcript.get("episode") != record.get("fork_id"):
        raise AtifExportError("transcript and record are for different episodes")
    if HELDOUT_MARKER in json.dumps(transcript):
        raise AtifExportError("transcript names a held-out parent")

    model = record.get("model")
    steps: list[dict[str, Any]] = []
    thinking_dropped = 0
    pending: dict[str, Any] | None = None  # the agent step awaiting its tool results

    for message in transcript.get("messages", []):
        role = message.get("role")
        blocks = _blocks(message)
        if role == "assistant":
            texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            calls = [
                {
                    "tool_call_id": b["id"],
                    "function_name": b["name"],
                    "arguments": b.get("input") or {},
                }
                for b in blocks
                if b.get("type") == "tool_use"
            ]
            thinking_dropped += sum(
                1 for b in blocks if b.get("type") in {"thinking", "redacted_thinking"}
            )
            step: dict[str, Any] = {
                "step_id": len(steps) + 1,
                "source": "agent",
                "model_name": model,
                "message": "\n".join(t for t in texts if t),
            }
            if calls:
                step["tool_calls"] = calls
            steps.append(step)
            pending = step if calls else None
        elif role == "user":
            results = [b for b in blocks if b.get("type") == "tool_result"]
            others = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            if results:
                if pending is None:
                    raise AtifExportError("tool_result with no preceding tool_use")
                call_ids = {c["tool_call_id"] for c in pending["tool_calls"]}
                observed = []
                for b in results:
                    if b.get("tool_use_id") not in call_ids:
                        raise AtifExportError("tool_result does not answer the previous step")
                    observed.append(
                        {"source_call_id": b["tool_use_id"], "content": _result_content(b)}
                    )
                pending["observation"] = {"results": observed}
                pending = None
            if others:
                steps.append(
                    {"step_id": len(steps) + 1, "source": "user", "message": "\n".join(others)}
                )
        else:
            raise AtifExportError(f"unsupported role {role!r}")

    if not steps:
        raise AtifExportError("episode has no steps")

    usage = record.get("usage") or {}
    grade = record.get("grade") or {}
    return {
        "schema_version": ATIF_VERSION,
        "session_id": f"{parent_id}/{record['fork_id']}",
        "trajectory_id": record.get("record_sha256") or f"{parent_id}/{record['fork_id']}",
        "agent": {"name": agent_name, "version": agent_version, "model_name": model},
        "steps": steps,
        "final_metrics": {
            "total_prompt_tokens": usage.get("input", 0)
            + usage.get("cache_read", 0)
            + usage.get("cache_write", 0),
            "total_completion_tokens": usage.get("output", 0),
            "total_cached_tokens": usage.get("cache_read", 0),
            "total_cost_usd": record.get("cost_usd"),
            "total_steps": len(steps),
        },
        "extra": {
            "provenance_tier": "C",  # ADR-0090: synthetic-world trace
            "world": "loanworld",
            "parent_id": parent_id,
            "fork_id": record["fork_id"],
            "outcome": record.get("outcome"),
            "reward": 1.0 if grade.get("terminal_pass") else 0.0,
            "grade": grade,
            "proof_pack_sha256": record.get("proof_pack_sha256"),
            "record_sha256": record.get("record_sha256"),
            "thinking_blocks_dropped": thinking_dropped,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a LoanWorld live episode as ATIF.")
    parser.add_argument("transcript", type=Path)
    parser.add_argument("record", type=Path)
    parser.add_argument("--parent-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    trajectory = episode_to_atif(
        json.loads(args.transcript.read_text()),
        json.loads(args.record.read_text()),
        parent_id=args.parent_id,
    )
    args.out.write_text(json.dumps(trajectory, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
