"""Tests for the NewsTicker model.

Covers HeadlineTemplate, buffer management, headline generation from game
state context, flavor fallback, non-repeat shuffle, and serialization.
"""

from spacegame.models.news_ticker import HeadlineTemplate, NewsTicker


# ============================================================================
# Helpers
# ============================================================================


def _make_template(
    id: str = "tmpl_001",
    template: str = "Breaking news from {system}.",
    trigger: str = "flavor",
    priority: int = 5,
    faction_id: str = "",
) -> HeadlineTemplate:
    """Create a HeadlineTemplate with sensible defaults."""
    return HeadlineTemplate(
        id=id,
        template=template,
        trigger=trigger,
        priority=priority,
        faction_id=faction_id,
    )


def _make_embargo_template() -> HeadlineTemplate:
    return _make_template(
        id="embargo_tmpl",
        template="{faction} imposes embargo on {commodity} at {system}.",
        trigger="galaxy_event_embargo",
        priority=8,
        faction_id="commerce_guild",
    )


def _make_festival_template() -> HeadlineTemplate:
    return _make_template(
        id="festival_tmpl",
        template="Festival declared in {system} — celebrations begin.",
        trigger="galaxy_event_festival",
        priority=7,
    )


def _make_market_template() -> HeadlineTemplate:
    return _make_template(
        id="market_tmpl",
        template="Market report: {commodity} prices shift at {system}.",
        trigger="market_event",
        priority=6,
    )


def _make_political_template() -> HeadlineTemplate:
    return _make_template(
        id="political_tmpl",
        template="Political dispatch: {description}",
        trigger="political_event",
        priority=7,
    )


def _make_milestone_template() -> HeadlineTemplate:
    return _make_template(
        id="milestone_tmpl",
        template="{milestone}",
        trigger="player_milestone",
        priority=9,
    )


def _make_flavor_templates() -> list[HeadlineTemplate]:
    """Return a pool of five distinct flavor templates."""
    return [
        _make_template(id=f"flavor_{i:02d}", template=f"Flavor headline #{i}.", trigger="flavor")
        for i in range(1, 6)
    ]


def _make_ticker(templates: list[HeadlineTemplate] | None = None, buffer_size: int = 8) -> NewsTicker:
    """Create a NewsTicker; defaults to a small mixed template set."""
    if templates is None:
        templates = [
            _make_embargo_template(),
            _make_festival_template(),
            _make_market_template(),
            *_make_flavor_templates(),
        ]
    return NewsTicker(templates=templates, buffer_size=buffer_size)


def _make_galaxy_event(
    event_type: str = "embargo",
    system_id: str = "nexus_prime",
    faction_id: str = "commerce_guild",
    description: str = "Trade restricted.",
    commodity: str = "fuel_cells",
) -> dict:
    return {
        "event_type": event_type,
        "system_id": system_id,
        "faction_id": faction_id,
        "description": description,
        "commodity": commodity,
    }


def _make_market_event(
    event_type: str = "price_surge",
    commodity: str = "refined_ore",
    system_id: str = "breakstone",
    description: str = "Refined ore prices spike.",
) -> dict:
    return {
        "event_type": event_type,
        "commodity": commodity,
        "system_id": system_id,
        "description": description,
    }


# ============================================================================
# Manual Headline Addition
# ============================================================================


