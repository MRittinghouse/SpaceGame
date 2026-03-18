"""Tests for encounter filtering with system, faction, flag, and level constraints."""

from spacegame.models.encounter import (
    EncounterContext,
    EncounterDefinition,
    EncounterChoice,
    EncounterOutcome,
    select_encounter_definition,
    _is_eligible,
)


def _make_definition(
    id: str = "test_enc",
    encounter_type: str = "distress_signal",
    danger_levels: list[str] | None = None,
    weight: int = 10,
    only_systems: list[str] | None = None,
    excluded_systems: list[str] | None = None,
    required_faction: str = "",
    requires_flags: list[str] | None = None,
    excludes_flags: list[str] | None = None,
    unique: bool = False,
    min_level: int = 0,
    max_level: int = 0,
    tone: str = "",
    category: str = "",
) -> EncounterDefinition:
    """Create a test encounter definition with sensible defaults."""
    return EncounterDefinition(
        id=id,
        encounter_type=encounter_type,
        name="Test Encounter",
        description="A test encounter.",
        choices=[
            EncounterChoice(
                id="choice_a",
                label="Do something",
                description="Action.",
                outcome=EncounterOutcome(description="Result.", rewards=[]),
            )
        ],
        weight=weight,
        danger_levels=danger_levels or ["moderate", "dangerous"],
        icon_color=(200, 200, 200),
        only_systems=only_systems or [],
        excluded_systems=excluded_systems or [],
        required_faction=required_faction,
        requires_flags=requires_flags or [],
        excludes_flags=excludes_flags or [],
        unique=unique,
        min_level=min_level,
        max_level=max_level,
        tone=tone,
        category=category,
    )


def _make_context(
    encounter_type: str = "distress_signal",
    danger_level: str = "moderate",
    seed: int = 42,
    system_id: str = "nexus_prime",
    faction_id: str = "commerce_guild",
    player_level: int = 5,
    dialogue_flags: dict[str, bool] | None = None,
) -> EncounterContext:
    """Create a test encounter context with sensible defaults."""
    return EncounterContext(
        encounter_type=encounter_type,
        danger_level=danger_level,
        seed=seed,
        system_id=system_id,
        faction_id=faction_id,
        player_level=player_level,
        dialogue_flags=dialogue_flags or {},
    )


class TestEncounterContext:
    """Tests for EncounterContext dataclass."""

    def test_defaults(self) -> None:
        ctx = EncounterContext(encounter_type="hostile", danger_level="moderate", seed=1)
        assert ctx.system_id == ""
        assert ctx.faction_id == ""
        assert ctx.player_level == 1
        assert ctx.dialogue_flags == {}

    def test_all_fields(self) -> None:
        ctx = _make_context(
            system_id="breakstone",
            faction_id="miners_union",
            player_level=10,
            dialogue_flags={"flag_a": True},
        )
        assert ctx.system_id == "breakstone"
        assert ctx.faction_id == "miners_union"
        assert ctx.player_level == 10
        assert ctx.dialogue_flags == {"flag_a": True}


