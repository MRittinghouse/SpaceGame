"""Bug bash BB-4: Elena, Footing the Bill and The Dead Ledger wait on the campaign's flag.

The flag ``iron_delivery_moved_on`` says the campaign no longer waits on Odom's errand;
``iron_delivery_resolved`` says the job itself is over. The delivery's reward sets the
campaign's flag, the betrayal's close sets it, and the job's clock sets it
(``spacegame.models.iron_consignment``), so no ending of the job ends the campaign.
"""

from __future__ import annotations

import pytest

from spacegame.constants.flags import iron_delivery_moved_on
from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.dialogue import DialogueManager
from spacegame.models.iron_consignment import OPEN_STATES, STATE_FLAGS, on_clock
from spacegame.models.mission import Mission, MissionManager, MissionStatus
from spacegame.models.player import Player
from spacegame.models.ship import Ship

FLAG = "iron_delivery_moved_on"
CLOSING_FLAGS = {"iron_ore_handed_over", "iron_delivery_failed", "iron_delivery_closed"}

# Every disposition or standing change in the job's trees, with what keeps it to one time
# (polish design 2.9: every disposition change sits on a one-time path). A new change fails
# test_every_change_is_reviewed until it is added here with its reason.
CHANGES: dict[tuple[str, str, str], str] = {
    (
        "merchant_delivery",
        "declined",
        "[Leave]",
    ): "sets iron_delivery_resolved, which the offer excludes",
    ("merchant_delivery", "waiting", "Take it back. I'm not running it."): "closes the job",
    ("merchant_delivery", "waiting_count", "Take it back. I'm not running it."): "closes the job",
    (
        "merchant_delivery",
        "waiting_clause",
        "Then it'll be there.",
    ): "behind the final Observation check",
    ("merchant_delivery", "loss_short", "Take back what's left."): "closes the job",
    ("merchant_delivery", "betrayal_lie", "..."): "the betrayal fails the job",
    ("merchant_delivery", "betrayal_rant", "It was just business."): "the betrayal fails the job",
    ("merchant_delivery", "betrayal_end", "[Leave]"): "the betrayal fails the job",
    (
        "merchant_delivery",
        "thanks",
        "You know where to find me.",
    ): "sets odom_ledger_open, which the reply excludes",
    (
        "merchant_delivery",
        "made_good_book",
        "You know where to find me.",
    ): "sets odom_ledger_open, which the reply excludes",
    (
        "merchant_delivery",
        "thanks_replaced",
        "The count was right.",
    ): "sets odom_noted_the_float, which the reply excludes",
    (
        "forgeworks_intake",
        "crucible",
        "[Wait while he calls it in.]",
    ): "behind the final crucible check",
    (
        "forgeworks_intake",
        "shop_talk",
        "Sounds like a living.",
    ): "sets intake_shop_talk_heard, which the reply excludes",
}
CHANGE_TREES = ("merchant_delivery", "forgeworks_intake")


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _mission(mission_id: str) -> Mission:
    return next(m for m in _dl().missions if m.id == mission_id)


def test_the_helper_names_the_content_flag() -> None:
    assert iron_delivery_moved_on() == FLAG


def test_elena_comes_when_the_campaign_moves_on() -> None:
    assert _dl().npcs["elena_reeves"].auto_trigger_prerequisites == [FLAG]


def test_footing_the_bill_waits_on_the_flag_not_a_completed_delivery() -> None:
    footing = _mission("footing_the_bill")
    assert footing.prerequisites == ["bill_of_landing"]
    assert footing.required_flags == [FLAG, "talked_to_elena_cantina"]
    assert "settled or overdue" in footing.hint


def test_the_dead_ledger_waits_on_the_flag_not_a_completed_delivery() -> None:
    ledger = _mission("the_dead_ledger")
    assert ledger.available_after == "bill_of_landing"
    assert ledger.required_flags == [FLAG]


