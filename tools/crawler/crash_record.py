"""Crash record schema + deduplication helpers.

A crash is normalized by ``(exception_class_name, tuple((file_basename,
lineno, func_name) for frame in traceback))`` so that different messages
sharing the same underlying fault collapse into a single record. Message
text, memory addresses, and local-variable reprs are excluded.
"""

from __future__ import annotations

import hashlib
import os
import traceback
from dataclasses import dataclass, field
from types import TracebackType
from typing import Optional


@dataclass
class CrashRecord:
    """One deduplicated crash observation.

    Attributes:
        signature: 16-char hex prefix of the normalized-signature SHA-1.
        exception_class: Exception class name (or synthetic string for
            invariant/softlock oracles).
        first_seed: Seed of the first run that produced this crash.
        first_action_index: 0-based action index at first occurrence.
        occurrence_count: Total observations across all runs.
        action_trace: Copy of the crawler's action trace up to and including
            the crash-producing action.
        full_traceback: Human-readable traceback string for triage.
        state_at_crash: Value of ``state_manager.current_state`` at crash.
        oracle: Which oracle produced this record (exception/invariant/
            softlock/ui_leak).
    """

    signature: str
    exception_class: str
    first_seed: int
    first_action_index: int
    occurrence_count: int
    action_trace: list[tuple]
    full_traceback: str
    state_at_crash: str
    oracle: str = "exception"
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary.

        Returns:
            Dict with the same fields as this record.
        """
        return {
            "signature": self.signature,
            "exception_class": self.exception_class,
            "first_seed": self.first_seed,
            "first_action_index": self.first_action_index,
            "occurrence_count": self.occurrence_count,
            "action_trace": [list(a) for a in self.action_trace],
            "full_traceback": self.full_traceback,
            "state_at_crash": self.state_at_crash,
            "oracle": self.oracle,
            "extra": dict(self.extra),
        }


def _frame_tuples_from_tb(tb: Optional[TracebackType]) -> list[tuple[str, int, str]]:
    """Extract normalized frame tuples from a traceback object.

    Args:
        tb: A traceback object, or None.

    Returns:
        List of ``(file_basename, lineno, func_name)`` tuples. A missing
        lineno is coerced to 0 so the signature stays a stable tuple of
        concrete ints.
    """
    if tb is None:
        return []
    frames = traceback.extract_tb(tb)
    return [(os.path.basename(f.filename), f.lineno or 0, f.name) for f in frames]


def normalized_signature(exception_class: str, frame_tuples: list[tuple[str, int, str]]) -> str:
    """Build the 16-char hex signature from class name and frame tuples.

    Args:
        exception_class: Exception class name string.
        frame_tuples: List of ``(basename, lineno, funcname)`` tuples.

    Returns:
        16-char hex string (SHA-1 prefix).
    """
    joined = "|".join(f"{b}:{ln}:{fn}" for b, ln, fn in frame_tuples)
    payload = f"{exception_class}|{joined}".encode()
    return hashlib.sha1(payload).hexdigest()[:16]


def signature_from_exception(exc: BaseException) -> tuple[str, list[tuple[str, int, str]]]:
    """Build the frame-tuple list and signature payload from an exception.

    Args:
        exc: A caught exception.

    Returns:
        Tuple of ``(signature, frame_tuples)``.
    """
    frames = _frame_tuples_from_tb(exc.__traceback__)
    exc_name = type(exc).__name__
    return normalized_signature(exc_name, frames), frames
