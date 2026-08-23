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
