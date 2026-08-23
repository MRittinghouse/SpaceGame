"""Argparse CLI for the play-harness crawler."""

from __future__ import annotations

import argparse
from typing import Optional, Sequence


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the crawler CLI.

    Returns:
        A configured ArgumentParser with all crawler flags registered.
    """
    parser = argparse.ArgumentParser(
        prog="python -m tools.crawler",
        description=(
            "Deterministic headless play-harness crawler for Aurelia. "
            "Boots a real Game, injects synthesized events, and records "
            "crashes, softlocks, invariant violations, and UI leaks."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        required=True,
        help="Integer seed for both stdlib random and numpy random.",
    )
    parser.add_argument(
        "--actions",
        type=int,
        required=True,
        help="Number of actions to execute in this session.",
    )
    parser.add_argument(
        "--checkpoint",
        choices=("early", "mid", "late"),
        default=None,
        help="Optional checkpoint save to load before crawling begins.",
    )
    parser.add_argument(
        "--debug-credits",
        type=int,
        default=0,
        help="Grant N credits to the player after checkpoint load (default: 0).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Write the full action trace to action_trace.log.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to write crawler_runs output to (defaults to CWD/crawler_runs).",
    )
    parser.add_argument(
        "--screenshot-dir",
        type=str,
        default=None,
        dest="screenshot_dir",
        help=(
            "Subdirectory under the run directory to write per-state screenshots. "
            "When absent or empty, screenshots are disabled."
        ),
    )
    baseline_group = parser.add_mutually_exclusive_group()
    baseline_group.add_argument(
        "--crash-baseline",
        type=str,
        default=None,
        dest="crash_baseline",
        help=(
            "Path to a crash-baseline JSON file. "
            "After the run, exit 1 if any crash signature is not in the baseline."
        ),
    )
    baseline_group.add_argument(
        "--write-crash-baseline",
        type=str,
        default=None,
        dest="write_crash_baseline",
        help=(
            "Write the current session's crash signatures to PATH (sorted; overwrites). "
            "Used for manual baseline regeneration. Mutually exclusive with --crash-baseline."
        ),
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments into a namespace.

    Args:
        argv: Optional list of argv strings; defaults to sys.argv when None.

    Returns:
        The parsed argparse Namespace.
    """
    return build_parser().parse_args(argv)
