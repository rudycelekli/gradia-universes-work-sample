"""The LoanWorld side of a Harbor task: one episode behind a small HTTP API.

It runs in its own container (the ``world`` compose service), so the agent, which has
root in the ``main`` container, can never read case truth, counterpart contracts or the
oracle's labels. The agent reaches it only through ``lw`` (``harbor_client.py``).

Endpoints (JSON):

* ``GET  /start``  the start message of protocol ``gradia.loanworld.stdio.v0``: scenario
  id, act budget, tool manifest, current projection. Does not spend an act.
* ``POST /call``   ``{"tool", "args"}`` -> ``{"act", "response"}``. ``get_page`` responses
  carry the rendered page as ``image_png_base64``.
* ``POST /grade``  requires header ``X-LoanWorld-Grader-Token``. Grades the episode with
  the oracle and freezes the world: no call is accepted afterwards.

Nothing else is served. Requests are handled one at a time, so the episode is
deterministic in the order the agent acts.
"""

from __future__ import annotations

import argparse
import base64
import hmac
import json
import os
import sys
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from .adapter import _result, _start_message
from .oracle import grade_episode
from .schema import LoanScenario
from .tools import LoanWorldSession

TOKEN_HEADER = "X-LoanWorld-Grader-Token"
MAX_BODY = 1_000_000


class WorldState:
    """One episode. ``images`` maps (upload_id, page) to PNG bytes; may be empty."""

    def __init__(
        self,
        bundle: dict[str, Any],
        token: str,
        images: dict[tuple[str, int], bytes] | None = None,
    ) -> None:
        self.bundle = bundle
        self.token = token
        self.images = images or {}
        self.session = LoanWorldSession(
            LoanScenario.parse(deepcopy(bundle["scenario"])),
            bundle["max_acts"],
            bundle["counterparts"],
        )
        self.censor_reason: str | None = None
        self.graded: dict[str, Any] | None = None

    def start(self) -> dict[str, Any]:
        return _start_message(self.session)

    def call(self, tool: Any, args: Any) -> tuple[int, dict[str, Any]]:
        if self.graded is not None:
            return 409, {"error": "episode_already_graded"}
        if self.session.terminal is not None:
            return 409, {"error": "episode_already_submitted"}
        if self.censor_reason is not None:
            return 409, {"error": self.censor_reason}
        if not isinstance(tool, str) or not isinstance(args, dict):
            return 400, {"error": "body must be {\"tool\": str, \"args\": object}"}
        response = self.session.call(tool, args)
        if response.get("error") == "act_budget_exhausted":
            self.censor_reason = "act_budget_exhausted"
        if tool == "get_page" and isinstance(response, dict) and response.get("ok"):
            key = (str(args.get("upload_id")), int(args.get("page", 0) or 0))
            png = self.images.get(key)
            if png is not None:
                response = {**response, "image_png_base64": base64.b64encode(png).decode()}
        return 200, {"act": self.session.act, "response": response}

    def grade(self, token: str | None) -> tuple[int, dict[str, Any]]:
        if not token or not hmac.compare_digest(token, self.token):
            return 403, {"error": "forbidden"}
        if self.graded is None:
            if self.session.terminal is not None:
                result = _result(self.session, "terminal", None)
            else:
                reason = self.censor_reason or "agent_stopped_without_submit"
                result = _result(self.session, "censored", reason)
            bundle = {
                "scenario": self.bundle["scenario"],
                "counterparts": self.bundle["counterparts"],
            }
            grade = grade_episode(bundle, self.bundle["labels"], result, self.bundle["fork_id"])
            reward = 1.0 if result["outcome"] == "terminal" and grade["terminal_pass"] else 0.0
            self.graded = {
                "parent_id": self.bundle["parent_id"],
                "fork_id": self.bundle["fork_id"],
                "outcome": result["outcome"],
                "censor_reason": result["censor_reason"],
                "acts": result["acts"],
                "reward": reward,
                "terminal_pass": grade["terminal_pass"],
                "autonomous": grade["autonomous"],
                "recommendation": grade["recommendation"],
                "critical_failures": grade["critical_failures"],
                "failed_criteria": sorted(k for k, v in grade["criteria"].items() if not v),
                "diagnostics": grade["diagnostics"],
                "grade_sha256": grade["grade_sha256"],
                "proof_pack_sha256": result["proof_pack"]["pack_sha256"],
            }
        return 200, self.graded


def make_handler(state: WorldState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, status: int, body: dict[str, Any]) -> None:
            data = json.dumps(body, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> Any:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return None
            try:
                return json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return None

        def do_GET(self) -> None:
            if self.path == "/start":
                self._send(200, state.start())
            else:
                self._send(404, {"error": "not_found"})

        def do_POST(self) -> None:
            body = self._body()
            if self.path == "/call":
                if not isinstance(body, dict):
                    self._send(400, {"error": "invalid_json"})
                    return
                self._send(*state.call(body.get("tool"), body.get("args", {})))
            elif self.path == "/grade":
                self._send(*state.grade(self.headers.get(TOKEN_HEADER)))
            else:
                self._send(404, {"error": "not_found"})

    return Handler


def load_images(scenario: dict[str, Any], render_dir: Path) -> dict[tuple[str, int], bytes]:
    """Render every page once. Needs the ``loanworld-render`` extra (PyMuPDF, Pillow)."""
    from .live import PageImages

    return PageImages(scenario, render_dir).images


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve one LoanWorld episode for Harbor.")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--render-dir", type=Path, default=Path("/tmp/loanworld-render"))
    parser.add_argument("--no-images", action="store_true")
    args = parser.parse_args(argv)

    token = os.environ.get("LOANWORLD_GRADER_TOKEN", "")
    if len(token) < 32:
        print("LOANWORLD_GRADER_TOKEN must be set (>= 32 chars)", file=sys.stderr)
        return 2
    bundle = json.loads(args.bundle.read_text())
    images = {} if args.no_images else load_images(bundle["scenario"], args.render_dir)
    state = WorldState(bundle, token, images)
    server = HTTPServer((args.host, args.port), make_handler(state))
    episode = f"{bundle['parent_id']}/{bundle['fork_id']}"
    print(f"loanworld world serving {episode} on :{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
