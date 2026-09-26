"""Portable deterministic random generator shared with the Godot port.

xoshiro128** seeded from the md5 of a key string (SP2 spec Section 3). Every
operation is specified so that the GDScript twin (``core/rng/sim_rng.gd`` in
the aurelia repo) produces bit-identical results: 32-bit arithmetic masked
after every step, no transcendental functions, and fixed algorithms for every
derived draw.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import MutableSequence, Sequence
from typing import TypeVar

T = TypeVar("T")

_MASK32 = 0xFFFFFFFF
_TWO_32 = 1 << 32
_FALLBACK_S0 = 0x9E3779B9
_INV_2_24 = 1.0 / 16777216.0

_entropy_seed: int | None = None
_entropy_counter = 0


def seed_entropy(seed: int | None) -> None:
    """Make ``SimRng.from_entropy()`` reproducible, or restore OS entropy.

    The crawler and ``Game.seed_rngs`` call this so seeded runs replay
    exactly. ``None`` restores ``os.urandom`` seeding.

    Args:
        seed: Integer seed, or None for OS entropy.
    """
    global _entropy_seed, _entropy_counter
    _entropy_seed = seed
    _entropy_counter = 0


def build_key(*parts: str | int) -> str:
    """Join key parts with ``|``.

    Args:
        *parts: Key parts. Only ``str`` and ``int`` render identically in
            Python and GDScript, so ``bool``, ``float``, and ``None`` are rejected.

    Returns:
        The key string.

    Raises:
        TypeError: If a part is not ``str`` or ``int``, or is a ``bool``.
    """
    rendered: list[str] = []
    for part in parts:
        if isinstance(part, bool) or not isinstance(part, (str, int)):
            raise TypeError(
                f"SimRng key parts must be str or int, got {type(part).__name__}: {part!r}"
            )
        rendered.append(str(part))
    return "|".join(rendered)


def stable_seed(*parts: str | int) -> int:
    """Return a process-stable unsigned 32-bit seed for the given key parts.

    Replaces ``hash(...) & 0xFFFFFFFF``, which Python salts per process.

    Args:
        *parts: Key parts, as for ``build_key``.

    Returns:
        The first state word of ``SimRng.from_key(*parts)``.
    """
    return SimRng.from_key(*parts).state()[0]


def _rotl(x: int, k: int) -> int:
    return ((x << k) & _MASK32) | (x >> (32 - k))


class SimRng:
    """xoshiro128** generator with a ``random.Random``-compatible subset.

    Construct with ``from_key`` for deterministic streams, ``from_entropy``
    where a caller does not care, and ``deserialize`` to resume a saved stream.
    """

    __slots__ = ("_s0", "_s1", "_s2", "_s3")

    def __init__(self, s0: int, s1: int, s2: int, s3: int) -> None:
        words = [w & _MASK32 for w in (s0, s1, s2, s3)]
        if not any(words):
            words[0] = _FALLBACK_S0
        self._s0, self._s1, self._s2, self._s3 = words

    # === CONSTRUCTION ===

    @classmethod
    def from_key(cls, *parts: str | int) -> SimRng:
        """Seed from the md5 of ``build_key(*parts)`` encoded as UTF-8."""
        return cls.from_digest(hashlib.md5(build_key(*parts).encode("utf-8")).digest())

    @classmethod
    def from_digest(cls, digest: bytes) -> SimRng:
        """Seed from 16 bytes read as four little-endian unsigned 32-bit words."""
        if len(digest) != 16:
            raise ValueError(f"SimRng needs a 16-byte digest, got {len(digest)} bytes")
        return cls(*(int.from_bytes(digest[i : i + 4], "little") for i in (0, 4, 8, 12)))

    @classmethod
    def from_entropy(cls) -> SimRng:
        """A stream for callers that do not need determinism (see ``seed_entropy``)."""
        global _entropy_counter
        if _entropy_seed is None:
            return cls.from_digest(os.urandom(16))
        _entropy_counter += 1
        return cls.from_key("entropy", _entropy_seed, _entropy_counter)

    @classmethod
    def from_state(cls, s0: int, s1: int, s2: int, s3: int) -> SimRng:
        """Resume from four state words."""
        return cls(s0, s1, s2, s3)

    @classmethod
    def deserialize(cls, words: Sequence[str]) -> SimRng:
        """Resume from ``serialize()`` output (four decimal strings)."""
        if len(words) != 4:
            raise ValueError(f"SimRng state needs 4 words, got {len(words)}")
        return cls(*(int(w) for w in words))

    def state(self) -> tuple[int, int, int, int]:
        """The four state words."""
        return (self._s0, self._s1, self._s2, self._s3)

    def serialize(self) -> list[str]:
        """State as four decimal strings (Godot parses JSON numbers as float64)."""
        return [str(w) for w in self.state()]

    # === CORE ===

    def next_u32(self) -> int:
        """Advance the generator and return an unsigned 32-bit value."""
        s0, s1, s2, s3 = self._s0, self._s1, self._s2, self._s3
        result = (_rotl((s1 * 5) & _MASK32, 7) * 9) & _MASK32
        t = (s1 << 9) & _MASK32
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = _rotl(s3, 11)
        self._s0, self._s1, self._s2, self._s3 = s0, s1, s2, s3
        return result

    def randf(self) -> float:
        """A float in [0, 1) built from the top 24 bits, exact in both engines."""
        return (self.next_u32() >> 8) * _INV_2_24

    def randint(self, lo: int, hi: int) -> int:
        """An int in [lo, hi], unbiased by rejection sampling."""
        n = hi - lo + 1
        if n < 1 or n > _TWO_32:
            raise ValueError(f"randint span must be 1..2**32, got lo={lo} hi={hi}")
        limit = (_TWO_32 // n) * n
        while True:
            x = self.next_u32()
            if x < limit:
                return lo + x % n

    def uniform(self, a: float, b: float) -> float:
        """A float in [a, b)."""
        return a + (b - a) * self.randf()

    def chance(self, p: float) -> bool:
        """True with probability ``p``."""
        return self.randf() < p

    def choice(self, seq: Sequence[T]) -> T:
        """One element of a non-empty sequence."""
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        return seq[self.randint(0, len(seq) - 1)]

    def shuffle(self, items: MutableSequence[T]) -> None:
        """Fisher-Yates shuffle in place, walking from the end."""
        for i in range(len(items) - 1, 0, -1):
            j = self.randint(0, i)
            items[i], items[j] = items[j], items[i]

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        """``k`` distinct elements by partial Fisher-Yates on a copy."""
        pool = list(population)
        n = len(pool)
        if k < 0 or k > n:
            raise ValueError(f"sample size {k} outside 0..{n}")
        for i in range(k):
            j = self.randint(i, n - 1)
            pool[i], pool[j] = pool[j], pool[i]
        return pool[:k]

    def weighted_index(self, weights: Sequence[float]) -> int:
        """An index drawn in proportion to ``weights`` (cumulative, index order)."""
        if not weights:
            raise ValueError("weighted_index needs at least one weight")
        total = 0.0
        for w in weights:
            total += w
        if total <= 0.0:
            raise ValueError("weighted_index needs at least one positive weight")
        r = self.randf() * total
        cumulative = 0.0
        for i, w in enumerate(weights):
            cumulative += w
            if r < cumulative:
                return i
        for i in range(len(weights) - 1, -1, -1):
            if weights[i] > 0:
                return i
        raise ValueError("weighted_index needs at least one positive weight")

    # === random.Random-COMPATIBLE ALIASES ===

    def random(self) -> float:
        """Alias of ``randf`` so converted call sites keep their spelling."""
        return self.randf()

    def choices(
        self, population: Sequence[T], weights: Sequence[float] | None = None, k: int = 1
    ) -> list[T]:
        """``k`` draws with replacement, weighted like ``weighted_index``."""
        if weights is None:
            return [self.choice(population) for _ in range(k)]
        if len(weights) != len(population):
            raise ValueError("choices needs one weight per population member")
        return [population[self.weighted_index(weights)] for _ in range(k)]
