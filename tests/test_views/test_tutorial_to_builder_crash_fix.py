"""Regression tests for the tutorial -> ship builder crash + UI overflow.

Bug: launching the ship builder after a tutorial purchase crashed with
KeyError 'slot_def_id' because TUTORIAL_PARTS dicts use 'part_id'. The
flag name was also wrong ('tutorial_bought_X' vs the actual
'tutorial_bought_part_X' set by the shop), and the filter relationship
was conceptually wrong (filtering slot_defs by part_id which never
matched any slot_def key).

UI bug: long part names ("Salvaged Pulse Emitter") spilled past the
card border in tutorial_shop_view.
"""

from __future__ import annotations

import pygame

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH


def _init_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _make_player(credits: int = 5000):
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship, ShipType

    ship_type = ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="x",
        cargo_capacity=10,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=2,
        special_abilities=[],
        availability="all",
    )
    return Player(
        name="T",
        credits=credits,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )


# ---------------------------------------------------------------------------
# CRASH FIX: tutorial -> ship builder doesn't crash
# ---------------------------------------------------------------------------


class TestTutorialToBuilderNoCrash:
    """Reproduces the exact sequence that crashed:
    1. Purchase a tutorial part (sets dialogue_flag)
    2. Enter ship builder in tutorial mode
    3. Render slot palette (calls _get_slot_definitions_grouped)
    """

    def test_get_slot_definitions_grouped_does_not_crash_in_tutorial(
        self,
    ) -> None:
        """Direct test of the function that crashed."""
        from spacegame.data_loader import get_data_loader
        from spacegame.views.ship_builder_view import ShipBuilderView

        _init_pygame()
        dl = get_data_loader()
        dl.load_all()
        player = _make_player()
        # Simulate tutorial purchase: set the flag the shop sets
        player.dialogue_flags["tutorial_bought_part_scrapyard_hold"] = True

        # Build the view in tutorial mode
        view = ShipBuilderView.__new__(ShipBuilderView)
        view.player = player
        view.data_loader = dl
        view._tutorial_mode = True

        # The function under test — previously crashed with KeyError
        groups = view._get_slot_definitions_grouped()
        # Returns a list (may be empty if no parts purchased, but must
        # not raise). Each entry is (slot_type, [SlotDefinition, ...]).
        assert isinstance(groups, list)
        for slot_type, defs in groups:
            assert isinstance(slot_type, str)
            assert isinstance(defs, list)

    def test_palette_includes_cargo_slots_after_buying_hold(self) -> None:
        """End-to-end: buying scrapyard_hold -> cargo slot type appears
        in the palette."""
        from spacegame.data_loader import get_data_loader
        from spacegame.views.ship_builder_view import ShipBuilderView

        _init_pygame()
        dl = get_data_loader()
        dl.load_all()
        player = _make_player()
        # Tutorial purchase of cargo hold -> should unlock cargo slot type
        player.dialogue_flags["tutorial_bought_part_scrapyard_hold"] = True

        view = ShipBuilderView.__new__(ShipBuilderView)
        view.player = player
        view.data_loader = dl
        view._tutorial_mode = True

        groups = view._get_slot_definitions_grouped()
        slot_types_shown = {st for st, _defs in groups}
        assert "cargo" in slot_types_shown, (
            f"Cargo slot should appear after buying scrapyard_hold; got {slot_types_shown}"
        )
        # Cockpit always available
        assert "cockpit" in slot_types_shown

    def test_no_purchases_falls_back_to_full_tutorial_palette(self) -> None:
        """Edge case: player enters builder before any purchase flag set
        (shouldn't happen normally, but UX safety). Falls back to full
        tutorial palette so the screen isn't empty."""
        from spacegame.data_loader import get_data_loader
        from spacegame.views.ship_builder_view import ShipBuilderView

        _init_pygame()
        dl = get_data_loader()
        dl.load_all()
        player = _make_player()
        # No tutorial purchase flags set

        view = ShipBuilderView.__new__(ShipBuilderView)
        view.player = player
        view.data_loader = dl
        view._tutorial_mode = True

        groups = view._get_slot_definitions_grouped()
        slot_types_shown = {st for st, _defs in groups}
        # Should show something — fallback ensures palette isn't empty
        assert len(slot_types_shown) > 0


