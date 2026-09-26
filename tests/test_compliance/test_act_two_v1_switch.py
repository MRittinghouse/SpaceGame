"""Act II v1 is archived and off by default (SP2 spec Section 5).

Act II v1 was written into the Act I galaxy and is not ported. The flag keeps
the Python reference behaving as Act I only; archived tests opt back in with
the ``act_two_v1`` marker.
"""

from __future__ import annotations

import pytest

import spacegame.config as sg_config
from spacegame.data_loader import DataLoader, get_data_loader
from tests.test_scenarios._helpers import fresh_player


class TestActTwoV1Switch:
    def test_flag_defaults_off(self) -> None:
        assert sg_config.ACT_TWO_V1_ENABLED is False, "Act II v1 must be off by default"

    def test_load_all_skips_act_two_registries(self) -> None:
        loader = DataLoader()
        loader.load_all()
        assert not loader.lenses, "lenses must not load with the flag off"
        assert not loader.capstones, "capstones must not load with the flag off"
        assert not loader.lens_reactions, "lens reactions must not load with the flag off"
        assert not loader.dilemmas, "dilemmas must not load with the flag off"
        assert not loader.post_capstone_templates, "post-capstone templates must not load"

    def test_load_act_two_v1_loads_registries(self) -> None:
        loader = DataLoader()
        loader.load_all()
        loader.load_act_two_v1()
        assert loader.lenses, "load_act_two_v1 must load the lens registry"
        assert loader.dilemmas, "load_act_two_v1 must load the dilemma registry"

    def test_record_lens_action_is_inert(self) -> None:
        player = fresh_player()
        assert player.record_lens_action("sold_cargo", 1) == [], (
            "record_lens_action must accrue nothing while Act II v1 is off"
        )


@pytest.mark.act_two_v1
class TestActTwoV1Marker:
    def test_marker_turns_the_flag_and_registries_on(self) -> None:
        assert sg_config.ACT_TWO_V1_ENABLED is True, "the marker must turn the flag on"
        assert get_data_loader().lenses, "the marker must make the lens registry available"
