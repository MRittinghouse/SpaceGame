"""PT-I "Second conversation" regression tests.

Covers the security desk scene (Sgt. Mossa / dead_ledger_investigation):
  - Decision-lock: once dead_ledger_accusation_made is set, investigation
    responses disappear and a recap branch takes their place.
  - Clean exits: nested nodes (suspects, evidence_synthesis) have
    come-back-later responses.
  - Pre-choice framing: greet text explicitly names the "why you" beat so
    the player understands why Mossa is asking a stranger.
  - Recap node (case_closed) exists and is routable from greet.
"""

from __future__ import annotations

import json
import os


def _tree() -> dict:
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dialogue", "dialogues.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return next(d for d in data["dialogues"] if d["id"] == "dead_ledger_investigation")


def _node(tree: dict, node_id: str) -> dict:
    return next(n for n in tree["nodes"] if n["id"] == node_id)


class TestDecisionLock:
    def test_greet_investigation_responses_excluded_after_accusation(self) -> None:
        """After accusation, the three investigation paths disappear."""
        greet = _node(_tree(), "greet")
        gated = [
            r
            for r in greet["responses"]
            if "dead_ledger_accusation_made" in r.get("excluded_flags", [])
        ]
        # Five pre-accusation responses must all exclude the accusation flag:
        # walk me through, NV-7 [Leadership] lead-the-investigation, review
        # suspects, make accusation, come back later.
        assert len(gated) == 5, (
            f"expected 5 responses gated on dead_ledger_accusation_made, found {len(gated)}"
        )

    def test_greet_recap_response_requires_accusation_flag(self) -> None:
        """The 'Any word from the prosecutor?' response only appears post-accusation."""
        greet = _node(_tree(), "greet")
        recap = next(
            (r for r in greet["responses"] if "prosecutor" in r["text"].lower()),
            None,
        )
        assert recap is not None, "greet must have a prosecutor-follow-up response"
        assert "dead_ledger_accusation_made" in recap.get("required_flags", [])
        assert recap["next_node_id"] == "case_closed"

    def test_case_closed_node_exists(self) -> None:
        case = _node(_tree(), "case_closed")
        assert case["speaker_id"] == "dock_investigator"
        # Exactly one exit response
        assert len(case["responses"]) == 1
        assert case["responses"][0]["next_node_id"] is None

    def test_case_closed_does_not_reopen_accusation(self) -> None:
        """Recap response must not route back into the accuse flow."""
        case = _node(_tree(), "case_closed")
        for r in case["responses"]:
            assert r["next_node_id"] is None, (
                "case_closed must terminate the conversation, not route to accuse_* nodes"
            )


class TestCleanExits:
    def test_suspects_node_has_come_back_later(self) -> None:
        suspects = _node(_tree(), "suspects")
        exits = [r for r in suspects["responses"] if r["next_node_id"] is None]
        assert exits, "suspects node must allow the player to leave without committing"

    def test_evidence_synthesis_has_come_back_later(self) -> None:
        syn = _node(_tree(), "evidence_synthesis")
        exits = [r for r in syn["responses"] if r["next_node_id"] is None]
        assert exits, "evidence_synthesis must allow the player to leave without accusing"

    def test_greet_come_back_later_excluded_post_accusation(self) -> None:
        """Come-back-later on greet must not persist after the case closes —
        it would be a dead option."""
        greet = _node(_tree(), "greet")
        cbl = next(
            (r for r in greet["responses"] if "come back later" in r["text"].lower()),
            None,
        )
        assert cbl is not None
        assert "dead_ledger_accusation_made" in cbl.get("excluded_flags", [])


class TestPreChoiceFraming:
    def test_greet_text_explains_why_player_specifically(self) -> None:
        """Playtester missed the original 'second opinion' framing. New text
        makes the 'why you' beat explicit."""
        greet = _node(_tree(), "greet")
        text = greet["text"].lower()
        # The key beat: Mossa names the reason you specifically are being asked.
        # The strengthened copy should mention the player's outsider status.
        assert "that's why you" in text, (
            "greet must explicitly state the why-you reason, not just imply it"
        )

    def test_greet_preserves_voice_and_facts(self) -> None:
        """Text tightening must not break Mossa's voice or lose case facts."""
        greet = _node(_tree(), "greet")
        text = greet["text"]
        # Voice anchors
        assert "Pull up a crate" in text
        assert "Reshad Patel" in text
        assert "Loading Bay C" in text
        # Writing Bible compliance
        assert "\u2014" not in text, "no em-dashes"
        assert "couldn't help but" not in text.lower()


class TestAccuseFlags:
    def test_all_three_accuse_nodes_set_umbrella_flag(self) -> None:
        """Every accusation path must set dead_ledger_accusation_made so the
        mission completes AND the decision-lock kicks in."""
        tree = _tree()
        for nid in ("accuse_vey", "accuse_drum", "accuse_solis"):
            node = _node(tree, nid)
            set_flags = [r.get("set_flag") for r in node["responses"]]
            assert "dead_ledger_accusation_made" in set_flags, (
                f"{nid} must set dead_ledger_accusation_made on exit"
            )
