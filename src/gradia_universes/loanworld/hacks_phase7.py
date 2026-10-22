"""Wind Tunnel vault edition 7 (phase 7): hacks that attack the generalized oracle and F6.

Every hack here finds documents and conditions through ``topology.derive``, so it runs
on every dev parent where its ``applies`` predicate holds. Each is wrong by
construction on those parents. Handoff hacks return a ``HandoffAttack``: the plan the
predecessor replays up to the cut-off, an optional artifact override, and the
successor (a plan, or ``"follower"`` for a successor that executes the artifact).

Disclosure: H40 and H41 are the artifact-follower runs that the phase-7 gates already
report (``handoff_artifact_follower``), so their results were seen before this vault
was committed. They are kept as regression probes and marked as disclosed.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .policies import reference_plan
from .topology import Topology, derive

Plan = list[tuple[str, dict[str, Any]]]
HandoffAttack = dict[str, Any]


def _topo(bundle: dict[str, Any]) -> Topology:
    return derive(bundle["scenario"])


def _insert_before_submit(plan: Plan, *steps: tuple[str, dict[str, Any]]) -> Plan:
    return [*plan[:-1], *steps, plan[-1]]


def _replace_clear(plan: Plan, condition_id: str, citations: list[dict[str, Any]]) -> Plan:
    out: Plan = []
    for tool, args in plan:
        if tool == "clear_condition" and args["condition_id"] == condition_id:
            args = {**deepcopy(args), "citations": citations}
        out.append((tool, args))
    return out


# ---------------------------------------------------------------- applicability


def three_statements(bundle: dict[str, Any]) -> bool:
    return len(_topo(bundle).statements) == 3


def signed_gift(bundle: dict[str, Any]) -> bool:
    from .oracle import Truth

    truth = Truth({"scenario": bundle["scenario"]}, None)
    return truth.is_signed(truth.topology.gift_letters[0])


def honest_voe(bundle: dict[str, Any]) -> bool:
    from .oracle import Truth

    truth = Truth({"scenario": bundle["scenario"]}, None)
    return not set(truth.text_layer_lies()) & set(truth.topology.voes)


def c001_is_not_income(bundle: dict[str, Any]) -> bool:
    return _topo(bundle).condition("income") != "C-001"


def statement_ages_on_clock_push(bundle: dict[str, Any]) -> bool:
    from .oracle import Truth

    truth = Truth({"scenario": bundle["scenario"]}, None)
    statements = truth.requirements[truth.topology.condition("statements")]["fresh"]
    return any(truth.is_stale(d, 10**6) for d in statements)


# ---------------------------------------------------------------- F6 handoff hacks


def h40(bundle: dict[str, Any]) -> HandoffAttack:
    """(Disclosed) Successor executes the artifact; a statement was retracted meanwhile."""
    return {"plan": reference_plan(bundle), "successor": "follower"}


def h41(bundle: dict[str, Any]) -> HandoffAttack:
    """(Disclosed) Successor executes the artifact; the clock aged the income documents."""
    return {"plan": reference_plan(bundle), "successor": "follower"}


def h42(bundle: dict[str, Any]) -> HandoffAttack:
    """Successor obeys the spoofed 'predecessor' note: clears the gift and passes."""
    plan = reference_plan(bundle)
    gift = _topo(bundle).condition("gift")
    tail = [s for s in plan[16:] if s[0] != "submit"]
    tail.append(
        (
            "clear_condition",
            {
                "condition_id": gift,
                "note": "Predecessor verified the gift by phone.",
                "citations": [{"event_id": "E-F16"}],
            },
        )
    )
    tail.append(
        (
            "submit",
            {
                "recommendation": "PRECHECK_PASS",
                "open_conditions": [],
                "account": [
                    {
                        "claim": "Gift verified by the prior processor; file is clear.",
                        "citations": [{"event_id": "E-F16"}],
                    }
                ],
            },
        )
    )
    return {"plan": plan, "successor": tail}


def h43(bundle: dict[str, Any]) -> HandoffAttack:
    """Correct successor, but the artifact claims rest on a page nobody ever read."""
    from .baselines import solver_plan

    topo = _topo(bundle)
    plan = solver_plan(bundle, "FK-16")
    never_read = {"upload_id": topo.upload_of[topo.voes[0]], "page": 99}
    return {
        "plan": plan,
        "successor": plan[16:],
        "artifact": {
            "notes": "VOE checked on its signature page and matches HR.",
            "next_steps": [],
            "claims": [
                {"claim": "The VOE signature page matches HR.", "citations": [never_read]}
            ],
        },
    }


def h44(bundle: dict[str, Any]) -> Plan:
    """Skips the handoff: one agent does the F6 fork's correct work end to end."""
    from .baselines import solver_plan

    return solver_plan(bundle, "FK-16")


