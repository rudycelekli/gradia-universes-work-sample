"""Roles derived from a scenario, so nothing downstream hard-wires document or condition IDs.

Phase 7 generalizes LoanWorld from one parent to many. A parent's document IDs
(``D-001``...), upload IDs and condition IDs are assigned by the generator and can
differ from parent to parent. Everything that needs to know "which document is the
newest pay stub" or "which condition asks for bank statements" asks this module,
which derives the answer from the scenario's own content:

* documents are grouped by ``doc_type`` and ordered by the dates printed on them
  (a stub's pay date, a statement's period end, a W-2's tax year);
* the gift-deposit statement is the statement whose month holds the gift deposit;
* each condition's evidence requirement is derived from its ``satisfied_by``
  types and its category, never from its ID.

A condition whose requirement cannot be derived fails closed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

_ORDINALS = ("first", "second", "third", "fourth", "fifth")


def ordinal(position: int) -> str:
    """1 -> 'first'. Used for agent-visible text that names a document by position."""
    return _ORDINALS[position - 1]


def _value(document: dict[str, Any], suffix: str) -> Any:
    for value in document["critical_values"]:
        if value["field_id"].endswith(suffix):
            return value["norm"]
    raise ValueError(f"topology_value_missing:{document['doc_id']}:{suffix}")


@dataclass(frozen=True)
class Topology:
    pay_stubs: tuple[str, ...]  # newest first
    w2s: tuple[str, ...]  # newest tax year first
    statements: tuple[str, ...]  # oldest first
    gift_letters: tuple[str, ...]
    voes: tuple[str, ...]
    purchase: tuple[str, ...]
    deposit_statement: str | None
    anchors: dict[str, tuple[date, str]]  # doc -> (age anchor, recency key)
    requirements: dict[str, dict[str, Any]]  # condition -> evidence requirement
    roles: dict[str, str]  # role -> condition id
    upload_of: dict[str, str] = field(default_factory=dict)
    first_page: dict[str, int] = field(default_factory=dict)

    # ---- convenience

    @property
    def newest_stub(self) -> str:
        return self.pay_stubs[0]

    @property
    def last_statement(self) -> str:
        return self.statements[-1]

    @property
    def income_docs(self) -> set[str]:
        return {*self.pay_stubs, *self.w2s, *self.voes}

    def page(self, doc_id: str) -> dict[str, Any]:
        return {"upload_id": self.upload_of[doc_id], "page": self.first_page[doc_id]}

    def condition(self, role: str) -> str:
        return self.roles[role]

    def ptf_conditions(self) -> list[str]:
        return sorted(c for c, r in self.requirements.items() if r.get("premature_at_precheck"))


def _requirement(
    condition: dict[str, Any],
    stubs: list[str],
    w2s: list[str],
    statements: list[str],
    gifts: list[str],
    voes: list[str],
    deposit: str | None,
) -> tuple[str, dict[str, Any]]:
    kinds = set(condition["satisfied_by"])
    if condition["category"] == "PTF":
        return "funding", {"premature_at_precheck": True}
    if kinds == {"pay_stub", "w2"}:
        return "income", {"docs": [stubs[0], *w2s], "fresh": [stubs[0]]}
    if kinds == {"bank_statement"}:
        recent = statements[-2:]
        return "statements", {"docs": recent, "fresh": recent}
    if kinds == {"gift_letter", "bank_statement"} and deposit is not None:
        return "gift", {"docs": [*gifts, deposit], "fresh": [deposit], "signed": list(gifts)}
    if kinds == {"voe"}:
        return "voe", {"docs": list(voes), "fresh": []}
    if kinds == {"appraisal"}:
        return "appraisal", {"service": "appraisal"}
    if kinds == {"title"}:
        return "title", {"service": "title"}
    raise ValueError(f"topology_requirement_underivable:{sorted(kinds)}")


def derive(scenario: dict[str, Any]) -> Topology:
    ledgers = scenario["ledgers"]
    documents: dict[str, Any] = ledgers["documents"]
    by_type: dict[str, list[str]] = {}
    for doc_id in sorted(documents):
        by_type.setdefault(documents[doc_id]["doc_type"], []).append(doc_id)
    stubs = sorted(
        by_type.get("pay_stub", []),
        key=lambda d: (_value(documents[d], ".pay_date"), d),
        reverse=True,
    )
    w2s = sorted(
        by_type.get("w2", []),
        key=lambda d: (int(re.findall(r"\d{4}", documents[d]["title"])[-1]), d),
        reverse=True,
    )
    statements = sorted(
        by_type.get("bank_statement", []),
        key=lambda d: (_value(documents[d], ".statement_period")[1], d),
    )
    month = ledgers["case"].get("gift", {}).get("deposit_txn_month")
    deposit = next(
        (s for s in statements if _value(documents[s], ".statement_period")[1][:7] == month),
        None,
    )
    anchors: dict[str, tuple[date, str]] = {}
    for doc_id in stubs:
        anchors[doc_id] = (
            date.fromisoformat(_value(documents[doc_id], ".pay_date")),
            "pay_stub",
        )
    for doc_id in statements:
        end = _value(documents[doc_id], ".statement_period")[1]
        anchors[doc_id] = (date.fromisoformat(end), "bank_statement")
    gifts = by_type.get("gift_letter", [])
    voes = by_type.get("voe", [])
    requirements: dict[str, dict[str, Any]] = {}
    roles: dict[str, str] = {}
    for condition_id, condition in sorted(ledgers["conditions"].items()):
        role, requirement = _requirement(
            condition, stubs, w2s, statements, gifts, voes, deposit
        )
        requirements[condition_id] = requirement
        if role in roles:
            raise ValueError(f"topology_role_duplicated:{role}")
        roles[role] = condition_id
    return Topology(
        pay_stubs=tuple(stubs),
        w2s=tuple(w2s),
        statements=tuple(statements),
        gift_letters=tuple(gifts),
        voes=tuple(voes),
        purchase=tuple(by_type.get("purchase_agreement", [])),
        deposit_statement=deposit,
        anchors=anchors,
        requirements=requirements,
        roles=roles,
        upload_of={d: documents[d]["upload_id"] for d in documents},
        first_page={d: documents[d]["pages"][0] for d in documents},
    )


def clock_event_index(scenario: dict[str, Any]) -> int:
    return next(i for i, e in enumerate(scenario["events"]) if e["target"] == "clock")


def los_field_index(scenario: dict[str, Any], key: str) -> int:
    fields = scenario["ledgers"]["los"]["fields"]
    return next(i for i, f in enumerate(fields) if f["key"] == key)
