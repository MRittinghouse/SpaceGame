"""Unit tests for scripts/mypy_populations.py.

Tests use synthetic mypy output lines only -- the real mypy-baseline.txt
is NOT imported as a fixture because it drifts as the codebase evolves.

SH-3 removed the engine/game.py exclusion rule from mypy_populations.py.
All game.py crash-class (union-attr / attr-defined-None) errors now count
as tracked Population A, so A=0 means a fully clean codebase.
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest

# Add scripts/ to path so we can import the module directly.
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from mypy_populations import classify_line, count_populations, main

# ── classify_line helpers ──────────────────────────────────────────────────────


class TestClassifyLine:
    """Tests for the line classifier."""

    def test_union_attr_is_population_a(self) -> None:
        line = 'spacegame/models/foo.py:0: error: Item "None" of "Foo | None" has no attribute "bar"  [union-attr]'
        assert classify_line(line) == "A"

    def test_attr_defined_none_has_no_attribute_is_population_a(self) -> None:
        line = 'spacegame/models/bar.py:0: error: "None" has no attribute "baz"  [attr-defined]'
        assert classify_line(line) == "A"

    def test_game_py_union_attr_is_population_a_after_sh3(self) -> None:
        """SH-3 removed the game.py exclusion; union-attr is now tracked Population A."""
        line = 'spacegame/engine/game.py:0: error: Item "None" of "Player | None" has no attribute "credits"  [union-attr]'
        assert classify_line(line) == "A"

    def test_game_py_union_attr_backslash_is_population_a_after_sh3(self) -> None:
        """Same as above via Windows path separator."""
        line = r'spacegame\engine\game.py:0: error: Item "None" of "Player | None" has no attribute "credits"  [union-attr]'
        assert classify_line(line) == "A"

    def test_game_py_attr_defined_none_forward_slash_is_population_a_after_sh3(self) -> None:
        """SH-3 removed the game.py exclusion; attr-defined-None in game.py is now A.

        Previously this was 'excluded_a' per the pre-SH-3 exclusion rule.
        After SH-3 cleared all 39 crash-class errors in game.py, the exclusion
        rule was removed and all A-shaped errors count as tracked Population A.
        """
        line = 'spacegame/engine/game.py:0: error: "None" has no attribute "health"  [attr-defined]'
        assert classify_line(line) == "A"

    def test_game_py_attr_defined_none_backslash_is_population_a_after_sh3(self) -> None:
        """Same exclusion-removal via Windows path separator."""
        line = (
            r'spacegame\engine\game.py:0: error: "None" has no attribute "health"  [attr-defined]'
        )
        assert classify_line(line) == "A"

    def test_attr_defined_none_outside_game_py_stays_in_a(self) -> None:
        """attr-defined-None in a non-game.py path is Population A (unchanged)."""
        line = 'spacegame/views/trading_view.py:0: error: "None" has no attribute "foo"  [attr-defined]'
        assert classify_line(line) == "A"

    def test_attr_defined_object_has_no_attribute_is_population_b(self) -> None:
        line = 'spacegame/models/crew.py:0: error: "object" has no attribute "name"  [attr-defined]'
        assert classify_line(line) == "B"

    def test_name_defined_is_population_b(self) -> None:
        line = 'spacegame/views/foo.py:0: error: Name "BarType" is not defined  [name-defined]'
        assert classify_line(line) == "B"

    def test_return_value_is_population_c(self) -> None:
        line = 'spacegame/models/system.py:0: error: Incompatible return value type (got "str", expected "int")  [return-value]'
        assert classify_line(line) == "C"

    def test_no_untyped_def_is_population_c(self) -> None:
        line = "spacegame/views/base_view.py:0: error: Function is missing a return type annotation  [no-untyped-def]"
        assert classify_line(line) == "C"

    def test_arg_type_is_population_c(self) -> None:
        line = 'spacegame/engine/game.py:0: error: Argument 1 to "foo" has incompatible type "str"; expected "int"  [arg-type]'
        assert classify_line(line) == "C"

    def test_note_severity_returns_none(self) -> None:
        """Note-severity lines are not errors and must be completely ignored."""
        line = "spacegame/engine/transitions.py:0: note: By default the bodies of untyped functions are not checked  [annotation-unchecked]"
        assert classify_line(line) is None

    def test_plain_note_line_returns_none(self) -> None:
        line = 'spacegame/engine/transitions.py:0: note: Use "-> None" if function does not return a value'
        assert classify_line(line) is None

    def test_mypy_summary_line_returns_none(self) -> None:
        line = "Found 768 errors in 64 files (checked 201 source files)"
        assert classify_line(line) is None

    def test_blank_line_returns_none(self) -> None:
        assert classify_line("") is None

    def test_union_attr_outside_game_py_is_population_a(self) -> None:
        """union-attr in a file that is NOT engine/game.py is tracked Population A."""
        line = 'spacegame/views/trading_view.py:0: error: Item "None" of "Player | None" has no attribute "ship"  [union-attr]'
        assert classify_line(line) == "A"


# ── count_populations ──────────────────────────────────────────────────────────


class TestCountPopulations:
    """Tests for the aggregation function.

    count_populations returns (A, B, C, TOTAL) where TOTAL = A + B + C.
    After SH-3 there is no excluded_a bucket.
    """

    def test_empty_input(self) -> None:
        a, b, c, total = count_populations([])
        assert (a, b, c, total) == (0, 0, 0, 0)

    def test_single_population_a(self) -> None:
        lines = [
            'spacegame/models/foo.py:0: error: Item "None" of "Foo | None" has no attribute "bar"  [union-attr]',
        ]
        a, b, c, total = count_populations(lines)
        assert (a, b, c, total) == (1, 0, 0, 1)

    def test_single_population_b(self) -> None:
        lines = [
            'spacegame/views/foo.py:0: error: Name "X" is not defined  [name-defined]',
        ]
        a, b, c, total = count_populations(lines)
        assert (a, b, c, total) == (0, 1, 0, 1)

    def test_single_population_c(self) -> None:
        lines = [
            'spacegame/models/system.py:0: error: Incompatible return value type (got "Station | None", expected "Station")  [return-value]',
        ]
        a, b, c, total = count_populations(lines)
        assert (a, b, c, total) == (0, 0, 1, 1)

    def test_note_lines_excluded_from_all_populations_and_total(self) -> None:
        """Note-severity lines must not appear in any bucket or TOTAL."""
        lines = [
            "Found 3 errors in 2 files (checked 10 source files)",
            'spacegame/engine/transitions.py:0: note: Use "-> None" if function does not return a value',
            "",
        ]
        a, b, c, total = count_populations(lines)
        assert (a, b, c, total) == (0, 0, 0, 0)

    def test_game_py_union_attr_is_tracked_a_after_sh3(self) -> None:
        """After SH-3, game.py union-attr counts as tracked Population A."""
        lines = [
            'spacegame/engine/game.py:0: error: Item "None" of "Player | None" has no attribute "credits"  [union-attr]',
            'spacegame/models/ship.py:0: error: Item "None" of "Foo | None" has no attribute "cargo"  [union-attr]',
        ]
        a, _b, c, total = count_populations(lines)
        assert a == 2  # both lines count as A (no exclusion)
        assert c == 0
        assert total == 2

    def test_game_py_union_attr_is_a_not_c_after_sh3(self) -> None:
        """game.py union-attr must not inflate the C count (unchanged from before SH-3)."""
        lines = [
            'spacegame/engine/game.py:0: error: Item "None" of "Player | None" has no attribute "credits"  [union-attr]',
        ]
        a, _b, c, total = count_populations(lines)
        assert a == 1
        assert c == 0
        assert total == 1

    def test_mixed_synthetic_fixture(self) -> None:
        """Fixture with known A/B/C/TOTAL distribution.

        After SH-3 there is no excluded_a bucket; all A-shaped errors
        (including those in engine/game.py) count as tracked Population A.

        Errors:
          - 2 union-attr (non-game.py) -> A
          - 1 None-has-no-attr attr-defined (non-game.py) -> A
          - 1 None-has-no-attr attr-defined (game.py) -> A (was excluded_a pre-SH-3)
          - 1 union-attr (game.py) -> A (was excluded_a pre-SH-3)
          - 1 object-has-no-attr attr-defined -> B
          - 2 name-defined -> B
          - 4 C-type errors -> C
          - 1 note line -> ignored
          - 1 summary line -> ignored
          - 1 blank -> ignored

        Expected: A=5, B=3, C=4, TOTAL=12
        """
        lines = [
            # Population A (3 non-game.py)
            'spacegame/models/foo.py:0: error: Item "None" of "Foo | None" has no attribute "x"  [union-attr]',
            'spacegame/models/foo.py:0: error: Item "None" of "Bar | None" has no attribute "y"  [union-attr]',
            'spacegame/models/bar.py:0: error: "None" has no attribute "z"  [attr-defined]',
            # Population A (2 game.py — now tracked, not excluded)
            'spacegame/engine/game.py:0: error: "None" has no attribute "health"  [attr-defined]',
            'spacegame/engine/game.py:0: error: Item "None" of "Player | None" has no attribute "credits"  [union-attr]',
            # Population B (3)
            'spacegame/models/crew.py:0: error: "object" has no attribute "name"  [attr-defined]',
            'spacegame/views/foo.py:0: error: Name "BazType" is not defined  [name-defined]',
            'spacegame/views/bar.py:0: error: Name "QuxType" is not defined  [name-defined]',
            # Population C (4)
            'spacegame/models/system.py:0: error: Incompatible return value type (got "Station | None", expected "Station")  [return-value]',
            "spacegame/views/base_view.py:0: error: Function is missing a return type annotation  [no-untyped-def]",
            'spacegame/engine/transitions.py:0: error: Argument 1 to "foo" has incompatible type "str"; expected "int"  [arg-type]',
            'spacegame/models/easing.py:0: error: Returning Any from function declared to return "float"  [no-any-return]',
            # Note -> ignored
            "spacegame/engine/transitions.py:0: note: By default the bodies of untyped functions are not checked  [annotation-unchecked]",
            # Summary / blank -> ignored
            "Found 12 errors in 6 files (checked 50 source files)",
            "",
        ]
        a, b, c, total = count_populations(lines)
        assert a == 5  # 3 non-game.py + 2 game.py (no exclusion post-SH-3)
        assert b == 3
        assert c == 4
        assert total == 12  # 5 A + 3 B + 4 C


# ── main / --stdin mode ────────────────────────────────────────────────────────


class TestMainStdin:
    """Test the --stdin flag without running mypy."""

    def test_stdin_mode_reads_from_stdin(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        synthetic = (
            'spacegame/models/foo.py:0: error: Item "None" of "Foo | None" has no attribute "x"  [union-attr]\n'
            'spacegame/views/bar.py:0: error: Name "BazType" is not defined  [name-defined]\n'
            'spacegame/models/system.py:0: error: Incompatible return value type (got "str", expected "int")  [return-value]\n'
        )
        monkeypatch.setattr("sys.stdin", StringIO(synthetic))
        main(["--stdin"])
        out = capsys.readouterr().out
        assert "A=1" in out
        assert "B=1" in out
        assert "C=1" in out
        assert "TOTAL=3" in out

    def test_empty_stdin_yields_zeros(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.stdin", StringIO(""))
        main(["--stdin"])
        out = capsys.readouterr().out
        assert "A=0" in out
        assert "B=0" in out
        assert "C=0" in out
        assert "TOTAL=0" in out

    def test_game_py_union_attr_in_a_after_sh3(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """After SH-3, game.py union-attr is tracked A, reflected in both A and TOTAL."""
        synthetic = (
            'spacegame/engine/game.py:0: error: Item "None" of "Player | None" has no attribute "credits"  [union-attr]\n'
            'spacegame/models/foo.py:0: error: Item "None" of "Foo | None" has no attribute "x"  [union-attr]\n'
        )
        monkeypatch.setattr("sys.stdin", StringIO(synthetic))
        main(["--stdin"])
        out = capsys.readouterr().out
        assert "A=2" in out  # both lines count as A (no exclusion)
        assert "TOTAL=2" in out
