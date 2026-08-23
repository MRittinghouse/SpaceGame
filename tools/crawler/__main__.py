"""CLI entry point for the play-harness crawler.

Invoke via ``python -m tools.crawler --seed S --actions N``.
"""

from __future__ import annotations

import os
import sys

# Headless SDL before pygame imports — mirrors tests/test_scenarios/_view_harness.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from tools.crawler.cli import parse_args
from tools.crawler.crawler import Crawler


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point.

    Args:
        argv: Optional argv override for testing.

    Returns:
        Process exit code (0 on clean completion).
    """
    args = parse_args(argv)
    crawler = Crawler(
        seed=args.seed,
        actions=args.actions,
        checkpoint=args.checkpoint,
        debug_credits=args.debug_credits,
        output_dir=args.output_dir,
        verbose=args.verbose,
    )
    crawler.run()
    crawler.write_reports()
    print(crawler.coverage_summary_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
