#!/usr/bin/env python3
"""``lw``: the agent's command-line door into a LoanWorld Harbor task.

Standard library only; copied verbatim into the agent's container as /usr/local/bin/lw.

    lw start                                   tools, act budget and the file as it is now
    lw tools                                   the tool list only
    lw <tool> ['<json args>']                  one act, e.g.
    lw get_page '{"upload_id": "U-001", "page": 1}'
    lw submit '{"recommendation": "CONDITIONAL", "open_conditions": [...], "account": [...]}'

Every call except ``start`` and ``tools`` spends one act. ``get_page`` saves the page
image to /app/pages/<upload>-p<page>.png and prints its path; open it to read the page.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

WORLD = os.environ.get("LOANWORLD_URL", "http://world:8080")
PAGES = Path(os.environ.get("LOANWORLD_PAGES", "/app/pages"))
READY_WAIT_S = 120.0


def _request(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        WORLD + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    deadline = time.monotonic() + READY_WAIT_S
    while True:
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read() or b"{}")
        except (urllib.error.URLError, ConnectionError):
            # The world may still be rendering pages at startup.
            if time.monotonic() > deadline:
                raise
            time.sleep(1.0)


def _save_page(args: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response")
    if not isinstance(response, dict) or "image_png_base64" not in response:
        return payload
    PAGES.mkdir(parents=True, exist_ok=True)
    path = PAGES / f"{args.get('upload_id')}-p{args.get('page')}.png"
    path.write_bytes(base64.b64decode(response.pop("image_png_base64")))
    response["image_path"] = str(path)
    return payload


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    command = argv[0]
    if command in {"start", "tools"}:
        status, payload = _request("GET", "/start")
        if command == "tools" and status == 200:
            payload = payload.get("tools", payload)
    else:
        raw = argv[1] if len(argv) > 1 else "{}"
        try:
            args = json.loads(raw)
        except json.JSONDecodeError as err:
            print(json.dumps({"error": f"arguments are not valid JSON: {err}"}))
            return 2
        if not isinstance(args, dict):
            print(json.dumps({"error": "arguments must be a JSON object"}))
            return 2
        status, payload = _request("POST", "/call", {"tool": command, "args": args})
        if status == 200 and command == "get_page":
            payload = _save_page(args, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
