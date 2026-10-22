"""Portable deterministic draws.

Python's ``random`` is stable in practice, but its exact algorithms are an
implementation detail. LoanWorld instead derives every draw from SHA-256 over
``seed|stream|counter`` so any language can regenerate a universe bit for bit.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")
_SPACE = 1 << 64


class Draws:
    def __init__(self, seed: str, stream: str) -> None:
        if not seed or not stream:
            raise ValueError("draws_seed_and_stream_required")
        self.seed = seed
        self.stream = stream
        self.counter = 0

    def _u64(self) -> int:
        material = f"{self.seed}|{self.stream}|{self.counter}".encode()
        self.counter += 1
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

    def below(self, n: int) -> int:
        """Uniform integer in [0, n) by rejection sampling."""
        if n <= 0:
            raise ValueError("draws_bound_must_be_positive")
        limit = _SPACE - (_SPACE % n)
        while True:
            value = self._u64()
            if value < limit:
                return value % n

    def between(self, low: int, high: int) -> int:
        """Uniform integer in [low, high], inclusive."""
        if high < low:
            raise ValueError("draws_range_invalid")
        return low + self.below(high - low + 1)

    def choice(self, items: Sequence[T]) -> T:
        if not items:
            raise ValueError("draws_choice_empty")
        return items[self.below(len(items))]

    def digits(self, count: int) -> str:
        return "".join(str(self.below(10)) for _ in range(count))


def derive_seed(master: str, split: str, index: int, generator_version: str) -> str:
    """HardLoan/LoanWorld seed derivation: sha256(master|split|index|version)[:16]."""
    material = f"{master}|{split}|{index}|{generator_version}".encode()
    return hashlib.sha256(material).hexdigest()[:16]
