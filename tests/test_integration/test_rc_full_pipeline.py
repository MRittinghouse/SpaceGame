"""RC-7: full RC arc integration tests.

Each test exercises multiple RC sprints in one chain so future content
or refactors that break the composition surface here, not in production.

Coverage matrix:
- RC-7a: Single captain through full lifecycle (RC-1 through RC-6)
- RC-7b: Composition magic (anatolia + Elena nemesis interjection)
- RC-7c: Multi-captain pool degradation
- RC-7e: Variant content quality bounds
- RC-7f: Save/load with rich RC state
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.data_loader import get_data_loader
from spacegame.models.captain_memory import (
    OUTCOME_BRIBED,
    OUTCOME_NEGOTIATED,
    OUTCOME_VICTORY,
    STATUS_BRIBED_OFF,
    STATUS_DEFEATED,
    STATUS_TRUCE,
)
from spacegame.models.captain_variant import (
    MEETING_STATE_POST_BRIBED_OFF,
    get_effective_captain_dialogue,
)
from spacegame.models.combat import (
    CombatEncounter,
    CombatState,
    EnemyShip,
    PlayerCombatState,
)
from spacegame.models.crew_interjection import CrewInterjectionResolver
from spacegame.models.encounter import EncounterContext, select_encounter_definition
from spacegame.models.journal import Journal
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.views.encounter_view import EncounterView

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _init_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _ui_manager() -> pygame_gui.UIManager:
    _init_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _make_player(game_day: int = 5) -> Player:
    ship_type = ShipType(
        id="shuttle", name="Shuttle", ship_class="light",
        description="x", cargo_capacity=10, fuel_capacity=50,
        fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=2, special_abilities=[],
        availability="all",
    )
    player = Player(
        name="Test", credits=2000, current_system_id="havens_rest",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )
    player.game_day = game_day
    return player


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


# ---------------------------------------------------------------------------
# RC-7a: Full single-captain lifecycle
# ---------------------------------------------------------------------------


class TestFullCaptainLifecycle:
    """Trace one captain from first meeting through resolution and verify
    every RC system fires in the right order."""

    def test_pay_to_bribed_off_full_cycle(self, dl) -> None:
        # Use vela_wolfs_ear attached to ransom_pirate_corvette_01
        defn = next(
            d for d in dl.encounter_definitions
            if d.id == "ransom_pirate_corvette_01"
        )
        assert defn.captain_id == "vela_wolfs_ear"

        player = _make_player(game_day=5)
        # Move past min_level=2 so the encounter is eligible
        player.progression.level = 5
        journal = Journal()
        from spacegame.models.encounter import EncounterRef

        # === Phase 1: First meeting renders base hail (RC-3) ===
        view = EncounterView(
            ui_manager=_ui_manager(),
            encounter_def=defn,
            encounter_ref=EncounterRef(
                enemy_template_ids=["pirate_raider"], encounter_seed=42
            ),
            player=player,
            journal=journal,
        )
        view.on_enter()
        # Effective dialogue should be base (no memory yet)
        assert view._effective_dialogue is not None
        captain = dl.captains["vela_wolfs_ear"]
        assert view._effective_dialogue.pre_combat_hail == captain.pre_combat_hail
        # Badge: empty (never met)
        assert view._met_before_badge_text() == ""

        # === Phase 2: Player picks Pay (non-combat) ===
        # Find the "pay" choice index
        pay_idx = next(
            i for i, c in enumerate(view.display_choices) if c.id == "pay"
        )
        view._select_choice(pay_idx)

        # === Phase 3: RC-6 recording fires, journal entry added ===
        assert "vela_wolfs_ear" in player.captain_memory
        mem = player.captain_memory["vela_wolfs_ear"]
        assert mem.encounter_count == 1
        assert mem.last_outcome == OUTCOME_BRIBED
        assert mem.status == STATUS_BRIBED_OFF
        assert mem.is_resolved
        # Journal entry from first meeting
        entries = journal.get_entries()
        assert len(entries) == 1
        assert "Captain Vela" in entries[0].text
        assert entries[0].tag == "people"
        view.on_exit()

        # === Phase 4: Encounter is now filtered from random pool (RC-5) ===
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="dangerous",
            seed=99,
            player_level=5,
            resolved_captain_ids={
                cid for cid, m in player.captain_memory.items() if m.is_resolved
            },
        )
        for seed in range(1, 100):
            ctx.seed = seed
            picked = select_encounter_definition(dl.encounter_definitions, ctx)
            if picked:
                assert picked.id != "ransom_pirate_corvette_01", (
                    f"Filtered captain encounter still spawned (seed={seed})"
                )

        # === Phase 5: Forced re-encounter uses post_bribed_off variant (RC-3+RC-4) ===
        # Vela has an authored post_bribed_off variant from RC-4
        post_variant = dl.captain_variants.get(
            ("vela_wolfs_ear", MEETING_STATE_POST_BRIBED_OFF)
        )
        assert post_variant is not None, "RC-4 should have authored vela post_bribed_off"
        effective = get_effective_captain_dialogue(
            captain, mem, dl.captain_variants
        )
        assert effective.pre_combat_hail == post_variant.pre_combat_hail
        assert effective.meeting_state == MEETING_STATE_POST_BRIBED_OFF


# ---------------------------------------------------------------------------
# RC-7b: Composition magic (captain + crew nemesis interjection)
# ---------------------------------------------------------------------------


class TestCompositionMagic:
    """The marquee CE-6 composition: anatolia attached to ransom_guild_audit_01,
    her signature ship is guild_revenue_cutter, Elena's nemesis interjection
    fires on guild_revenue_cutter. All three fire in one fight."""

    def test_anatolia_encounter_fires_elena_nemesis_interjection(self, dl) -> None:
        # Build the encounter the way game.py would
        defn = next(
            d for d in dl.encounter_definitions
            if d.id == "ransom_guild_audit_01"
        )
        assert defn.captain_id == "anatolia_kestrel_crow"

        # Find the spawn override for the refuse outcome
        refuse_choice = next(c for c in defn.choices if c.id == "refuse")
        assert "guild_revenue_cutter" in refuse_choice.outcome.enemy_template_ids

        # Simulate the combat encounter spawning guild_revenue_cutter
        revenue_cutter = dl.enemy_templates["guild_revenue_cutter"]
        encounter = CombatEncounter(
            enemy_templates=[revenue_cutter],
            encounter_seed=42,
            captain_id="anatolia_kestrel_crow",
        )
        state = CombatState(
            player=PlayerCombatState(
                hull=100, max_hull=100, shields=20, max_shields=40,
                energy=10, max_energy=10, energy_regen=3, speed=8,
                evasion=10, accuracy=80, equipment_moves=[], crew_moves=[],
                active_effects=[], cooldowns={},
            ),
            enemies=[EnemyShip.from_template(revenue_cutter)],
            encounter=encounter,
            combat_log=[],
        )

        # Find Elena's nemesis interjection entry
        elena_nemesis = next(
            e for e in dl.crew_interjections
            if e.crew_id == "elena_reeves"
            and e.trigger == "enemy_type_match"
        )
        # Elena's nemesis must be guild_revenue_cutter (CE-6 alignment)
        assert elena_nemesis.conditions["enemy_template_id"] == "guild_revenue_cutter"

        # Build the resolver as the view would
        resolver = CrewInterjectionResolver(
            dl.crew_interjections,
            crew_aboard=[("elena_reeves", "Elena")],
            seed=42,
        )
        events = resolver.evaluate_round(state)
        # Elena's nemesis interjection is in the eligible set
        nemesis_events = [
            e for e in events
            if e.trigger == "enemy_type_match"
            and e.crew_id == "elena_reeves"
        ]
        assert len(nemesis_events) == 1, (
            "Elena's nemesis interjection should fire when fighting "
            "guild_revenue_cutter under anatolia attachment"
        )


# ---------------------------------------------------------------------------
# RC-7c: Multi-captain pool degradation
# ---------------------------------------------------------------------------


class TestPoolDegradation:
    def test_resolving_one_captain_removes_only_their_encounter(self, dl) -> None:
        # Resolve vela; other ransom captains still spawnable
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="dangerous",
            seed=42,
            player_level=5,
            resolved_captain_ids={"vela_wolfs_ear"},
        )
        seen = set()
        for seed in range(1, 200):
            ctx.seed = seed
            picked = select_encounter_definition(dl.encounter_definitions, ctx)
            if picked:
                seen.add(picked.id)
        # Vela's encounter never appears
        assert "ransom_pirate_corvette_01" not in seen
        # At least one other ransom encounter still appears
        other_ransoms = {
            "ransom_reach_collector_01",
            "ransom_frontier_brigand_01",
            "ransom_guild_audit_01",
        }
        assert seen & other_ransoms, "Other ransom encounters should still spawn"

    def test_resolving_all_ransom_captains_drains_pool(self, dl) -> None:
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="dangerous",
            seed=42,
            player_level=5,
            resolved_captain_ids={
                "vela_wolfs_ear",
                "calder_cold_read",
                "fyodor_fourth_try",
                "anatolia_kestrel_crow",
            },
        )
        # Pool is empty; selection returns None for every seed
        for seed in range(1, 50):
            ctx.seed = seed
            picked = select_encounter_definition(dl.encounter_definitions, ctx)
            assert picked is None, (
                f"All ransom captains resolved but encounter still spawned: {picked.id}"
            )


# ---------------------------------------------------------------------------
# RC-7e: Variant content quality bounds
# ---------------------------------------------------------------------------


class TestVariantContentQuality:
    HAIL_MAX_LENGTH = 280  # Fits the encounter view text box at all resolutions
    HAIL_MIN_LENGTH = 8    # Reject dead-empty placeholders

    def test_no_variant_hail_is_a_copy_of_base(self, dl) -> None:
        """A variant pre_combat_hail that equals the base hail is dead
        content — it overlays nothing."""
        offenders = []
        for (cid, _state), variant in dl.captain_variants.items():
            if not variant.pre_combat_hail:
                continue
            base = dl.captains[cid].pre_combat_hail
            if variant.pre_combat_hail == base:
                offenders.append(f"{cid}: variant equals base hail")
        assert not offenders, (
            "Variant hails identical to base:\n  " + "\n  ".join(offenders)
        )

    def test_variant_hail_length_within_bounds(self, dl) -> None:
        offenders = []
        for (cid, state), variant in dl.captain_variants.items():
            if not variant.pre_combat_hail:
                continue
            n = len(variant.pre_combat_hail)
            if n < self.HAIL_MIN_LENGTH:
                offenders.append(
                    f"{cid}/{state}: hail too short ({n} chars)"
                )
            if n > self.HAIL_MAX_LENGTH:
                offenders.append(
                    f"{cid}/{state}: hail too long ({n} chars)"
                )
        assert not offenders, (
            "Variant hail length issues:\n  " + "\n  ".join(offenders)
        )

    def test_no_duplicate_variant_hails_across_captains(self, dl) -> None:
        """Different captains shouldn't share variant hail text — the
        whole point of variants is captain-specific voice."""
        seen: dict[str, list[str]] = {}
        for (cid, _state), variant in dl.captain_variants.items():
            if not variant.pre_combat_hail:
                continue
            seen.setdefault(variant.pre_combat_hail, []).append(cid)
        dups = {h: cids for h, cids in seen.items() if len(cids) > 1}
        assert not dups, (
            f"Duplicate variant hails across captains: {dups}"
        )


# ---------------------------------------------------------------------------
# RC-7f: Save/load with rich RC state
# ---------------------------------------------------------------------------


class TestSaveLoadRichState:
    def test_full_rc_state_survives_roundtrip(self, tmp_path) -> None:
        from spacegame.save_manager import SaveManager

        # Build a player with multiple captains in different states
        player = _make_player(game_day=20)
        player.record_captain_encounter("vela_wolfs_ear", OUTCOME_VICTORY)
        player.game_day = 25
        player.record_captain_encounter("calder_cold_read", OUTCOME_NEGOTIATED)
        player.game_day = 30
        player.record_captain_encounter("ngozi_pale_reckoning", OUTCOME_BRIBED)

        sm = SaveManager(save_directory=tmp_path)
        sm.save_game(
            slot=0, player=player, markets={}, active_events={},
            playtime_seconds=0,
        )

        loaded = sm.load_game(slot=0)
        assert loaded is not None
        loaded_player = loaded["player"]

        # All three memories preserved with correct status
        assert loaded_player.captain_memory["vela_wolfs_ear"].status == STATUS_DEFEATED
        assert loaded_player.captain_memory["calder_cold_read"].status == STATUS_TRUCE
        assert loaded_player.captain_memory["ngozi_pale_reckoning"].status == STATUS_BRIBED_OFF

        # Resolved captains drive the filter on load
        resolved = {
            cid for cid, m in loaded_player.captain_memory.items()
            if m.is_resolved
        }
        assert resolved == {
            "vela_wolfs_ear", "calder_cold_read", "ngozi_pale_reckoning"
        }


# ---------------------------------------------------------------------------
# RC-7d: Programmatic journal text Writing Bible compliance
# ---------------------------------------------------------------------------


class TestProgrammaticJournalCompliance:
    """The journal entry text generated by RC-6 from captain data must
    follow the Writing Bible (no em-dashes leaking from display_name)."""

    EM_DASHES = ("\u2014", "\u2013", " -- ")

    def test_journal_text_for_every_captain_is_clean(self, dl) -> None:
        """Simulate what the journal text would look like for each of the
        17 captains and assert no em-dashes leak."""
        offenders = []
        for cid, captain in dl.captains.items():
            nickname_phrase = (
                f', the {captain.nickname},' if captain.nickname else ','
            )
            text = (
                f"Met {captain.name}{nickname_phrase} for the first time. "
                f"Their ship runs the {captain.signature_ship_template} hull. "
                f"They keep a base out of {captain.home_sector or 'parts unknown'}."
            )
            for dash in self.EM_DASHES:
                if dash in text:
                    offenders.append(f"{cid}: em-dash in journal text")
                    break
        assert not offenders, (
            "Journal text contains em-dashes:\n  " + "\n  ".join(offenders)
        )
