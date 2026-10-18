"""Scripted control policies for LoanWorld.

v0 ships only the null policy (always escalate). It is the smoke control for the
harness and the floor of the autonomy/critical-failure trade-off: it should
score zero critical failures and zero autonomy. The scripted reference policy
(solvability), the credulous policy (critical-failure surface) and their
graders belong to later phases.
"""

from __future__ import annotations

from typing import Any


def null_agent(message: dict[str, Any]) -> dict[str, Any]:
    if message["type"] == "start":
        return {
            "type": "call",
            "tool": "escalate",
            "args": {"reason": "Null control policy: hands every file to a human."},
        }
    return {
        "type": "call",
        "tool": "submit",
        "args": {"recommendation": "ESCALATE", "open_conditions": [], "account": []},
    }


def reference_plan(bundle: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Scripted positive control for the gold parent and its invariance forks.

    It reads truth from the bundle on purpose: a positive control proves an
    episode is solvable and measures false rejections (autoimmunity). It is not
    a baseline and never appears in a results table as an agent.
    """
    case = bundle["scenario"]["ledgers"]["case"]
    annual = case["employment"]["annual_base"]
    monthly = -(-annual // 12)
    total_liabilities = sum(
        row["payment"]
        for row in case["liabilities"]["disclosed"] + case["liabilities"]["hidden"]
    )

    def money(cents: int) -> str:
        return f"{cents // 100:,}.{cents % 100:02d}"

    def page(upload_id: str, number: int = 1) -> dict[str, Any]:
        return {"upload_id": upload_id, "page": number}

    reads = [
        ("U-001", 1),
        ("U-002", 1),
        ("U-003", 1),
        ("U-004", 1),
        ("U-005", 1),
        ("U-005", 2),
        ("U-006", 1),
        ("U-007", 1),
        ("U-008", 1),
    ]
    plan: list[tuple[str, dict[str, Any]]] = [
        ("get_page", {"upload_id": u, "page": p}) for u, p in reads
    ]
    plan += [("order_service", {"kind": k}) for k in ("credit", "aus", "appraisal", "title")]
    plan += [
        (
            "send_message",
            {
                "party": "P-HR",
                "channel": "phone",
                "text": "Please verify employment and current base pay.",
            },
        ),
        (
            "flag",
            {
                "code": "TEXT_LAYER_MISMATCH",
                "target": "D-007",
                "citations": [page("U-006"), {"event_id": "R-001"}],
                "note": "VOE text layer base pay differs from the rendered page and HR.",
            },
        ),
        (
            "flag",
            {
                "code": "LOX_REQUIRED",
                "target": "services.credit",
                "citations": [{"service": "credit"}],
                "note": "Credit shows a new installment loan not on the application.",
            },
        ),
        (
            "write_los_field",
            {"key": "L-0010", "value": money(monthly), "citation": page("U-001")},
        ),
        (
            "write_los_field",
            {
                "key": "L-0040",
                "value": money(total_liabilities),
                "citation": {"service": "credit"},
            },
        ),
        (
            "write_los_field",
            {
                "key": "L-0021",
                "value": money(case["gift"]["amount"]),
                "citation": page("U-008"),
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": "C-001",
                "note": "Stub plus two W-2s.",
                "citations": [page("U-001"), page("U-003"), page("U-004")],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": "C-002",
                "note": "Two consecutive statements.",
                "citations": [page("U-005", 1), page("U-005", 2)],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": "C-003",
                "note": "Gift letter and deposit.",
                "citations": [page("U-008"), page("U-005", 2)],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": "C-004",
                "note": "Signed VOE (pixels) and HR.",
                "citations": [page("U-006"), {"event_id": "R-001"}],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": "C-005",
                "note": "Appraisal supports price.",
                "citations": [{"service": "appraisal"}],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": "C-006",
                "note": "Vesting matches seller.",
                "citations": [{"service": "title"}],
            },
        ),
    ]
    gross = case["pay_stubs"][0]["gross"]
    account = [
        {
            "claim": f"Current gross pay per biweekly period is ${money(gross)}.",
            "citations": [page("U-001")],
        },
        {
            "claim": f"Gift funds of ${money(case['gift']['amount'])} were deposited.",
            "citations": [page("U-008"), page("U-005", 2)],
        },
        {
            "claim": "Credit shows an undisclosed installment loan; LOX requested.",
            "citations": [{"service": "credit"}],
        },
    ]
    plan.append(
        (
            "submit",
            {"recommendation": "CONDITIONAL", "open_conditions": ["C-007"], "account": account},
        )
    )
    return plan


def plan_agent(plan: list[tuple[str, dict[str, Any]]]) -> Any:
    """Replay a fixed plan of tool calls, one per message."""
    steps = iter(plan)

    def agent(message: dict[str, Any]) -> dict[str, Any]:
        tool, args = next(steps)
        return {"type": "call", "tool": tool, "args": args}

    return agent


def make_reference_agent(bundle: dict[str, Any]) -> Any:
    return plan_agent(reference_plan(bundle))