class TestIsEligible:
    """Tests for the _is_eligible filtering function."""

    def test_basic_type_and_danger_match(self) -> None:
        defn = _make_definition()
        ctx = _make_context()
        assert _is_eligible(defn, ctx)

    def test_type_mismatch_excluded(self) -> None:
        defn = _make_definition(encounter_type="merchant")
        ctx = _make_context(encounter_type="distress_signal")
        assert not _is_eligible(defn, ctx)

    def test_danger_level_mismatch_excluded(self) -> None:
        defn = _make_definition(danger_levels=["dangerous"])
        ctx = _make_context(danger_level="moderate")
        assert not _is_eligible(defn, ctx)

    # --- System filtering ---

    def test_only_systems_includes(self) -> None:
        defn = _make_definition(only_systems=["nexus_prime", "breakstone"])
        ctx = _make_context(system_id="nexus_prime")
        assert _is_eligible(defn, ctx)

    def test_only_systems_excludes(self) -> None:
        defn = _make_definition(only_systems=["breakstone"])
        ctx = _make_context(system_id="nexus_prime")
        assert not _is_eligible(defn, ctx)

    def test_only_systems_empty_means_all(self) -> None:
        defn = _make_definition(only_systems=[])
        ctx = _make_context(system_id="any_system")
        assert _is_eligible(defn, ctx)

    def test_excluded_systems_blocks(self) -> None:
        defn = _make_definition(excluded_systems=["nexus_prime"])
        ctx = _make_context(system_id="nexus_prime")
        assert not _is_eligible(defn, ctx)

    def test_excluded_systems_allows_others(self) -> None:
        defn = _make_definition(excluded_systems=["nexus_prime"])
        ctx = _make_context(system_id="breakstone")
        assert _is_eligible(defn, ctx)

    # --- Faction filtering ---

    def test_required_faction_matches(self) -> None:
        defn = _make_definition(required_faction="commerce_guild")
        ctx = _make_context(faction_id="commerce_guild")
        assert _is_eligible(defn, ctx)

    def test_required_faction_mismatches(self) -> None:
        defn = _make_definition(required_faction="commerce_guild")
        ctx = _make_context(faction_id="miners_union")
        assert not _is_eligible(defn, ctx)

    def test_required_faction_empty_means_any(self) -> None:
        defn = _make_definition(required_faction="")
        ctx = _make_context(faction_id="miners_union")
        assert _is_eligible(defn, ctx)

    # --- Flag filtering ---

    def test_requires_flags_all_must_be_set(self) -> None:
        defn = _make_definition(requires_flags=["flag_a", "flag_b"])
        ctx = _make_context(dialogue_flags={"flag_a": True, "flag_b": True})
        assert _is_eligible(defn, ctx)

    def test_requires_flags_missing_one_excludes(self) -> None:
        defn = _make_definition(requires_flags=["flag_a", "flag_b"])
        ctx = _make_context(dialogue_flags={"flag_a": True})
        assert not _is_eligible(defn, ctx)

    def test_requires_flags_empty_means_no_requirement(self) -> None:
        defn = _make_definition(requires_flags=[])
        ctx = _make_context(dialogue_flags={})
        assert _is_eligible(defn, ctx)

    def test_excludes_flags_any_blocks(self) -> None:
        defn = _make_definition(excludes_flags=["flag_x"])
        ctx = _make_context(dialogue_flags={"flag_x": True})
        assert not _is_eligible(defn, ctx)

    def test_excludes_flags_absent_allows(self) -> None:
        defn = _make_definition(excludes_flags=["flag_x"])
        ctx = _make_context(dialogue_flags={})
        assert _is_eligible(defn, ctx)

    # --- Unique encounters ---

    def test_unique_allowed_before_seen(self) -> None:
        defn = _make_definition(id="special_event", unique=True)
        ctx = _make_context(dialogue_flags={})
        assert _is_eligible(defn, ctx)

    def test_unique_excluded_after_seen(self) -> None:
        defn = _make_definition(id="special_event", unique=True)
        ctx = _make_context(dialogue_flags={"encounter_seen_special_event": True})
        assert not _is_eligible(defn, ctx)

    # --- Level filtering ---

    def test_min_level_filters(self) -> None:
        defn = _make_definition(min_level=10)
        ctx = _make_context(player_level=5)
        assert not _is_eligible(defn, ctx)

    def test_min_level_exact_passes(self) -> None:
        defn = _make_definition(min_level=5)
        ctx = _make_context(player_level=5)
        assert _is_eligible(defn, ctx)

    def test_max_level_filters(self) -> None:
        defn = _make_definition(max_level=3)
        ctx = _make_context(player_level=5)
        assert not _is_eligible(defn, ctx)

    def test_max_level_exact_passes(self) -> None:
        defn = _make_definition(max_level=5)
        ctx = _make_context(player_level=5)
        assert _is_eligible(defn, ctx)

    def test_level_zero_means_no_constraint(self) -> None:
        defn = _make_definition(min_level=0, max_level=0)
        ctx = _make_context(player_level=99)
        assert _is_eligible(defn, ctx)

    # --- Combined filters ---

    def test_combined_filters_all_pass(self) -> None:
        defn = _make_definition(
            only_systems=["breakstone"],
            required_faction="miners_union",
            requires_flags=["met_foreman"],
            min_level=3,
            max_level=20,
        )
        ctx = _make_context(
            system_id="breakstone",
            faction_id="miners_union",
            player_level=10,
            dialogue_flags={"met_foreman": True},
        )
        assert _is_eligible(defn, ctx)

    def test_combined_filters_one_fails(self) -> None:
        defn = _make_definition(
            only_systems=["breakstone"],
            required_faction="miners_union",
            min_level=3,
        )
        ctx = _make_context(
            system_id="breakstone",
            faction_id="commerce_guild",  # Wrong faction
            player_level=10,
        )
        assert not _is_eligible(defn, ctx)

    # --- Backward compatibility ---

    def test_backward_compat_no_new_fields(self) -> None:
        """Encounter with no new fields passes all filters."""
        defn = EncounterDefinition(
            id="old_enc",
            encounter_type="distress_signal",
            name="Old",
            description="Old encounter.",
            choices=[
                EncounterChoice(
                    id="a",
                    label="A",
                    description="A.",
                    outcome=EncounterOutcome(description="R.", rewards=[]),
                )
            ],
            weight=10,
            danger_levels=["moderate", "dangerous"],
            icon_color=(200, 200, 200),
        )
        ctx = _make_context()
        assert _is_eligible(defn, ctx)


