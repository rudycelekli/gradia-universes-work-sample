"""Canonical serialization and digest helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def normalize_numbers(value: Any) -> Any:
    """Keep canonical evidence portable across Python and JavaScript.

    JSON has one number type. Python nevertheless preserves ``1.0`` while a
    JavaScript parse/stringify cycle emits ``1``. Evidence that is signed in
    Python and verified in the Gradia Explorer must not change spelling merely
    because it crossed that runtime boundary.
    """

    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_numbers(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        normalize_numbers(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"object_required:{path}")
    if raw != canonical_bytes(value) + b"\n" and raw != canonical_bytes(value):
        raise ValueError(f"noncanonical_json:{path}")
    return value


def write_canonical(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")
