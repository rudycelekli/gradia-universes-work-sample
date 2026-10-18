"""``gradia-universe loanworld-*`` commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..canonical import canonical_bytes, load_json, write_canonical
from .adapter import run_python_agent, tool_manifest
from .generator import build_gold_parent
from .policies import null_agent
from .schema import LoanScenario
from .tools import verify_proof_pack

PARENTS = Path("fixtures") / "loanworld" / "parents"


def command_build(args: argparse.Namespace) -> int:
    scenario = build_gold_parent(args.seed)
    LoanScenario.parse(scenario)
    path = args.root / PARENTS / f"{scenario['scenario_id']}.json"
    write_canonical(path, scenario)
    print(
        json.dumps(
            {
                "written": str(path.relative_to(args.root)),
                "scenario_id": scenario["scenario_id"],
            },
            sort_keys=True,
        )
    )
    return 0


def verify_parents(root: Path) -> list[dict[str, Any]]:
    """Regenerate every committed parent from its seed, then run the null control."""
    rows = []
    paths = sorted((root / PARENTS).glob("*.json"))
    if not paths:
        raise ValueError("loanworld_no_parents")
    for path in paths:
        committed = load_json(path)
        regenerated = build_gold_parent(
            committed["generator"]["seed"], committed["scenario_id"]
        )
        if canonical_bytes(regenerated) != canonical_bytes(committed):
            raise ValueError(f"loanworld_parent_not_reproducible:{path.name}")
        scenario = LoanScenario.parse(committed)
        result = run_python_agent(scenario, null_agent)
        verify_proof_pack(result["proof_pack"])
        if result["outcome"] != "terminal":
            raise ValueError(f"loanworld_null_control_censored:{result['censor_reason']}")
        rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "documents": len(scenario.ledgers["documents"]),
                "critical_values": sum(
                    len(doc["critical_values"])
                    for doc in scenario.ledgers["documents"].values()
                ),
                "null_control_pack_sha256": result["proof_pack"]["pack_sha256"],
            }
        )
    return rows


def command_verify(args: argparse.Namespace) -> int:
    print(json.dumps({"verified": verify_parents(args.root)}, sort_keys=True, indent=2))
    return 0


def command_render(args: argparse.Namespace) -> int:
    from .render import render_scenario  # optional extra: loanworld-render

    scenario = load_json(args.scenario)
    manifest = render_scenario(scenario, args.out)
    write_canonical(args.out / scenario["scenario_id"] / "render-manifest.json", manifest)
    print(
        json.dumps(
            {"manifest_sha256": manifest["manifest_sha256"], "files": len(manifest["files"])},
            sort_keys=True,
        )
    )
    return 0


def command_tools(args: argparse.Namespace) -> int:
    print(json.dumps(tool_manifest(), sort_keys=True, indent=2))
    return 0


def command_prereg(args: argparse.Namespace) -> int:
    from .prereg import build_design_preregistration

    value = build_design_preregistration(args.root, args.created_at)
    stamp = args.created_at[:10].replace("-", "")
    path = args.root / "preregistrations" / f"loanworld-v0-design-{stamp}.json"
    if path.exists():
        raise ValueError(f"prereg_already_frozen:{path.name}")
    write_canonical(path, value)
    print(json.dumps({"written": str(path.relative_to(args.root)), "digest": value["digest"]}))
    return 0


def command_prereg_verify(args: argparse.Namespace) -> int:
    from .prereg import verify_design_preregistration

    value = verify_design_preregistration(args.file)
    print(json.dumps({"verified": value["digest"], "git_sha": value["git_sha"]}))
    return 0


def register(sub: Any) -> None:
    build = sub.add_parser("loanworld-build", help="generate a seeded LoanWorld gold parent")
    build.add_argument("--seed", required=True)
    build.set_defaults(func=command_build)
    verify = sub.add_parser(
        "loanworld-verify", help="regenerate committed parents and run the null control"
    )
    verify.set_defaults(func=command_verify)
    render = sub.add_parser(
        "loanworld-render", help="render uploads to PDF/PNG (needs the loanworld-render extra)"
    )
    render.add_argument("--scenario", type=Path, required=True)
    render.add_argument("--out", type=Path, required=True)
    render.set_defaults(func=command_render)
    tools = sub.add_parser("loanworld-tools", help="print the agent tool manifest")
    tools.set_defaults(func=command_tools)
    prereg = sub.add_parser(
        "loanworld-prereg", help="freeze the v0 design preregistration (clean tree only)"
    )
    prereg.add_argument(
        "--created-at", required=True, help="RFC 3339 UTC, e.g. 2026-10-18T12:00:00Z"
    )
    prereg.set_defaults(func=command_prereg)
    prereg_verify = sub.add_parser("loanworld-prereg-verify", help="check a v0 preregistration")
    prereg_verify.add_argument("--file", type=Path, required=True)
    prereg_verify.set_defaults(func=command_prereg_verify)
