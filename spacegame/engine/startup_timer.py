"""Lightweight startup phase profiler.

Records named phases with high-resolution timing and logs a summary.
Zero overhead after startup completes.
"""

import time

from spacegame.utils.logger import logger


class StartupTimer:
    """Records startup phase durations for profiling."""

    def __init__(self) -> None:
        self.phases: dict[str, float] = {}
        self._pending: dict[str, float] = {}

    def begin(self, phase: str) -> None:
        """Mark the start of a phase."""
        self._pending[phase] = time.perf_counter()

    def end(self, phase: str) -> None:
        """Mark the end of a phase and record its duration."""
        start = self._pending.pop(phase, None)
        if start is None:
            return
        self.phases[phase] = time.perf_counter() - start

    def total_time(self) -> float:
        """Sum of all recorded phase durations."""
        return sum(self.phases.values())

    def format_summary(self) -> str:
        """Format phase durations as a compact string."""
        parts = [f"{name}={dur * 1000:.0f}ms" for name, dur in self.phases.items()]
        parts.append(f"total={self.total_time() * 1000:.0f}ms")
        return "Startup: " + ", ".join(parts)

    def log_summary(self) -> None:
        """Log phase summary at INFO level."""
        logger.info(self.format_summary())
