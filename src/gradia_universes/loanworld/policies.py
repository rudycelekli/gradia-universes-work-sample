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
    """Scripted positive control for a gold parent and its invariance forks.

    It reads truth from the bundle on purpose: a positive control proves an
    episode is solvable and measures false rejections (autoimmunity). It is not
    a baseline and never appears in a results table as an agent. Since phase 7 it
    finds every document and condition through ``topology.derive``; on dev-001 it
    emits exactly the plan it emitted before.
    """
    from .oracle import Truth  # truth-reading by design; local import avoids a cycle

    scenario = bundle["scenario"]
    ledgers = scenario["ledgers"]
    case = ledgers["case"]
    truth = Truth({"scenario": scenario}, None)
    topo = truth.topology
    annual = case["employment"]["annual_base"]
    monthly = -(-annual // 12)
    total_liabilities = sum(
        row["payment"]
        for row in case["liabilities"]["disclosed"] + case["liabilities"]["hidden"]
    )

    def money(cents: int) -> str:
        return f"{cents // 100:,}.{cents % 100:02d}"

    def page(doc_id: str) -> dict[str, Any]:
        return topo.page(doc_id)

    plan: list[tuple[str, dict[str, Any]]] = [
        ("get_page", {"upload_id": upload_id, "page": number})
        for upload_id, upload in sorted(ledgers["uploads"].items())
        for number in range(1, len(upload["pages"]) + 1)
    ]
    plan += [("order_service", {"kind": k}) for k in ("credit", "aus", "appraisal", "title")]
    plan.append(
        (
            "send_message",
            {
                "party": "P-HR",
                "channel": "phone",
                "text": "Please verify employment and current base pay.",
            },
        )
    )
    lies = set(truth.text_layer_lies())
    for voe in topo.voes:
        if voe in lies:
            plan.append(
                (
                    "flag",
                    {
                        "code": "TEXT_LAYER_MISMATCH",
                        "target": voe,
                        "citations": [page(voe), {"event_id": "R-001"}],
                        "note": (
                            "VOE text layer base pay differs from the rendered page and HR."
                        ),
                    },
                )
            )
    gift = topo.gift_letters[0]
    plan += [
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
            {"key": "L-0010", "value": money(monthly), "citation": page(topo.newest_stub)},
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
            {"key": "L-0021", "value": money(case["gift"]["amount"]), "citation": page(gift)},
        ),
        (
            "clear_condition",
            {
                "condition_id": topo.condition("income"),
                "note": "Stub plus two W-2s.",
                "citations": [
                    page(d) for d in topo.requirements[topo.condition("income")]["docs"]
                ],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": topo.condition("statements"),
                "note": "Two consecutive statements.",
                "citations": [
                    page(d) for d in topo.requirements[topo.condition("statements")]["docs"]
                ],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": topo.condition("appraisal"),
                "note": "Appraisal supports price.",
                "citations": [{"service": "appraisal"}],
            },
        ),
        (
            "clear_condition",
            {
                "condition_id": topo.condition("title"),
                "note": "Vesting matches seller.",
                "citations": [{"service": "title"}],
            },
        ),
    ]
    late = 10**6
    for doc_id in sorted(topo.anchors):
        if truth.is_stale(doc_id, late):
            plan.append(
                (
                    "flag",
                    {
                        "code": "DOCUMENT_EXPIRED",
                        "target": doc_id,
                        "citations": [page(doc_id)],
                        "note": "Past the recency window; superseded by a newer one on file.",
                    },
                )
            )
    # 0.4.0 truth: an unsigned gift letter cannot satisfy "signed gift letter", and an
    # altered VOE satisfies nothing, so those stay open and are re-requested.
    open_conditions = list(topo.ptf_conditions())
    signed = truth.is_signed(gift)
    if signed:
        plan.append(
            (
                "clear_condition",
                {
                    "condition_id": topo.condition("gift"),
                    "note": "Signed gift letter and the deposit.",
                    "citations": [page(gift), page(topo.deposit_statement or gift)],
                },
            )
        )
    else:
        open_conditions.append(topo.condition("gift"))
        plan.append(
            (
                "request_document",
                {
                    "party": "P-BORR",
                    "doc_type": "gift_letter",
                    "reason": "Please send a gift letter signed and dated by the donor.",
                },
            )
        )
    if set(topo.voes) & lies:
        open_conditions.append(topo.condition("voe"))
        plan.append(
            (
                "request_document",
                {
                    "party": "P-HR",
                    "doc_type": "voe",
                    "reason": "Please complete, sign and date a new written VOE.",
                },
            )
        )
    else:
        plan.append(
            (
                "clear_condition",
                {
                    "condition_id": topo.condition("voe"),
                    "note": "Written VOE matches HR.",
                    "citations": [page(v) for v in topo.voes],
                },
            )
        )
    gross = case["pay_stubs"][0]["gross"]
    account = [
        {
            "claim": f"Current gross pay per biweekly period is ${money(gross)}.",
            "citations": [page(topo.newest_stub)],
        },
        {
            "claim": f"Gift funds of ${money(case['gift']['amount'])} were deposited.",
            "citations": [page(gift), page(topo.deposit_statement or gift)],
        },
        {
            "claim": "Credit shows an undisclosed installment loan; LOX requested.",
            "citations": [{"service": "credit"}],
        },
    ]
    plan.append(
        (
            "submit",
            {
                "recommendation": "CONDITIONAL",
                "open_conditions": sorted(open_conditions),
                "account": account,
            },
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
