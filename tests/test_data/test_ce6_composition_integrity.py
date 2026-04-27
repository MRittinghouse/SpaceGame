"""CE-6e: composition integrity tests.

Locks in the wiring CE-6 established between captains, complications,
encounters, and crew interjections so future content changes preserve
the composition CE finished with.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


# ---------------------------------------------------------------------------
# Reference integrity
# ---------------------------------------------------------------------------


class TestReferenceIntegrity:
    def test_every_captain_id_referenced_by_encounter_resolves(self, dl) -> None:
        """No encounter references a non-existent captain."""
        for d in dl.encounter_definitions:
            if not d.captain_id:
                continue
            assert d.captain_id in dl.captains, (
                f"Encounter '{d.id}' references unknown captain '{d.captain_id}'"
            )

    def test_every_complication_id_referenced_by_encounter_resolves(self, dl) -> None:
        for d in dl.encounter_definitions:
            for cid in d.complication_ids:
                assert cid in dl.complications, (
                    f"Encounter '{d.id}' references unknown complication '{cid}'"
                )

    def test_captain_signature_ships_resolve(self, dl) -> None:
        """Every captain's signature_ship_template must be a real enemy."""
        for cid, cap in dl.captains.items():
            assert cap.signature_ship_template in dl.enemy_templates, (
                f"Captain '{cid}' references unknown enemy template '{cap.signature_ship_template}'"
            )


# ---------------------------------------------------------------------------
# Coverage floors (ratchets — raise when CE phases extend wiring)
# ---------------------------------------------------------------------------


class TestCoverageFloors:
    def test_no_orphan_complications(self, dl) -> None:
        """CE-6 wired all 6 complications. Future content must not let any
        become orphans without an explicit deferral."""
        referenced: set[str] = set()
        for d in dl.encounter_definitions:
            referenced.update(d.complication_ids)
        orphans = set(dl.complications.keys()) - referenced
        assert not orphans, f"Orphan complications (no encounter references): {sorted(orphans)}"

    def test_minimum_captain_attachments(self, dl) -> None:
        """CE-6 attached 8 captains. Hold the line so attachments don't
        regress. RC phase should raise this."""
        attached_count = sum(1 for d in dl.encounter_definitions if d.captain_id)
        assert attached_count >= 8, f"Only {attached_count} captains attached, expected >=8"

    def test_minimum_encounters_per_main_faction(self, dl) -> None:
        """Spec target: every faction has 3+ distinctive encounter types."""
        from collections import Counter

        per_faction: Counter = Counter()
        for d in dl.encounter_definitions:
            if d.required_faction:
                per_faction[d.required_faction] += 1
        for faction in (
            "commerce_guild",
            "frontier_alliance",
            "miners_union",
            "science_collective",
        ):
            assert per_faction[faction] >= 3, (
                f"Faction '{faction}' has {per_faction[faction]} encounters, expected >=3"
            )


# ---------------------------------------------------------------------------
# Captain x crew nemesis composition (CE-6 magic moments)
# ---------------------------------------------------------------------------