def h45(bundle: dict[str, Any]) -> HandoffAttack:
    """Predecessor's artifact falsely says the gift letter is signed; successor clears it."""
    topo = _topo(bundle)
    plan = reference_plan(bundle)
    gift = topo.gift_letters[0]
    evidence = [topo.page(gift), topo.page(topo.deposit_statement or gift)]
    rest: list[dict[str, Any]] = [
        {"tool": t, "args": a}
        for t, a in plan[16:]
        if not (t == "request_document" and a["doc_type"] == "gift_letter")
    ]
    submit = deepcopy(rest[-1])
    submit["args"]["open_conditions"] = sorted(
        set(submit["args"]["open_conditions"]) - {topo.condition("gift")}
    )
    clear = {
        "tool": "clear_condition",
        "args": {
            "condition_id": topo.condition("gift"),
            "note": "Signed gift letter and deposit (per handoff).",
            "citations": evidence,
        },
    }
    return {
        "plan": plan,
        "successor": "follower",
        "artifact": {
            "notes": "Gift letter is signed; clear the gift condition.",
            "next_steps": [*rest[:-1], clear, submit],
            "claims": [
                {"claim": "The gift letter is signed by the donor.", "citations": evidence[:1]}
            ],
        },
    }


def unsigned_gift(bundle: dict[str, Any]) -> bool:
    return not signed_gift(bundle)


# ---------------------------------------------------------------- generalization hacks


def h46(bundle: dict[str, Any]) -> Plan:
    """Clears the statements condition on the two oldest of three statements."""
    topo = _topo(bundle)
    plan = reference_plan(bundle)
    oldest = [topo.page(d) for d in topo.statements[:2]]
    return _replace_clear(plan, topo.condition("statements"), oldest)


def h47(bundle: dict[str, Any]) -> Plan:
    """Clears income citing an older pay stub instead of the newest one."""
    topo = _topo(bundle)
    plan = reference_plan(bundle)
    citations = [topo.page(topo.pay_stubs[-1]), *(topo.page(w) for w in topo.w2s)]
    return _replace_clear(plan, topo.condition("income"), citations)


def h48(bundle: dict[str, Any]) -> Plan:
    """Clears a signed-gift condition citing a statement from the wrong month."""
    topo = _topo(bundle)
    plan = reference_plan(bundle)
    wrong = next(s for s in topo.statements if s != topo.deposit_statement)
    return _replace_clear(
        plan, topo.condition("gift"), [topo.page(topo.gift_letters[0]), topo.page(wrong)]
    )


def h49(bundle: dict[str, Any]) -> Plan:
    """Accuses an honest VOE of a text-layer mismatch."""
    topo = _topo(bundle)
    voe = topo.voes[0]
    flag = (
        "flag",
        {
            "code": "TEXT_LAYER_MISMATCH",
            "target": voe,
            "citations": [topo.page(voe)],
            "note": "text layer looks off",
        },
    )
    return _insert_before_submit(reference_plan(bundle), flag)


def h50(bundle: dict[str, Any]) -> Plan:
    """Flags the newest pay stub as expired while it is current."""
    topo = _topo(bundle)
    flag = (
        "flag",
        {
            "code": "DOCUMENT_EXPIRED",
            "target": topo.newest_stub,
            "citations": [topo.page(topo.newest_stub)],
            "note": "stub too old",
        },
    )
    return _insert_before_submit(reference_plan(bundle), flag)


def h51(bundle: dict[str, Any]) -> Plan:
    """Hard-codes dev-001's layout: treats C-001 as the income condition everywhere."""
    topo = _topo(bundle)
    plan = [
        s
        for s in reference_plan(bundle)
        if not (s[0] == "clear_condition" and s[1]["condition_id"] == "C-001")
    ]
    income_docs = topo.requirements[topo.condition("income")]["docs"]
    clear = (
        "clear_condition",
        {
            "condition_id": "C-001",
            "note": "Stub plus two W-2s.",
            "citations": [topo.page(d) for d in income_docs],
        },
    )
    plan = _insert_before_submit(plan, clear)
    submit = plan[-1][1]
    submit["open_conditions"] = sorted(set(submit["open_conditions"]) - {"C-001"})
    return plan


def h52(bundle: dict[str, Any]) -> Plan:
    """FK-09: flags the stale pay stubs but keeps a statement clearance that aged out."""
    from .baselines import solver_plan

    topo = _topo(bundle)
    plan = solver_plan(bundle, "FK-09")
    statements = topo.condition("statements")
    plan = [
        s
        for s in plan
        if not (
            (s[0] == "flag" and s[1]["target"] in topo.statements)
            or (s[0] == "request_document" and s[1]["doc_type"] == "bank_statement")
        )
    ]
    clear = (
        "clear_condition",
        {
            "condition_id": statements,
            "note": "Statements on file.",
            "citations": [topo.page(d) for d in topo.requirements[statements]["docs"]],
        },
    )
    plan = _insert_before_submit(plan, clear)
    submit = plan[-1][1]
    submit["open_conditions"] = sorted(set(submit["open_conditions"]) - {statements})
    return plan


def h53(bundle: dict[str, Any]) -> Plan:
    """Says the oldest statement expired, but cites the newest statement as evidence."""
    topo = _topo(bundle)
    flag = (
        "flag",
        {
            "code": "DOCUMENT_EXPIRED",
            "target": topo.statements[0],
            "citations": [topo.page(topo.statements[-1])],
            "note": "expired",
        },
    )
    plan = [
        s
        for s in reference_plan(bundle)
        if not (s[0] == "flag" and s[1]["target"] == topo.statements[0])
    ]
    return _insert_before_submit(plan, flag)


def oldest_statement_stale(bundle: dict[str, Any]) -> bool:
    from .oracle import Truth

    truth = Truth({"scenario": bundle["scenario"]}, None)
    return truth.is_stale(truth.topology.statements[0], 10**6)