class TestSelectEncounterDefinitionWithContext:
    """Tests for context-based encounter selection."""

    def test_selects_eligible_encounter(self) -> None:
        eligible = _make_definition(id="eligible", only_systems=["nexus_prime"])
        ineligible = _make_definition(id="ineligible", only_systems=["breakstone"])
        ctx = _make_context(system_id="nexus_prime")

        result = select_encounter_definition([eligible, ineligible], ctx)
        assert result is not None
        assert result.id == "eligible"

    def test_returns_none_when_no_candidates(self) -> None:
        defn = _make_definition(required_faction="miners_union")
        ctx = _make_context(faction_id="commerce_guild")

        result = select_encounter_definition([defn], ctx)
        assert result is None

    def test_weighted_selection_respects_weights(self) -> None:
        """Higher weight encounters should be selected more often."""
        heavy = _make_definition(id="heavy", weight=100)
        light = _make_definition(id="light", weight=1)

        heavy_count = 0
        for seed in range(200):
            ctx = _make_context(seed=seed)
            result = select_encounter_definition([heavy, light], ctx)
            if result and result.id == "heavy":
                heavy_count += 1

        # With 100:1 weight ratio, heavy should dominate
        assert heavy_count > 150, f"Heavy selected {heavy_count}/200 times"


class TestSelectEncounterDefinitionBackwardCompat:
    """Tests for the old 4-arg signature."""

    def test_old_signature_still_works(self) -> None:
        defn = _make_definition()
        result = select_encounter_definition(
            [defn], "distress_signal", "moderate", 42
        )
        assert result is not None
        assert result.id == "test_enc"

    def test_old_signature_filters_by_type(self) -> None:
        defn = _make_definition(encounter_type="merchant")
        result = select_encounter_definition(
            [defn], "distress_signal", "moderate", 42
        )
        assert result is None

    def test_old_signature_filters_by_danger(self) -> None:
        defn = _make_definition(danger_levels=["dangerous"])
        result = select_encounter_definition(
            [defn], "distress_signal", "moderate", 42
        )
        assert result is None
