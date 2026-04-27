"""RC-3: CaptainVariant model + resolution helper tests."""

from __future__ import annotations

import pytest

from spacegame.models.captain_memory import (
    OUTCOME_BRIBED,
    OUTCOME_NEGOTIATED,
    OUTCOME_VICTORY,
    STATUS_ACTIVE,
    STATUS_BRIBED_OFF,
    STATUS_DEFEATED,
    STATUS_TRUCE,
    STATUS_WANDERER,
    CaptainMemory,
)
from spacegame.models.captain_variant import (
    MEETING_STATE_FIRST,
    MEETING_STATE_POST_BRIBED_OFF,
    MEETING_STATE_POST_DEFEATED,
    MEETING_STATE_POST_TRUCE,
    MEETING_STATE_POST_WANDERER,
    MEETING_STATE_RETURN,
    VALID_MEETING_STATES,
    CaptainVariant,
    EffectiveCaptainDialogue,
    get_effective_captain_dialogue,
    meeting_state_for_memory,
)
from spacegame.models.enemy_captain import EnemyCaptain


# ---------------------------------------------------------------------------
# Model basics
# ---------------------------------------------------------------------------


class TestCaptainVariantModel:
    def test_round_trip(self) -> None:
        original = CaptainVariant(
            captain_id="vela_wolfs_ear",
            meeting_state=MEETING_STATE_RETURN,
            pre_combat_hail="Wolf's Ear again. Different cargo, same answer.",
            victory_line="Told you we'd meet again.",
        )
        restored = CaptainVariant.from_dict(original.to_dict())
        assert restored == original

    def test_defaults_empty(self) -> None:
        v = CaptainVariant(captain_id="x", meeting_state=MEETING_STATE_RETURN)
        assert v.pre_combat_hail == ""
        assert v.surrender_line == ""
        assert v.retreat_line == ""
        assert v.victory_line == ""
        assert v.defeat_line == ""

    def test_meeting_state_constants(self) -> None:
        for s in (
            MEETING_STATE_FIRST,
            MEETING_STATE_RETURN,
            MEETING_STATE_POST_TRUCE,
            MEETING_STATE_POST_BRIBED_OFF,
            MEETING_STATE_POST_DEFEATED,
            MEETING_STATE_POST_WANDERER,
        ):
            assert s in VALID_MEETING_STATES


# ---------------------------------------------------------------------------
# Meeting state derivation
# ---------------------------------------------------------------------------


class TestMeetingStateForMemory:
    def test_no_memory_means_first(self) -> None:
        assert meeting_state_for_memory(None) == MEETING_STATE_FIRST

    def test_zero_count_means_first(self) -> None:
        mem = CaptainMemory(captain_id="x")
        assert meeting_state_for_memory(mem) == MEETING_STATE_FIRST

    def test_active_with_count_means_return(self) -> None:
        mem = CaptainMemory(captain_id="x", encounter_count=1, status=STATUS_ACTIVE)
        assert meeting_state_for_memory(mem) == MEETING_STATE_RETURN

    @pytest.mark.parametrize(
        "status,expected",
        [
            (STATUS_TRUCE, MEETING_STATE_POST_TRUCE),
            (STATUS_BRIBED_OFF, MEETING_STATE_POST_BRIBED_OFF),
            (STATUS_DEFEATED, MEETING_STATE_POST_DEFEATED),
            (STATUS_WANDERER, MEETING_STATE_POST_WANDERER),
        ],
    )
    def test_resolved_status_maps_to_post_state(self, status, expected) -> None:
        mem = CaptainMemory(captain_id="x", encounter_count=1, status=status)
        assert meeting_state_for_memory(mem) == expected


# ---------------------------------------------------------------------------
# Effective dialogue overlay
# ---------------------------------------------------------------------------


