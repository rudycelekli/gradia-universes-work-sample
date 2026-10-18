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
