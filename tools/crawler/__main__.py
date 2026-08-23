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


def _write_github_step_summary(
    crawler: Crawler,
    novel_signatures: list,
) -> None:
    """Append a Markdown summary block to $GITHUB_STEP_SUMMARY if the env var is set.

    Args:
        crawler: Completed crawler session.
        novel_signatures: List of CrashRecords that are new vs. baseline.
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    total_states = len(crawler.coverage.states_reached)
    reached_count = sum(1 for v in crawler.coverage.states_reached.values() if v)
    total_transitions = len(crawler.coverage.transitions)
    total_crashes = len(crawler.crashes)
    novel_count = len(novel_signatures)

    lines = [
        f"## Crawler run (seed={crawler.config.seed}, actions={crawler.config.actions})",
        f"- **State coverage**: {reached_count}/{total_states} states reached",
        f"- **Transitions fired**: {total_transitions}",
        f"- **Crash signatures**: {total_crashes} total ({novel_count} new vs. baseline)",
    ]

    if novel_count > 0:
        lines.append("")
        lines.append("### New crash signatures")
        for record in novel_signatures:
            lines.append(
                f"- `{record.signature}` — {record.state_at_crash} / "
                f"{record.oracle} / {record.exception_class}"
            )

    lines.append("")

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point.

    Args:
        argv: Optional argv override for testing.

    Returns:
        Process exit code (0 on clean completion, 1 if novel crash signatures found).
    """
    args = parse_args(argv)

    crawler = Crawler(
        seed=args.seed,
        actions=args.actions,
        checkpoint=args.checkpoint,
        debug_credits=args.debug_credits,
        output_dir=args.output_dir,
        verbose=args.verbose,
        screenshot_dir=args.screenshot_dir,
    )
    crawler.run()
    crawler.write_reports()
    print(crawler.coverage_summary_text())

    # Baseline handling: write or compare.
    novel_signatures: list = []

    if args.write_crash_baseline:
        from tools.crawler.baseline import write_baseline

        write_baseline(
            args.write_crash_baseline,
            crawler.crashes,
            [(crawler.config.seed, crawler.config.checkpoint, crawler.config.actions)],
        )
        _write_github_step_summary(crawler, novel_signatures)
        return 0

    if args.crash_baseline:
        from tools.crawler.baseline import compare, load_baseline

        known = load_baseline(args.crash_baseline)
        novel_signatures = compare(crawler.crashes, known)

        _write_github_step_summary(crawler, novel_signatures)

        if novel_signatures:
            print(
                f"\nERROR: {len(novel_signatures)} novel crash signature(s) not in baseline:",
                file=sys.stderr,
            )
            for record in novel_signatures:
                print(
                    f"  {record.signature}  state={record.state_at_crash}"
                    f"  oracle={record.oracle}  exc={record.exception_class}",
                    file=sys.stderr,
                )
            return 1
        return 0

    _write_github_step_summary(crawler, novel_signatures)
    return 0


if __name__ == "__main__":
    sys.exit(main())