def _make_captain() -> EnemyCaptain:
    return EnemyCaptain(
        id="vela_wolfs_ear",
        name="Captain Vela",
        nickname="Wolf's Ear",
        home_sector="havens_rest",
        signature_ship_template="pirate_raider",
        pre_combat_hail="base hail",
        surrender_line="base surrender",
        retreat_line="base retreat",
        victory_line="base victory",
        defeat_line="base defeat",
    )


class TestGetEffectiveCaptainDialogue:
    def test_no_variant_returns_base_lines(self) -> None:
        cap = _make_captain()
        eff = get_effective_captain_dialogue(cap, None, {})
        assert eff.pre_combat_hail == "base hail"
        assert eff.surrender_line == "base surrender"
        assert eff.retreat_line == "base retreat"
        assert eff.victory_line == "base victory"
        assert eff.defeat_line == "base defeat"
        assert eff.meeting_state == MEETING_STATE_FIRST
        assert eff.display_name == cap.display_name

    def test_variant_overlays_only_specified_fields(self) -> None:
        cap = _make_captain()
        memory = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            status=STATUS_ACTIVE,
        )
        variants = {
            ("vela_wolfs_ear", MEETING_STATE_RETURN): CaptainVariant(
                captain_id="vela_wolfs_ear",
                meeting_state=MEETING_STATE_RETURN,
                pre_combat_hail="return hail",
                # surrender_line, retreat_line, victory_line, defeat_line empty
            )
        }
        eff = get_effective_captain_dialogue(cap, memory, variants)
        # Overridden
        assert eff.pre_combat_hail == "return hail"
        # Empty variant fields fall back to base
        assert eff.surrender_line == "base surrender"
        assert eff.victory_line == "base victory"
        assert eff.defeat_line == "base defeat"
        assert eff.retreat_line == "base retreat"
        assert eff.meeting_state == MEETING_STATE_RETURN

    def test_variant_overlays_all_fields_when_authored(self) -> None:
        cap = _make_captain()
        memory = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            status=STATUS_TRUCE,
        )
        variants = {
            ("vela_wolfs_ear", MEETING_STATE_POST_TRUCE): CaptainVariant(
                captain_id="vela_wolfs_ear",
                meeting_state=MEETING_STATE_POST_TRUCE,
                pre_combat_hail="truce broken hail",
                surrender_line="truce surrender",
                retreat_line="truce retreat",
                victory_line="truce victory",
                defeat_line="truce defeat",
            )
        }
        eff = get_effective_captain_dialogue(cap, memory, variants)
        assert eff.pre_combat_hail == "truce broken hail"
        assert eff.surrender_line == "truce surrender"
        assert eff.retreat_line == "truce retreat"
        assert eff.victory_line == "truce victory"
        assert eff.defeat_line == "truce defeat"

    def test_first_meeting_uses_base_even_with_authored_first_meeting_variant(
        self,
    ) -> None:
        """A 'first_meeting' authored variant would also overlay if keyed."""
        cap = _make_captain()
        variants = {
            ("vela_wolfs_ear", MEETING_STATE_FIRST): CaptainVariant(
                captain_id="vela_wolfs_ear",
                meeting_state=MEETING_STATE_FIRST,
                pre_combat_hail="custom first hail",
            )
        }
        eff = get_effective_captain_dialogue(cap, None, variants)
        assert eff.pre_combat_hail == "custom first hail"
        assert eff.meeting_state == MEETING_STATE_FIRST

    def test_variant_for_wrong_state_is_ignored(self) -> None:
        cap = _make_captain()
        memory = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            status=STATUS_ACTIVE,  # state is "return"
        )
        variants = {
            # Authored only for post_truce — not applicable to return
            ("vela_wolfs_ear", MEETING_STATE_POST_TRUCE): CaptainVariant(
                captain_id="vela_wolfs_ear",
                meeting_state=MEETING_STATE_POST_TRUCE,
                pre_combat_hail="should not appear",
            )
        }
        eff = get_effective_captain_dialogue(cap, memory, variants)
        assert eff.pre_combat_hail == "base hail"
