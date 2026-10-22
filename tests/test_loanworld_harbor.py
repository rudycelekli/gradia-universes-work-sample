"""LoanWorld as Harbor tasks: the emitted tasks are solvable, unsolvable by doing nothing,
and the grader is reachable only with the verifier's token."""

from __future__ import annotations

import contextlib
import io
import json
import threading
import tomllib
from http.server import HTTPServer
from pathlib import Path
from typing import Any

import pytest

from gradia_universes.loanworld import harbor_client
from gradia_universes.loanworld.harbor import (
    DEV_PARENTS,
    SINGLE_FORKS,
    emit_dataset,
    emit_task,
)
from gradia_universes.loanworld.harbor_world import WorldState, make_handler
from gradia_universes.loanworld.policies import null_agent

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tasks(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    return emit_dataset(ROOT, tmp_path_factory.mktemp("harbor"))


def _state(task: Path) -> WorldState:
    bundle = json.loads((task / "environment" / "world" / "bundle.json").read_text())
    return WorldState(bundle, _token(task))


def _token(task: Path) -> str:
    config = tomllib.loads((task / "task.toml").read_text())
    return str(config["verifier"]["env"]["LOANWORLD_GRADER_TOKEN"])


def test_every_dev_parent_and_single_fork_is_emitted(tasks: list[Path]) -> None:
    assert len(tasks) == len(DEV_PARENTS) * len(SINGLE_FORKS) == 56
    for task in tasks:
        for rel in (
            "instruction.md",
            "task.toml",
            "environment/Dockerfile",
            "environment/lw",
            "environment/docker-compose.yaml",
            "environment/world/Dockerfile",
            "environment/world/bundle.json",
            "solution/solve.sh",
            "solution/plan.json",
            "tests/test.sh",
            "tests/grade.py",
        ):
            assert (task / rel).is_file(), f"{task.name}: missing {rel}"


def test_reference_solution_scores_one_on_every_task(tasks: list[Path]) -> None:
    failures = []
    for task in tasks:
        state = _state(task)
        for tool, args in json.loads((task / "solution" / "plan.json").read_text()):
            status, _ = state.call(tool, args)
            assert status == 200, f"{task.name}: {tool} refused"
        status, grade = state.grade(_token(task))
        assert status == 200
        if grade["reward"] != 1.0:
            failures.append((task.name, grade["failed_criteria"], grade["critical_failures"]))
    assert failures == []


def test_doing_nothing_scores_zero_on_every_task(tasks: list[Path]) -> None:
    for task in tasks:
        status, grade = _state(task).grade(_token(task))
        assert status == 200
        assert grade["reward"] == 0.0
        assert grade["censor_reason"] == "agent_stopped_without_submit"


def test_the_null_policy_scores_zero_on_every_task(tasks: list[Path]) -> None:
    """The repo's null baseline (look, escalate, submit) must not pass a Harbor task."""
    passed = []
    for task in tasks:
        state = _state(task)
        message: dict[str, Any] = state.start()
        while state.session.terminal is None:
            call = null_agent(message)
            _, payload = state.call(call["tool"], call.get("args", {}))
            message = {"type": "result", **payload}
        _, grade = state.grade(_token(task))
        if grade["reward"]:
            passed.append(task.name)
    assert passed == []


def test_grade_needs_the_token_and_freezes_the_world(tasks: list[Path]) -> None:
    task = tasks[0]
    state = _state(task)
    assert state.grade(None)[0] == 403
    assert state.grade("x" * 64)[0] == 403
    assert state.grade(_token(task))[0] == 200
    status, body = state.call("get_conditions", {})
    assert status == 409 and body["error"] == "episode_already_graded"


def test_held_out_parents_are_never_emitted(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        emit_task(ROOT, "loanworld-parent-heldout-001", "FK-00", tmp_path)


def test_instruction_never_names_the_fork(tasks: list[Path]) -> None:
    for task in tasks:
        text = (task / "instruction.md").read_text()
        assert "FK-" not in text and "family" not in text


def test_lw_over_http_with_page_images(tasks: list[Path], tmp_path: Path) -> None:
    """The real server and the real client, one task, rendered pages."""
    pytest.importorskip("fitz")
    from gradia_universes.loanworld.harbor_world import load_images

    task = next(t for t in tasks if t.name == "dev-001-fk-00")
    bundle = json.loads((task / "environment" / "world" / "bundle.json").read_text())
    state = WorldState(bundle, _token(task), load_images(bundle["scenario"], tmp_path / "r"))
    server = HTTPServer(("127.0.0.1", 0), make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    old_world, old_pages = harbor_client.WORLD, harbor_client.PAGES
    harbor_client.WORLD = f"http://127.0.0.1:{server.server_address[1]}"
    harbor_client.PAGES = tmp_path / "pages"
    try:

        def lw(*argv: str) -> tuple[int, Any]:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = harbor_client.main(list(argv))
            return code, json.loads(out.getvalue())

        code, start = lw("start")
        assert code == 0 and start["max_acts"] == 60 and start["tools"]
        code, page = lw("get_page", '{"upload_id": "U-001", "page": 1}')
        assert code == 0
        image = Path(page["response"]["image_path"])
        assert image.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert "image_png_base64" not in json.dumps(page)
        code, bad = lw("get_page", "not json")
        assert code == 2 and "error" in bad
    finally:
        harbor_client.WORLD, harbor_client.PAGES = old_world, old_pages
        server.shutdown()
