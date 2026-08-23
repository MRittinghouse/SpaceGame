"""Play-harness crawler (QF-6).

Deterministic headless crawler that drives the real ``Game`` object through
real event dispatch to surface crashes, invariant violations, softlocks, and
pygame_gui element leaks. Emits a JSON coverage report and dedup'd crash
records for the CI gate (QF-7) and reachability-prioritized burndown (QF-8).
"""

from tools.crawler.crawler import Crawler
from tools.crawler.crash_record import CrashRecord, normalized_signature
from tools.crawler.coverage import CoverageTracker

__all__ = [
    "CoverageTracker",
    "Crawler",
    "CrashRecord",
    "normalized_signature",
]
