"""Blinded human-review packet and agreement analysis."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .canonical import digest, write_canonical

CRITERIA = (
    "recommendation_correct",
    "current_world_root",
    "authoritative_evidence",
    "changed_world_adaptation",
    "output_contract",
)
DECISIONS = {"yes", "no", "cannot_assess"}


def build_packet(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for receipt in receipts:
        item_id = digest(
            {
                "study": "gradia-public-human-calibration.v1",
                "receipt_sha256": receipt["receipt_sha256"],
            }
        )[:20]
        items.append(
            {
                "review_item_id": item_id,
                "receipt_sha256": receipt["receipt_sha256"],
                "task": "Apply the synthetic policy to current authoritative evidence.",
                "acts": receipt["acts"],
                "evolution_witness": receipt["evolution_witness"],
                "restore_receipts": receipt["restore_receipts"],
                "judge_evidence": receipt["judge_evidence"],
                "submission": receipt["submission"],
            }
        )
    items.sort(key=lambda row: row["review_item_id"])
    body = {
        "schema": "gradia-public-human-review-packet.v1",
        "blinding": (
            "Agent policy, scenario label and deterministic verdict are omitted. "
            "Do not inspect results/reference until the review file is frozen."
        ),
        "criteria": list(CRITERIA),
        "items": items,
    }
    return {**body, "packet_sha256": digest(body)}


def write_packet(receipts: list[dict[str, Any]], target: Path) -> tuple[Path, Path]:
    packet = build_packet(receipts)
    json_path = target / "human-review-packet.json"
    csv_path = target / "human-review-template.csv"
    write_canonical(json_path, packet)
    target.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["review_item_id", "reviewer_id", *CRITERIA, "reason"],
        )
        writer.writeheader()
        for item in packet["items"]:
            writer.writerow(
                {
                    "review_item_id": item["review_item_id"],
                    "reviewer_id": "",
                    **{criterion: "" for criterion in CRITERIA},
                    "reason": "",
                }
            )
    return json_path, csv_path


def _load_review(path: Path) -> tuple[str, dict[str, dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"human_review_empty:{path}")
    reviewer_ids = {row.get("reviewer_id", "").strip() for row in rows}
    if "" in reviewer_ids or len(reviewer_ids) != 1:
        raise ValueError(f"human_review_reviewer_id_invalid:{path}")
    reviewer_id = next(iter(reviewer_ids))
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        item_id = row.get("review_item_id", "").strip()
        if not item_id or item_id in indexed:
            raise ValueError(f"human_review_item_id_invalid:{path}")
        for criterion in CRITERIA:
            decision = row.get(criterion, "").strip()
            if decision not in DECISIONS:
                raise ValueError(
                    f"human_review_decision_invalid:{path}:{item_id}:{criterion}"
                )
        if not row.get("reason", "").strip():
            raise ValueError(f"human_review_reason_required:{path}:{item_id}")
        indexed[item_id] = row
    return reviewer_id, indexed


def _kappa(left: list[bool], right: list[bool]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    left_yes = sum(left) / len(left)
    right_yes = sum(right) / len(right)
    expected = left_yes * right_yes + (1 - left_yes) * (1 - right_yes)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def agreement(
    receipts: list[dict[str, Any]], review_paths: list[Path]
) -> dict[str, Any]:
    if len(review_paths) < 2:
        raise ValueError("two_human_review_files_required")
    packet = build_packet(receipts)
    receipt_by_id = {
        item["review_item_id"]: next(
            row for row in receipts if row["receipt_sha256"] == item["receipt_sha256"]
        )
        for item in packet["items"]
    }
    loaded = [_load_review(path) for path in review_paths]
    reviewer_ids = [row[0] for row in loaded]
    if len(reviewer_ids) != len(set(reviewer_ids)):
        raise ValueError("human_reviewers_must_be_distinct")
    required_ids = set(receipt_by_id)
    for reviewer_id, rows in loaded:
        if set(rows) != required_ids:
            raise ValueError(f"human_review_coverage_mismatch:{reviewer_id}")
    reviewer_reports = []
    for reviewer_id, rows in loaded:
        criteria_report: dict[str, Any] = {}
        for criterion in CRITERIA:
            human: list[bool] = []
            machine: list[bool] = []
            cannot_assess = 0
            for item_id in sorted(required_ids):
                decision = rows[item_id][criterion]
                if decision == "cannot_assess":
                    cannot_assess += 1
                    continue
                human.append(decision == "yes")
                machine.append(bool(receipt_by_id[item_id]["verdict"]["criteria"][criterion]))
            agreements = sum(
                a == b for a, b in zip(human, machine, strict=True)
            )
            criteria_report[criterion] = {
                "assessed": len(human),
                "cannot_assess": cannot_assess,
                "raw_agreement": agreements / len(human) if human else None,
                "cohen_kappa": _kappa(human, machine),
            }
        reviewer_reports.append(
            {"reviewer_id": reviewer_id, "criteria": criteria_report}
        )
    body = {
        "schema": "gradia-public-human-agreement.v1",
        "packet_sha256": packet["packet_sha256"],
        "reviewer_count": len(loaded),
        "item_count": len(required_ids),
        "reviewers": reviewer_reports,
        "adjudication_required": [
            item_id
            for item_id in sorted(required_ids)
            if any(
                len({rows[item_id][criterion] for _, rows in loaded}) > 1
                for criterion in CRITERIA
            )
        ],
    }
    return {**body, "agreement_sha256": digest(body)}


def load_agreement_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("agreement_json_object_required")
    return value

