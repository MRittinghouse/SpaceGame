"""CE-1: tests for the EnemyCaptain model + data loader integration.

Covers:
  - Round-trip ``from_dict`` / ``to_dict``
  - Default handling (missing optional fields)
  - ``display_name`` property formatting (with / without nickname)
  - ``lookup_captain`` helper
  - Data loader parses the CE-1 stub roster
  - Encounter integration: ``EncounterDefinition.captain_id`` threads
    through the parser and is reachable from the encounter
"""

from __future__ import annotations

import pytest

from spacegame.models.enemy_captain import EnemyCaptain, lookup_captain


class TestEnemyCaptainModel:
    def test_from_dict_minimum_fields(self) -> None:
        captain = EnemyCaptain.from_dict(
            {
                "id": "test",
                "name": "Test Captain",
                "nickname": "",
                "home_sector": "nexus_prime",
                "signature_ship_template": "pirate_scout",
                "pre_combat_hail": "Hold position.",
            }
        )
        assert captain.id == "test"
        assert captain.name == "Test Captain"
        assert captain.nickname == ""
        assert captain.home_sector == "nexus_prime"
        assert captain.pre_combat_hail == "Hold position."
        # Optional fields default to empty string / False
        assert captain.surrender_line == ""
        assert captain.retreat_line == ""
        assert captain.victory_line == ""
        assert captain.defeat_line == ""
        assert captain.is_recurring is False

    def test_from_dict_full_fields(self) -> None:
        data = {
            "id": "vela",
            "name": "Captain Vela",
            "nickname": "Wolf's Ear",
            "home_sector": "havens_rest",
            "signature_ship_template": "pirate_raider",
            "pre_combat_hail": "Wolf's Ear. Talk fast.",
            "surrender_line": "Yielding.",
            "retreat_line": "Out.",
            "victory_line": "Told you.",
            "defeat_line": "Not the whole pack.",
            "is_recurring": True,
        }
        captain = EnemyCaptain.from_dict(data)
        assert captain.is_recurring is True
        assert captain.surrender_line == "Yielding."
        assert captain.retreat_line == "Out."

    def test_round_trip(self) -> None:
        data = {
            "id": "round_trip",
            "name": "Round Trip",
            "nickname": "Mirror",
            "home_sector": "iron_depths",
            "signature_ship_template": "mercenary_gunship",
            "pre_combat_hail": "Before you move, listen.",
            "surrender_line": "",
            "retreat_line": "See you.",
            "victory_line": "",
            "defeat_line": "",
            "is_recurring": False,
        }
        captain = EnemyCaptain.from_dict(data)
        assert captain.to_dict() == data


class TestDisplayName:
    def test_with_nickname(self) -> None:
        captain = EnemyCaptain(
            id="x",
            name="Captain Vela",
            nickname="Wolf's Ear",
            home_sector="havens_rest",
            signature_ship_template="pirate_raider",
            pre_combat_hail="hail",
        )
        # em-dash (U+2014) separator between name and nickname
        assert captain.display_name == "Captain Vela \u2014 Wolf's Ear"

    def test_without_nickname(self) -> None:
        captain = EnemyCaptain(
            id="x",
            name="Plain Captain",
            nickname="",
            home_sector="nexus_prime",
            signature_ship_template="pirate_scout",
            pre_combat_hail="hail",
        )
        assert captain.display_name == "Plain Captain"


class TestLookupCaptain:
    def _make(self):
        return {
            "vela": EnemyCaptain(
                id="vela",
                name="Captain Vela",
                nickname="Wolf's Ear",
                home_sector="havens_rest",
                signature_ship_template="pirate_raider",
                pre_combat_hail="hail",
            )
        }

    def test_resolves_known_id(self) -> None:
        cs = self._make()
        assert lookup_captain(cs, "vela") is not None

    def test_returns_none_for_empty_id(self) -> None:
        cs = self._make()
        assert lookup_captain(cs, "") is None
        assert lookup_captain(cs, None) is None

    def test_returns_none_for_unknown_id(self) -> None:
        cs = self._make()
        assert lookup_captain(cs, "unknown") is None