# ---------------------------------------------------------------------------
# UI FIX: long part names don't overflow card
# ---------------------------------------------------------------------------


class TestTutorialPartNameTruncation:
    def test_long_part_name_fits_card_width(self) -> None:
        """Salvaged Pulse Emitter at standard card width should now
        truncate-with-ellipsis instead of overflowing."""
        from spacegame.engine.draw_utils import truncate_text
        from spacegame.engine.fonts import FONT_XL, get_font

        _init_pygame()
        font = get_font("dialogue", FONT_XL)
        long_name = "Salvaged Pulse Emitter"
        # Approximate tutorial shop card width minus padding
        card_w_minus_padding = 200
        truncated = truncate_text(long_name, font, card_w_minus_padding)
        surf = font.render(truncated, True, (255, 255, 255))
        assert surf.get_width() <= card_w_minus_padding

    def test_short_part_name_unchanged(self) -> None:
        """Truncation should be a no-op for names that fit."""
        from spacegame.engine.draw_utils import truncate_text
        from spacegame.engine.fonts import FONT_XL, get_font

        _init_pygame()
        font = get_font("dialogue", FONT_XL)
        short_name = "Hold"
        truncated = truncate_text(short_name, font, 200)
        assert truncated == short_name


# ---------------------------------------------------------------------------
# Integration: tutorial purchase flow round-trip with both fixes
# ---------------------------------------------------------------------------