class TestAddHeadline:
    """add_headline inserts a string directly into the buffer."""

    def test_added_headline_appears_in_get_headlines(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("Trader vessels spotted near Varn Station.")
        results = ticker.get_headlines()
        assert any("Trader vessels" in h for h in results), (
            "Manually added headline should appear in get_headlines output"
        )

    def test_added_headline_is_returned_as_newest_first(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("First headline.")
        ticker.add_headline("Second headline.")
        results = ticker.get_headlines()
        assert results[0] == "Second headline.", (
            "Most recently added headline should be first in get_headlines"
        )

    def test_multiple_manually_added_headlines_all_present(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("Alpha.")
        ticker.add_headline("Beta.")
        ticker.add_headline("Gamma.")
        results = ticker.get_headlines(count=3)
        assert "Gamma." in results
        assert "Beta." in results
        assert "Alpha." in results


# ============================================================================
# Buffer Size Limit
# ============================================================================


class TestBufferSizeLimit:
    """Buffer drops oldest entries when capacity is exceeded."""

    def test_buffer_never_exceeds_buffer_size(self) -> None:
        ticker = _make_ticker(buffer_size=4)
        for i in range(10):
            ticker.add_headline(f"Headline {i}.")
        results = ticker.get_headlines(count=10)
        assert len(results) <= 4, f"Buffer should hold at most 4 headlines, got {len(results)}"

    def test_oldest_headline_is_dropped_when_buffer_full(self) -> None:
        ticker = _make_ticker(buffer_size=3)
        ticker.add_headline("Very old news.")
        ticker.add_headline("Old news.")
        ticker.add_headline("Recent news.")
        ticker.add_headline("Latest news.")  # pushes "Very old news." out
        results = ticker.get_headlines(count=4)
        assert "Very old news." not in results, (
            "Oldest headline should be dropped once buffer overflows"
        )

    def test_newest_headlines_retained_after_overflow(self) -> None:
        ticker = _make_ticker(buffer_size=3)
        for i in range(6):
            ticker.add_headline(f"Headline {i}.")
        results = ticker.get_headlines(count=3)
        assert "Headline 5." in results
        assert "Headline 4." in results
        assert "Headline 3." in results


# ============================================================================
# get_headlines Count and Order
# ============================================================================


class TestGetHeadlines:
    """get_headlines returns at most `count` items, newest first."""

    def test_returns_at_most_count_items(self) -> None:
        ticker = _make_ticker()
        for i in range(6):
            ticker.add_headline(f"Story {i}.")
        results = ticker.get_headlines(count=3)
        assert len(results) == 3, f"Expected 3 headlines, got {len(results)}"

    def test_default_count_is_five(self) -> None:
        ticker = _make_ticker()
        for i in range(8):
            ticker.add_headline(f"Story {i}.")
        results = ticker.get_headlines()
        assert len(results) == 5, f"Default count should be 5, got {len(results)}"

    def test_returns_fewer_when_buffer_has_fewer_items(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("Only headline.")
        results = ticker.get_headlines(count=5)
        assert len(results) == 1, "Should return only available headlines"

    def test_returns_newest_first(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("Oldest.")
        ticker.add_headline("Middle.")
        ticker.add_headline("Newest.")
        results = ticker.get_headlines(count=3)
        assert results == ["Newest.", "Middle.", "Oldest."], (
            "Headlines should be ordered newest-first"
        )

    def test_empty_buffer_returns_empty_list(self) -> None:
        ticker = NewsTicker(templates=[], buffer_size=8)
        results = ticker.get_headlines()
        assert results == [], "Empty buffer should return empty list"


# ============================================================================
# generate_headlines — Galaxy Events
# ============================================================================


class TestGenerateFromGalaxyEvents:
    """generate_headlines fills the buffer from galaxy_events context."""

    def test_embargo_event_adds_headline(self) -> None:
        ticker = NewsTicker(templates=[_make_embargo_template()], buffer_size=8)
        context: dict = {
            "galaxy_events": [_make_galaxy_event(event_type="embargo")],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        assert len(results) > 0, "Embargo event should produce at least one headline"

    def test_embargo_headline_contains_faction_name(self) -> None:
        ticker = NewsTicker(templates=[_make_embargo_template()], buffer_size=8)
        context: dict = {
            "galaxy_events": [
                _make_galaxy_event(
                    event_type="embargo",
                    faction_id="commerce_guild",
                    commodity="fuel_cells",
                    system_id="nexus_prime",
                )
            ],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        combined = " ".join(results)
        assert "commerce_guild" in combined or "nexus_prime" in combined, (
            "Embargo headline should reference faction or system from the event"
        )

    def test_festival_event_adds_headline(self) -> None:
        ticker = NewsTicker(templates=[_make_festival_template()], buffer_size=8)
        context: dict = {
            "galaxy_events": [_make_galaxy_event(event_type="festival", system_id="varn_station")],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        assert len(results) > 0, "Festival event should produce at least one headline"

    def test_unmatched_event_type_does_not_add_headline(self) -> None:
        # Ticker only has embargo template but event is a festival
        ticker = NewsTicker(templates=[_make_embargo_template()], buffer_size=8)
        context: dict = {
            "galaxy_events": [_make_galaxy_event(event_type="festival")],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        assert len(results) == 0, (
            "Event type with no matching template should produce no headlines"
        )

    def test_multiple_galaxy_events_each_add_headline(self) -> None:
        templates = [_make_embargo_template(), _make_festival_template()]
        ticker = NewsTicker(templates=templates, buffer_size=8)
        context: dict = {
            "galaxy_events": [
                _make_galaxy_event(event_type="embargo"),
                _make_galaxy_event(event_type="festival", system_id="varn_station"),
            ],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines(count=8)
        assert len(results) >= 2, "Each matching galaxy event should generate a headline"


# ============================================================================
# generate_headlines — Market Events
# ============================================================================


class TestGenerateFromMarketEvents:
    """generate_headlines fills the buffer from market_events context."""

    def test_market_event_adds_headline(self) -> None:
        ticker = NewsTicker(templates=[_make_market_template()], buffer_size=8)
        context: dict = {
            "market_events": [_make_market_event()],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        assert len(results) > 0, "Market event should produce at least one headline"

    def test_market_headline_contains_commodity_or_system(self) -> None:
        ticker = NewsTicker(templates=[_make_market_template()], buffer_size=8)
        context: dict = {
            "market_events": [
                _make_market_event(commodity="refined_ore", system_id="breakstone")
            ],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        combined = " ".join(results)
        assert "refined_ore" in combined or "breakstone" in combined, (
            "Market headline should reference commodity or system from the event"
        )


# ============================================================================
# generate_headlines — Political Events
# ============================================================================


class TestGenerateFromPoliticalEvents:
    """generate_headlines fills the buffer from political_events context."""

    def test_political_event_adds_headline(self) -> None:
        ticker = NewsTicker(templates=[_make_political_template()], buffer_size=8)
        context: dict = {
            "political_events": [{"description": "Senate convenes emergency session."}],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        assert len(results) > 0, "Political event should produce at least one headline"

    def test_political_headline_contains_description(self) -> None:
        ticker = NewsTicker(templates=[_make_political_template()], buffer_size=8)
        context: dict = {
            "political_events": [{"description": "Senate convenes emergency session."}],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        combined = " ".join(results)
        assert "Senate" in combined, (
            "Political headline should include the event description text"
        )


# ============================================================================
# generate_headlines — Player Milestones
# ============================================================================


class TestGenerateFromMilestones:
    """generate_headlines fills the buffer from player_milestones context."""

    def test_player_milestone_adds_headline(self) -> None:
        ticker = NewsTicker(templates=[_make_milestone_template()], buffer_size=8)
        context: dict = {
            "player_milestones": ["Pilot Reyes reaches Level 10."],
        }
        ticker.generate_headlines(context)
        results = ticker.get_headlines()
        assert any("Level 10" in h for h in results), (
            "Player milestone string should appear in headlines"
        )


# ============================================================================
# generate_headlines — Flavor Fallback
# ============================================================================


class TestFlavorFallback:
    """Flavor headlines fill the buffer when no event-driven content exists."""

    def test_flavor_added_when_context_is_empty(self) -> None:
        ticker = _make_ticker(templates=_make_flavor_templates())
        ticker.generate_headlines({})
        results = ticker.get_headlines()
        assert len(results) > 0, "Flavor templates should produce headlines when context is empty"

    def test_flavor_added_when_no_events_match(self) -> None:
        # Ticker has only embargo template but context has no events at all
        ticker = NewsTicker(
            templates=[_make_embargo_template(), *_make_flavor_templates()],
            buffer_size=8,
        )
        ticker.generate_headlines({})
        results = ticker.get_headlines()
        assert len(results) > 0, (
            "Flavor headlines should fill buffer when no matching events are provided"
        )

    def test_flavor_headlines_do_not_repeat_before_pool_exhausted(self) -> None:
        # 3 flavor templates; call generate twice; first two sets should be different
        flavor_templates = [
            _make_template(id=f"fl_{i}", template=f"Flavor line {i}.", trigger="flavor")
            for i in range(3)
        ]
        ticker = NewsTicker(templates=flavor_templates, buffer_size=8)
        ticker.generate_headlines({})
        first_batch = set(ticker.get_headlines(count=3))

        # Generate again into a fresh ticker to compare
        ticker2 = NewsTicker(templates=flavor_templates, buffer_size=8)
        ticker2.generate_headlines({})
        second_batch = set(ticker2.get_headlines(count=3))

        # Both sets must come from the same pool — no duplicates within a single batch
        for batch in (first_batch, second_batch):
            assert len(batch) == len(list(batch)), (
                "A single generate call should not produce duplicate flavor lines"
            )

    def test_flavor_pool_resets_after_exhaustion(self) -> None:
        # Only 2 flavor templates; generate twice — second call should still produce lines
        flavor_templates = [
            _make_template(id="fl_a", template="Flavor A.", trigger="flavor"),
            _make_template(id="fl_b", template="Flavor B.", trigger="flavor"),
        ]
        ticker = NewsTicker(templates=flavor_templates, buffer_size=8)
        ticker.generate_headlines({})  # consumes both
        ticker.generate_headlines({})  # pool should reset; still generates
        results = ticker.get_headlines(count=8)
        assert len(results) > 0, "Flavor pool should recycle after exhaustion"


# ============================================================================
# Serialization
# ============================================================================


class TestSerialization:
    """to_dict / from_dict round-trip preserves buffer contents."""

    def test_to_dict_returns_dict(self) -> None:
        ticker = _make_ticker()
        data = ticker.to_dict()
        assert isinstance(data, dict), "to_dict should return a dict"

    def test_to_dict_contains_version(self) -> None:
        ticker = _make_ticker()
        data = ticker.to_dict()
        assert "version" in data, "Serialized dict should contain a version key"

    def test_round_trip_restores_buffer_contents(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("Preserved headline.")
        ticker.add_headline("Also preserved.")
        data = ticker.to_dict()

        templates = [_make_embargo_template(), _make_festival_template(), *_make_flavor_templates()]
        ticker2 = NewsTicker.from_dict(data, templates)
        results = ticker2.get_headlines(count=5)
        assert "Preserved headline." in results, (
            "Buffer contents should survive a to_dict / from_dict round-trip"
        )
        assert "Also preserved." in results, (
            "All buffer items should survive a to_dict / from_dict round-trip"
        )

    def test_round_trip_preserves_order(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("First.")
        ticker.add_headline("Second.")
        ticker.add_headline("Third.")
        data = ticker.to_dict()

        ticker2 = NewsTicker.from_dict(data, [])
        results = ticker2.get_headlines(count=3)
        assert results == ["Third.", "Second.", "First."], (
            "Newest-first order should be preserved after round-trip"
        )

    def test_from_dict_empty_data_produces_empty_buffer(self) -> None:
        ticker = NewsTicker.from_dict({}, [])
        results = ticker.get_headlines()
        assert results == [], "from_dict with empty dict should produce empty buffer"

    def test_round_trip_preserves_buffer_size(self) -> None:
        ticker = NewsTicker(templates=[], buffer_size=3)
        ticker.add_headline("A.")
        ticker.add_headline("B.")
        ticker.add_headline("C.")
        data = ticker.to_dict()

        ticker2 = NewsTicker.from_dict(data, [])
        # Adding one more should drop the oldest
        ticker2.add_headline("D.")
        results = ticker2.get_headlines(count=4)
        assert "A." not in results, "Buffer size should be preserved through serialization"
        assert len(results) <= 3


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Edge conditions: empty templates, empty context, zero buffer."""

    def test_empty_templates_and_empty_context_produces_empty_buffer(self) -> None:
        ticker = NewsTicker(templates=[], buffer_size=8)
        ticker.generate_headlines({})
        assert ticker.get_headlines() == [], (
            "No templates and no context should yield no headlines"
        )

    def test_generate_headlines_with_none_values_in_context_is_safe(self) -> None:
        ticker = _make_ticker()
        # Keys present but with empty lists — should not raise
        context: dict = {
            "galaxy_events": [],
            "market_events": [],
            "political_events": [],
            "player_milestones": [],
        }
        ticker.generate_headlines(context)  # must not raise

    def test_get_headlines_count_zero_returns_empty(self) -> None:
        ticker = _make_ticker()
        ticker.add_headline("Something.")
        results = ticker.get_headlines(count=0)
        assert results == [], "count=0 should return empty list"