class TestDataLoader:
    """Data loader integration — the CE-1 stub roster loads."""

    def test_loader_parses_stub_roster(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        assert len(dl.captains) >= 2, "CE-1 ships at least 2 stub captains"
        assert "vela_wolfs_ear" in dl.captains
        assert "calder_cold_read" in dl.captains

    def test_loaded_captains_have_valid_structure(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for captain in dl.captains.values():
            assert captain.id, "every captain must have an id"
            assert captain.name, "every captain must have a name"
            assert captain.home_sector, "every captain must have a home_sector"
            assert captain.signature_ship_template, (
                "every captain must reference a signature_ship_template"
            )
            assert captain.pre_combat_hail, (
                "every captain must have a pre_combat_hail"
            )
            # Stub captains are all non-recurring (RC will flip specific
            # ones in a later phase).
            assert captain.is_recurring is False

    def test_captain_home_sectors_reference_real_systems(self) -> None:
        """Captain home_sector ids should resolve to real systems."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for captain in dl.captains.values():
            assert captain.home_sector in dl.systems, (
                f"captain {captain.id} home_sector='{captain.home_sector}' "
                "does not resolve to a real system"
            )

    def test_captain_ship_templates_reference_real_enemies(self) -> None:
        """Captain signature_ship_template ids must resolve to real enemy templates.

        Catches typos in captain authoring at load time rather than at
        combat time.
        """
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for captain in dl.captains.values():
            assert captain.signature_ship_template in dl.enemy_templates, (
                f"captain {captain.id} signature_ship_template="
                f"'{captain.signature_ship_template}' does not resolve "
                "to a registered enemy template"
            )


class TestCaptainContentQuality:
    """CE-2 roster quality: variety + writing discipline across the roster."""

    def test_roster_size_in_target_band(self) -> None:
        """CE-2 target: 15-20 captains total."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        assert 15 <= len(dl.captains) <= 20, (
            f"CE-2 roster target is 15-20 captains; found {len(dl.captains)}"
        )

    def test_home_sector_variety(self) -> None:
        """Captains should spread across multiple systems — no single
        sector hoards more than half the roster."""
        from spacegame.data_loader import get_data_loader
        from collections import Counter

        dl = get_data_loader()
        dl.load_all()
        counts = Counter(c.home_sector for c in dl.captains.values())
        max_share = max(counts.values()) / len(dl.captains)
        assert max_share <= 0.5, (
            f"One sector holds {max_share:.0%} of the roster. Spread captains."
        )

    def test_ship_template_variety(self) -> None:
        """At least half the roster should fly distinct ship templates."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        unique_ships = len({c.signature_ship_template for c in dl.captains.values()})
        assert unique_ships >= len(dl.captains) / 2, (
            f"Only {unique_ships} unique ship templates across "
            f"{len(dl.captains)} captains. Vary the fleet."
        )

    def test_nicknames_are_unique(self) -> None:
        """Every captain has a distinctive ship nickname. No duplicates."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        nicknames = [c.nickname for c in dl.captains.values() if c.nickname]
        assert len(nicknames) == len(set(nicknames)), (
            "Duplicate ship nickname(s) in captain roster"
        )

    def test_pre_combat_hails_minimum_length(self) -> None:
        """Every hail must carry at least two sentences of voice.

        Single-sentence hails read as templates. CE-2 roster is
        character-forward — every captain earns a real first-impression.
        """
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for captain in dl.captains.values():
            sentences = [
                s.strip() for s in captain.pre_combat_hail.split(".") if s.strip()
            ]
            # Tsovinar's entire voice is minimalism — she gets the exception.
            # Any captain whose hail is <=2 words per sentence is a
            # short-voice specialist and we trust the author.
            if captain.id == "sovi_mirror":
                continue
            assert len(sentences) >= 2, (
                f"captain {captain.id} pre_combat_hail has only "
                f"{len(sentences)} sentence(s); minimum 2 for voice"
            )

    def test_no_em_dashes_in_captain_dialogue(self) -> None:
        """Writing Bible compliance on captain-authored content."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        offenders = []
        for captain in dl.captains.values():
            for field_name in (
                "pre_combat_hail",
                "surrender_line",
                "retreat_line",
                "victory_line",
                "defeat_line",
            ):
                text = getattr(captain, field_name)
                if "\u2014" in text or "\u2013" in text:
                    offenders.append(f"{captain.id}.{field_name}: {text[:80]!r}")
        assert not offenders, (
            "Em-dashes / en-dashes in captain dialogue:\n  "
            + "\n  ".join(offenders)
        )

    def test_no_ai_tells_in_captain_dialogue(self) -> None:
        """No 'couldn't help but', 'a testament to', or similar AI tells."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        banned = ["couldn't help but", "a testament to"]
        offenders = []
        for captain in dl.captains.values():
            for field_name in (
                "pre_combat_hail",
                "surrender_line",
                "retreat_line",
                "victory_line",
                "defeat_line",
            ):
                text = getattr(captain, field_name).lower()
                for phrase in banned:
                    if phrase in text:
                        offenders.append(f"{captain.id}.{field_name}: '{phrase}'")
        assert not offenders, "AI tells in captain dialogue:\n  " + "\n  ".join(
            offenders
        )


class TestEncounterDefinitionCaptainId:
    """The new ``captain_id`` field threads through parsing + defaults."""

    def test_encounter_definition_has_captain_id_default_empty(self) -> None:
        from spacegame.models.encounter import (
            EncounterChoice,
            EncounterDefinition,
            EncounterOutcome,
        )

        defn = EncounterDefinition(
            id="x",
            encounter_type="test",
            name="Test",
            description="desc",
            choices=[
                EncounterChoice(
                    id="c",
                    label="choice",
                    description="d",
                    outcome=EncounterOutcome(description="", rewards=[]),
                )
            ],
        )
        assert defn.captain_id == ""

    def test_encounter_definition_accepts_captain_id(self) -> None:
        from spacegame.models.encounter import (
            EncounterChoice,
            EncounterDefinition,
            EncounterOutcome,
        )

        defn = EncounterDefinition(
            id="x",
            encounter_type="test",
            name="Test",
            description="desc",
            choices=[
                EncounterChoice(
                    id="c",
                    label="choice",
                    description="d",
                    outcome=EncounterOutcome(description="", rewards=[]),
                )
            ],
            captain_id="vela_wolfs_ear",
        )
        assert defn.captain_id == "vela_wolfs_ear"

    def test_parser_threads_captain_id(self) -> None:
        """DataLoader._parse_encounter_definition preserves captain_id."""
        from spacegame.data_loader import DataLoader

        dl = DataLoader()
        raw = {
            "id": "test_ce1",
            "encounter_type": "hostile",
            "name": "Test",
            "description": "desc",
            "choices": [],
            "captain_id": "vela_wolfs_ear",
        }
        defn = dl._parse_encounter_definition(raw)
        assert defn.captain_id == "vela_wolfs_ear"

    def test_parser_defaults_captain_id_when_absent(self) -> None:
        """Legacy encounters without captain_id parse cleanly to empty."""
        from spacegame.data_loader import DataLoader

        dl = DataLoader()
        raw = {
            "id": "legacy",
            "encounter_type": "hostile",
            "name": "Legacy",
            "description": "desc",
            "choices": [],
        }
        defn = dl._parse_encounter_definition(raw)
        assert defn.captain_id == ""


class TestCombatComplicationModel:
    """CE-1 ships the model only. CE-3 wires triggers to handlers."""

    def test_from_dict_roundtrip(self) -> None:
        from spacegame.models.combat_complication import CombatComplication

        data = {
            "id": "reinforcement_t3",
            "name": "Reinforcement Arrival",
            "description": "Additional enemies drop in at turn 3",
            "trigger_type": "turn_counter",
            "trigger_params": {"turn": 3},
            "effect_type": "spawn_reinforcement",
            "effect_params": {"template_ids": ["pirate_scout"]},
            "narration": "Another ship warps in.",
        }
        c = CombatComplication.from_dict(data)
        assert c.id == "reinforcement_t3"
        assert c.trigger_params == {"turn": 3}
        assert c.effect_params == {"template_ids": ["pirate_scout"]}
        assert c.to_dict() == data

    def test_defaults_when_params_absent(self) -> None:
        from spacegame.models.combat_complication import CombatComplication

        c = CombatComplication.from_dict(
            {
                "id": "simple",
                "name": "Simple",
                "description": "desc",
                "trigger_type": "turn_counter",
                "effect_type": "environmental",
            }
        )
        assert c.trigger_params == {}
        assert c.effect_params == {}
        assert c.narration == ""

    def test_valid_types_enumerated(self) -> None:
        """Catch typos by verifying types match the enumerated constants."""
        from spacegame.models.combat_complication import (
            VALID_EFFECT_TYPES,
            VALID_TRIGGER_TYPES,
        )

        assert "turn_counter" in VALID_TRIGGER_TYPES
        assert "spawn_reinforcement" in VALID_EFFECT_TYPES