class TestPickTutorialNarrationNoCrash:
    """The 2nd KeyError crash came from _pick_tutorial_narration which
    has the same p['slot_def_id'] bug. Direct regression."""

    def test_pick_narration_does_not_crash_after_purchase(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.views.ship_builder_view import ShipBuilderView
        from spacegame.views.tutorial_shop_view import TUTORIAL_PARTS

        _init_pygame()
        dl = get_data_loader()
        dl.load_all()
        player = _make_player()
        player.dialogue_flags["tutorial_bought_part_scrapyard_hold"] = True

        view = ShipBuilderView.__new__(ShipBuilderView)
        view.player = player
        view.data_loader = dl
        view._tutorial_mode = True
        view._selected_slot_def_id = None
        view._shown_rotation_tip = False

        part_narration = {
            "cockpit_scout_pod": "Cockpit narration",
            "cargo_small": "Cargo narration",
        }
        # Empty placed_ids → welcome narration fires
        result = view._pick_tutorial_narration(set(), part_narration, TUTORIAL_PARTS)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_pick_narration_selects_by_slot_type_not_part_id(self) -> None:
        """After buying scrapyard_hold (slot_type=cargo) but placing no
        cargo slot yet, the narration should point to the cargo line."""
        from spacegame.data_loader import get_data_loader
        from spacegame.views.ship_builder_view import ShipBuilderView
        from spacegame.views.tutorial_shop_view import TUTORIAL_PARTS

        _init_pygame()
        dl = get_data_loader()
        dl.load_all()
        player = _make_player()
        player.dialogue_flags["tutorial_bought_part_scrapyard_hold"] = True

        view = ShipBuilderView.__new__(ShipBuilderView)
        view.player = player
        view.data_loader = dl
        view._tutorial_mode = True
        view._selected_slot_def_id = None
        view._shown_rotation_tip = False

        part_narration = {
            "cargo_small": "CARGO_LINE",
            "weapon_small": "WEAPON_LINE",
        }
        # Simulate cockpit already placed (so "welcome" doesn't fire),
        # but no cargo placed yet
        placed_ids = {"cockpit_scout_pod"}
        result = view._pick_tutorial_narration(placed_ids, part_narration, TUTORIAL_PARTS)
        assert result == "CARGO_LINE", (
            f"Expected cargo narration for bought scrapyard_hold; got {result!r}"
        )


class TestNoMoreBrokenPatterns:
    """Compliance scan: catch any remaining use of the broken
    p['slot_def_id'] pattern on TUTORIAL_PARTS dicts. Also catches the
    flag-name mismatch (tutorial_bought_X instead of
    tutorial_bought_part_X)."""

    def test_no_slot_def_id_indexing_on_tutorial_parts_dicts(self) -> None:
        """The KeyError crashed in two different functions because both
        read p['slot_def_id']. If we see that pattern anywhere in code
        that iterates TUTORIAL_PARTS, it's the same bug waiting."""
        import re
        from pathlib import Path

        # Scan view source for the broken indexing. Skip lines that are
        # comments / docstring prose / backtick-quoted examples — those are
        # historical references in explanatory text, not live code.
        view_dir = Path("spacegame/views")
        offenders = []
        pattern = re.compile(r"""p\[['"]slot_def_id['"]\]""")
        for pyfile in view_dir.glob("*.py"):
            source = pyfile.read_text(encoding="utf-8")
            if "TUTORIAL_PARTS" not in source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if not pattern.search(line):
                    continue
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                # Backtick-quoted (docstring prose, Sphinx-style ``x``)
                if "``" in line and "p['slot_def_id']" in line.replace("``p['slot_def_id']``", ""):
                    # Shouldn't reach here — the replace above zeros it out
                    offenders.append(f"{pyfile.name}:{i}: {line.strip()}")
                    continue
                if "``p['slot_def_id']``" in line:
                    continue
                offenders.append(f"{pyfile.name}:{i}: {line.strip()}")
        assert not offenders, (
            "Found p['slot_def_id'] usage in files that iterate "
            "TUTORIAL_PARTS. Those dicts use 'part_id'. Offenders:\n  " + "\n  ".join(offenders)
        )

    def test_tutorial_bought_flag_name_consistent(self) -> None:
        """The shop sets 'tutorial_bought_part_X'. Any reader must use
        the same prefix — catch bare 'tutorial_bought_X' reads."""
        import re
        from pathlib import Path

        view_dir = Path("spacegame/views")
        offenders = []
        # Bad pattern: 'tutorial_bought_' followed directly by a
        # interpolated part ID WITHOUT the 'part_' infix
        bad_pattern = re.compile(r"""tutorial_bought_\{""")
        for pyfile in view_dir.glob("*.py"):
            source = pyfile.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                if bad_pattern.search(line):
                    offenders.append(f"{pyfile.name}:{i}: {line.strip()}")
        assert not offenders, (
            "Found raw 'tutorial_bought_{...}' (missing 'part_' infix). "
            "Shop sets 'tutorial_bought_part_{part_id}'. Offenders:\n  " + "\n  ".join(offenders)
        )


class TestTutorialFlowEndToEnd:
    def test_purchase_then_builder_pipeline_works(self) -> None:
        """Simulate the player buying every required tutorial part + the
        cargo hold, then entering the builder — palette should show all
        the slot types matching their purchases without crashing."""
        from spacegame.data_loader import get_data_loader
        from spacegame.views.ship_builder_view import ShipBuilderView
        from spacegame.views.tutorial_shop_view import TUTORIAL_PARTS

        _init_pygame()
        dl = get_data_loader()
        dl.load_all()
        player = _make_player()

        # Mark all 3 mandatory + cargo hold purchased (typical playthrough)
        from spacegame.constants.flags import tutorial_bought_part

        for p in TUTORIAL_PARTS:
            if p.part_id in (
                "scrapyard_thruster",
                "scrapyard_reactor",
                "scrapyard_fuel_cell",
                "scrapyard_hold",
            ):
                player.dialogue_flags[tutorial_bought_part(p.part_id)] = True

        view = ShipBuilderView.__new__(ShipBuilderView)
        view.player = player
        view.data_loader = dl
        view._tutorial_mode = True

        groups = view._get_slot_definitions_grouped()
        slot_types_shown = {st for st, _defs in groups}
        # All slot types matching purchased parts should appear
        expected_types = {"cockpit", "engine", "reactor", "fuel", "cargo"}
        assert expected_types.issubset(slot_types_shown), (
            f"Missing slot types: {expected_types - slot_types_shown}"
        )