def test_the_delivery_sets_the_flag() -> None:
    rewards = [(r.reward_type, r.target_id) for r in _mission("iron_delivery").rewards]
    assert ("set_flag", FLAG) in rewards
    assert ("set_flag", "iron_ore_delivered") in rewards


def test_a_failed_delivery_no_longer_closes_the_campaign() -> None:
    manager = MissionManager(_dl().missions)
    manager.load_state({"status": {"bill_of_landing": "completed", "iron_delivery": "failed"}})
    flags = {"iron_delivery_failed": True, FLAG: True, "talked_to_elena_cantina": True}
    manager.update_availability(flags, game_day=12)
    assert manager.get_status("footing_the_bill") == MissionStatus.ACTIVE
    assert manager.get_status("the_dead_ledger") == MissionStatus.AVAILABLE


def test_a_job_left_open_moves_the_campaign_on_and_still_pays() -> None:
    dl = _dl()
    manager = MissionManager(dl.missions)
    manager.load_state(
        {
            "status": {"bill_of_landing": "completed", "iron_delivery": "active"},
            "accepted_day": {"iron_delivery": 1},
        }
    )
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    player = Player("TestPilot", 5000, "nexus_prime", ship)
    player.ship.add_cargo("iron_ore", 10, 0)
    assert on_clock(manager, player, player.dialogue_flags, 20)
    player.dialogue_flags["talked_to_elena_cantina"] = True
    manager.update_availability(player.dialogue_flags, game_day=20)
    assert manager.get_status("footing_the_bill") == MissionStatus.ACTIVE
    assert manager.get_status("iron_delivery") == MissionStatus.ACTIVE
    player.game_day = 25
    manager.apply_rewards("iron_delivery", player)
    assert player.credits == 5000 + 300


def _greet_targets(flags: dict[str, bool]) -> set[str]:
    manager = DialogueManager()
    manager.load_flags(flags)
    manager.start_dialogue(_dl().dialogue_trees["merchant_delivery"], "odom_broker")
    return {r.next_node_id for r in manager.get_available_responses()}


def _walk_nodes(tree_id: str, start: str) -> set[str]:
    """Every node reachable from start, following replies and both branches of a check."""
    tree = _dl().dialogue_trees[tree_id]
    todo, seen = [start], set()
    while todo:
        node_id = todo.pop()
        if node_id in seen or node_id not in tree.nodes:
            continue
        seen.add(node_id)
        for r in tree.nodes[node_id].responses:
            if r.skill_check:
                todo += [r.skill_check.success_node_id, r.skill_check.failure_node_id]
            if r.next_node_id:
                todo.append(r.next_node_id)
    return seen


def test_a_finished_delivery_never_offers_the_betrayal() -> None:
    assert "betrayal" in _greet_targets({"iron_job_moved": True})
    targets = _greet_targets({"iron_job_done_clean": True, FLAG: True})
    assert "thanks" in targets
    assert "betrayal" not in targets


def test_the_reward_ends_the_job_and_moves_the_campaign_on() -> None:
    rewards = [(r.reward_type, r.target_id) for r in _mission("iron_delivery").rewards]
    assert ("set_flag", "iron_delivery_resolved") in rewards
    assert ("set_flag", FLAG) in rewards


def test_the_hand_over_pays_on_what_was_weighed() -> None:
    mission = _mission("iron_delivery")
    delivered = [
        (r.target_id, r.amount) for r in mission.rewards if r.reward_type == "deliver_cargo"
    ]
    assert delivered == [(c.commodity_id, c.quantity) for c in mission.on_accept_cargo]


def test_each_state_gates_a_reply() -> None:
    tree = _dl().dialogue_trees["merchant_delivery"]
    gated = {f for n in tree.nodes.values() for r in n.responses for f in r.required_flags}
    assert set(STATE_FLAGS) <= gated


