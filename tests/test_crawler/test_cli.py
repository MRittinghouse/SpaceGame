"""CLI argparse tests for the play-harness crawler (QF-6)."""

from __future__ import annotations

import pytest

from tools.crawler.cli import build_parser, parse_args


class TestCLIParser:
    """Verify the argparse parser exposes all locked flags."""

    def test_crawler_cli_has_expected_flags(self) -> None:
        parser = build_parser()
        option_strings: set[str] = set()
        for action in parser._actions:
            option_strings.update(action.option_strings)
        for expected in ("--seed", "--actions", "--checkpoint", "--debug-credits", "--verbose"):
            assert expected in option_strings, f"missing CLI flag {expected}"

    def test_parse_args_minimum(self) -> None:
        ns = parse_args(["--seed", "42", "--actions", "5"])
        assert ns.seed == 42
        assert ns.actions == 5
        assert ns.checkpoint is None
        assert ns.debug_credits == 0
        assert ns.verbose is False

    def test_parse_args_checkpoint_choices(self) -> None:
        for name in ("early", "mid", "late"):
            ns = parse_args(["--seed", "1", "--actions", "1", "--checkpoint", name])
            assert ns.checkpoint == name

    def test_parse_args_bad_checkpoint_rejected(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--seed", "1", "--actions", "1", "--checkpoint", "middle"])


class TestCLINewFlagsQF7:
    """QF-7: verify new screenshot/baseline CLI flags are accepted."""

    def test_cli_accepts_screenshot_dir(self) -> None:
        ns = parse_args(["--seed", "42", "--actions", "10", "--screenshot-dir", "screenshots"])
        assert ns.screenshot_dir == "screenshots"

    def test_cli_screenshot_dir_defaults_to_none(self) -> None:
        ns = parse_args(["--seed", "42", "--actions", "10"])
        assert ns.screenshot_dir is None

    def test_cli_accepts_crash_baseline(self) -> None:
        ns = parse_args(
            [
                "--seed",
                "42",
                "--actions",
                "10",
                "--crash-baseline",
                "tools/crawler/crash_baseline.json",
            ]
        )
        assert ns.crash_baseline == "tools/crawler/crash_baseline.json"

    def test_cli_accepts_write_crash_baseline(self) -> None:
        ns = parse_args(
            [
                "--seed",
                "42",
                "--actions",
                "10",
                "--write-crash-baseline",
                "/tmp/baseline.json",
            ]
        )
        assert ns.write_crash_baseline == "/tmp/baseline.json"

    def test_cli_rejects_both_baseline_flags(self) -> None:
        """Passing --crash-baseline and --write-crash-baseline together should fail."""
        with pytest.raises(SystemExit):
            parse_args(
                [
                    "--seed",
                    "42",
                    "--actions",
                    "10",
                    "--crash-baseline",
                    "a.json",
                    "--write-crash-baseline",
                    "b.json",
                ]
            )

    def test_cli_crash_baseline_defaults_to_none(self) -> None:
        ns = parse_args(["--seed", "42", "--actions", "10"])
        assert ns.crash_baseline is None

    def test_cli_write_crash_baseline_defaults_to_none(self) -> None:
        ns = parse_args(["--seed", "42", "--actions", "10"])
        assert ns.write_crash_baseline is None