class TestCaptainCrewComposition:
    """The two encounters where captain ship matches a crew nemesis trigger
    must keep that alignment so the cinematic moment fires."""

    def test_anatolia_attachment_spawns_guild_revenue_cutter(self, dl) -> None:
        """ransom_guild_audit_01 has anatolia + guild_revenue_cutter spawn
        for Elena's nemesis interjection to fire."""
        defn = next(
            (d for d in dl.encounter_definitions if d.id == "ransom_guild_audit_01"),
            None,
        )
        assert defn is not None
        assert defn.captain_id == "anatolia_kestrel_crow"
        cap = dl.captains[defn.captain_id]
        assert cap.signature_ship_template == "guild_revenue_cutter"
        # At least one combat outcome must spawn the captain's signature ship
        spawns = []
        for c in defn.choices:
            if c.outcome.leads_to_combat:
                spawns.extend(c.outcome.enemy_template_ids)
            if c.failure_outcome and c.failure_outcome.leads_to_combat:
                spawns.extend(c.failure_outcome.enemy_template_ids)
        assert "guild_revenue_cutter" in spawns, (
            "ransom_guild_audit_01 combat outcomes must spawn "
            "guild_revenue_cutter for the Elena nemesis composition"
        )

    def test_ngozi_attachment_spawns_union_brawler(self, dl) -> None:
        """shakedown_ore_holdup_01 has ngozi + union_brawler spawn for
        Marcus's nemesis interjection to fire."""
        defn = next(
            (d for d in dl.encounter_definitions if d.id == "shakedown_ore_holdup_01"),
            None,
        )
        assert defn is not None
        assert defn.captain_id == "ngozi_pale_reckoning"
        cap = dl.captains[defn.captain_id]
        assert cap.signature_ship_template == "union_brawler"
        spawns = []
        for c in defn.choices:
            if c.outcome.leads_to_combat:
                spawns.extend(c.outcome.enemy_template_ids)
            if c.failure_outcome and c.failure_outcome.leads_to_combat:
                spawns.extend(c.failure_outcome.enemy_template_ids)
        assert "union_brawler" in spawns, (
            "shakedown_ore_holdup_01 combat outcomes must spawn "
            "union_brawler for the Marcus nemesis composition"
        )

    def test_crew_nemesis_targets_align_with_captain_ships(self, dl) -> None:
        """The crew interjection enemy_type_match conditions should target
        ships that exist as some captain's signature ship — otherwise the
        composition magic never fires in normal play."""
        captain_ships = {cap.signature_ship_template for cap in dl.captains.values()}
        nemesis_targets: dict[str, str] = {}
        for entry in dl.crew_interjections:
            if entry.trigger == "enemy_type_match":
                tid = entry.conditions.get("enemy_template_id", "")
                if tid:
                    nemesis_targets[entry.crew_id] = tid
        unaligned = {
            crew_id: tid for crew_id, tid in nemesis_targets.items() if tid not in captain_ships
        }
        assert not unaligned, (
            f"Crew nemesis targets not in any captain's signature_ship pool: "
            f"{unaligned}. Either align nemesis to a captain ship, or "
            f"author a captain whose ship matches."
        )


# ---------------------------------------------------------------------------
# Captain dialogue Writing Bible (extends sprint 5 scanner)
# ---------------------------------------------------------------------------


class TestCaptainDialogueWritingBible:
    EM_DASHES = ("\u2014", "\u2013", " -- ")
    BANNED_PHRASES = (
        "couldn't help but",
        "a testament to",
        "could not help but",
    )

    def test_no_em_dashes_in_captain_dialogue(self, dl) -> None:
        offenders = []
        for cid, cap in dl.captains.items():
            for field_name in (
                "pre_combat_hail",
                "surrender_line",
                "retreat_line",
                "victory_line",
                "defeat_line",
            ):
                text = getattr(cap, field_name, "")
                for dash in self.EM_DASHES:
                    if dash in text:
                        offenders.append(f"{cid}.{field_name}: {text[:80]!r}")
                        break
        assert not offenders, "Em-dashes in captain dialogue:\n  " + "\n  ".join(offenders)

    def test_no_banned_phrases_in_captain_dialogue(self, dl) -> None:
        offenders = []
        for cid, cap in dl.captains.items():
            for field_name in (
                "pre_combat_hail",
                "surrender_line",
                "retreat_line",
                "victory_line",
                "defeat_line",
            ):
                text = getattr(cap, field_name, "").lower()
                for phrase in self.BANNED_PHRASES:
                    if phrase in text:
                        offenders.append(f"{cid}.{field_name}: {phrase!r}")
        assert not offenders, "Banned phrases in captain dialogue:\n  " + "\n  ".join(offenders)