def test_every_close_sits_behind_an_open_state() -> None:
    tree = _dl().dialogue_trees["merchant_delivery"]
    reachable: set[str] = set()
    for r in tree.nodes["greet"].responses:
        if set(r.required_flags) & set(OPEN_STATES) and r.next_node_id:
            reachable |= _walk_nodes("merchant_delivery", r.next_node_id)
    closing = {
        n.id
        for n in tree.nodes.values()
        for r in n.responses
        if r.set_flag in {"iron_delivery_failed", "iron_delivery_closed"}
    }
    assert closing and closing <= reachable


def test_hearing_the_offer_no_longer_accepts_it() -> None:
    tree = _dl().dialogue_trees["merchant_delivery"]
    assert all(not r.set_flag for r in tree.nodes["offer"].responses)
    accepts = [r for r in tree.nodes["details"].responses if r.set_flag == "talked_to_cargo_broker"]
    assert [r.next_node_id for r in accepts] == [None]


def test_the_betrayal_costs_the_guild_and_nothing_else() -> None:
    end = _dl().dialogue_trees["merchant_delivery"].nodes["betrayal_end"]
    (leave,) = end.responses
    assert leave.set_flag == "iron_delivery_failed"
    assert leave.faction_reputation_changes == [{"commerce_guild": -10}]


def test_every_change_is_reviewed() -> None:
    found = {
        (tree_id, node.id, r.text)
        for tree_id in CHANGE_TREES
        for node in _dl().dialogue_trees[tree_id].nodes.values()
        for r in node.responses
        if r.disposition_change or r.faction_reputation_changes
    }
    assert found == set(CHANGES)


def test_the_longer_ledger_opens_on_odoms_word() -> None:
    ledger = _mission("sa_v_investment_intro")
    assert ledger.prerequisites == ["bill_of_landing"]
    assert ledger.required_flags == ["odom_ledger_open"]


@pytest.mark.parametrize("state", OPEN_STATES)
def test_every_open_state_has_a_closing_reply(state: str) -> None:
    """Polish design 2.9: in every open state, someone who can close the job offers a way."""
    from spacegame.models.iron_consignment import closers

    who = closers({state: True})
    assert who
    for npc_id in who:
        tree_id = _dl().npcs[npc_id].dialogue_id
        greet = _dl().dialogue_trees[tree_id].nodes["greet"]
        starts = [r.next_node_id for r in greet.responses if state in r.required_flags]
        assert starts, (npc_id, state)
        tree = _dl().dialogue_trees[tree_id]
        closing = [
            node_id
            for start in starts
            if start
            for node_id in _walk_nodes(tree_id, start)
            if any(r.set_flag in CLOSING_FLAGS for r in tree.nodes[node_id].responses)
        ]
        assert closing, (npc_id, state)


def test_the_clerk_signs_only_what_the_scale_reads() -> None:
    greet = _dl().dialogue_trees["forgeworks_intake"].nodes["greet"]
    targets = {r.next_node_id: r.required_flags for r in greet.responses if r.required_flags}
    assert targets["accept"] == ["iron_job_full"]
    assert targets["accept_made_good"] == ["iron_job_made_good"]
    assert targets["accept_floor_stock"] == ["iron_job_replaced"]
    assert targets["no_sign"] == ["iron_job_moved"]
    assert targets["weigh_short"] == ["iron_job_short_lost"]
    assert targets["nothing_to_weigh"] == ["iron_job_gone_lost"]


def test_elenas_iron_replies_are_one_time_each() -> None:
    tips = _dl().dialogue_trees["elena_cantina"].nodes["trading_tips"]
    gated = {r.next_node_id: (r.required_flags, r.excluded_flags) for r in tips.responses[:3]}
    assert gated == {
        "iron_carriage": (["iron_ore_delivered"], ["elena_heard_carriage"]),
        "iron_lane": (["broker_ore_lost"], ["elena_heard_lane"]),
        "iron_violation": (["iron_delivery_failed"], ["elena_heard_violation"]),
    }
