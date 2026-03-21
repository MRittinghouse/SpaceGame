# Journal System Design

## Overview

The journal is a **player-facing narrative log** that tracks key story events and allows the player to write their own notes. It serves two purposes:

1. **Reference** — auto-generated factual entries remind the player what happened, without interpreting it for them
2. **Expression** — player-written entries let them record suspicions, theories, goals, and observations in their own words

The journal is **not a quest tracker**. It doesn't tell you where to go or what to do. The Mission Log handles objectives. The journal handles meaning.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auto-entry tone | Factual/neutral (ship's log) | Doesn't put words in the player's mouth; provides facts to interpret |
| Player entries | Freeform text + optional tags | Maximum expression with light structure for filtering |
| Organization | Chronological | Mirrors a real journal; simple to scan |
| Auto-entry frequency | Key story beats only | ~20-25 auto-entries in Act One; sparse and meaningful |
| Player entry editing | Edit and delete freely | Player has full control over their own content |
| Access | Galaxy map button + pause menu | Always reachable without breaking flow |
| Tags | People, Places, Suspicions, Goals | Narrative-relevant categories; "Suspicions" encourages theorizing |

---

## Data Model

### JournalEntry

```python
@dataclass
class JournalEntry:
    """A single journal entry — either auto-generated or player-written."""
    entry_id: str           # Unique ID (auto: "auto_<mission_id>_<beat>", player: "player_<timestamp>")
    text: str               # Entry content
    game_day: int           # In-game day when entry was created
    system_id: str          # System the player was in when entry was created
    source: str = "auto"    # "auto" or "player"
    tag: str = ""           # "people", "places", "suspicions", "goals", or "" (none)
    mission_id: str = ""    # Which mission triggered this (auto entries only)
    created_at: int = 0     # Monotonic counter for stable sort order within a day
```

**Auto entries** are created by the game engine at story beats. They cannot be edited or deleted by the player.

**Player entries** are created by the player via the journal UI. They can be freely edited and deleted.

### Journal

```python
@dataclass
class Journal:
    """The player's complete journal."""
    entries: list[JournalEntry] = field(default_factory=list)
    _next_id: int = 0       # Counter for player entry IDs

    def add_auto_entry(self, entry_id: str, text: str, game_day: int,
                       system_id: str, mission_id: str = "") -> JournalEntry: ...
    def add_player_entry(self, text: str, game_day: int, system_id: str,
                         tag: str = "") -> JournalEntry: ...
    def edit_player_entry(self, entry_id: str, new_text: str,
                          new_tag: str = "") -> tuple[bool, str]: ...
    def delete_player_entry(self, entry_id: str) -> tuple[bool, str]: ...
    def get_entries(self, tag_filter: str = "",
                    source_filter: str = "") -> list[JournalEntry]: ...
    def get_entry(self, entry_id: str) -> Optional[JournalEntry]: ...
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Journal": ...
```

**Key behaviors:**
- `add_auto_entry()` prevents duplicates — if `entry_id` already exists, it's a no-op (idempotent)
- `edit_player_entry()` and `delete_player_entry()` refuse to modify auto entries → `(False, "Cannot modify auto entries")`
- `get_entries()` returns entries in chronological order (by `game_day`, then `created_at`)
- Tag filter: `""` returns all entries; `"people"` returns only entries tagged "people"
- Source filter: `""` returns all; `"auto"` or `"player"` filters by source

### Serialization

Journal serializes as part of the Player save chain:

```
SaveManager → Player.to_dict() → Journal.to_dict()
                                → list of JournalEntry dicts
```

Backward compatibility: if `journal` key is missing from save data, create an empty Journal.

---

## Auto-Entry Triggers

Auto entries fire at **key story beats only** — approximately one per mission, sometimes zero for simpler missions, occasionally two for missions with major branching.

### Act One Auto-Entry Map

| Mission | Entry ID | Trigger | Text |
|---------|----------|---------|------|
| M01 | `auto_m01_permit` | Bill of landing acquired | "Acquired bill of landing at Nexus Prime. 250 credits for the privilege of trading. Officer Larsen warned about dangerous systems and unarmed travel." |
| M02 | `auto_m02_delivery` | Iron ore delivered to Forgeworks | "Delivered 10 units of iron ore to Forgeworks for the cargo broker. 500 credits earned. First completed contract." |
| M03 | `auto_m03_elena` | Elena conversation complete | "Met Elena Reeves at Nexus Prime. Freelance navigator, ex-Commerce Guild. Offered to optimize routes in exchange for a berth." |
| M04 | `auto_m04_breakstone` | Breakstone permit earned | "Earned trade access at Breakstone by delivering food to the miners' commissary. Hanna Voss — dock boss — judges people by what they do, not what they say." |
| M05 | `auto_m05_marcus` | Marcus dialogue complete | "Met Marcus Jin at Breakstone. Mining foreman, twenty years on station. He filed an engineering report about the air recyclers on the Nexus Prime orbital. The report was buried. My father died six months later." |
| M06 | `auto_m06_priya` | Priya delivered to Axiom Labs | "Transported Dr. Priya Osei to Axiom Labs with research samples. She studies resource extraction economics. Described working conditions as data. Axiom Labs is clinical, precise — a different world from Breakstone." |
| M07 | `auto_m07_tomas` | Tomas deal resolved | "Met Tomas Drifter at Haven's Rest. [Accepted/Declined] a gray-market trade — rerouting supplies past Guild tariffs to people who need them. Haven's Rest runs on handshakes and trust." |
| M08 | `auto_m08_distress` | Distress signal encounter resolved | "[Helped/Ignored] a freighter under pirate attack. Met Captain Reva Sato, Guild military escort. Three convoy attacks this month — same pattern. Someone knows the patrol routes." |
| M09 | `auto_m09_dex` | Dex conversation complete | "Dex Halloran, information broker, approached at Nexus Prime cantina. Offered intel on the pirate attacks in exchange for a delivery to Crimson Reach. No questions asked." |
| M10 | `auto_m10_crimson` | Data chip delivered to Malia | "Delivered Dex's package to Malia Torres at Crimson Reach. She says whoever is backing the pirates has serious resources — real money, real ships, real intelligence. This isn't random raiding." |
| M11 | `auto_m11_summit` | Summit concludes | "Attended faction summit at Axiom Labs. All four factions present. No agreement reached — Guild wants military response, Union wants economic solidarity, Collective wants data, Alliance wants independence. Deadlock." |
| M12 | `auto_m12_attack` | Combat encounter survived | "Pirate ambush during travel. Survived. [If Marcus present: Marcus identified Guild-standard hardware on the pirate vessel. Guild ships, attacking Guild convoys.]" |
| M13 | `auto_m13_oren` | Oren reveals base location | "Found Oren Tak in Breakstone's mining tunnels. Retired miner, paranoid — justifiably. He's seen unmarked ships docking at a hidden facility near Iron Depths. Guild-class hulls." |
| M14 | `auto_m14_scan` | Base scan complete | "Located the pirate command base near Iron Depths. [If Priya present: Priya modified the scanner for long-range detection.] Hard evidence — this is real." |
| M15 | `auto_m15_decision` | Faction path chosen | "Presented evidence to faction leaders. Chose to work with [faction name] for the operation against the pirate base. [Brief reason based on faction approach.]" |
| M16 | `auto_m16_ledger` | The Ledger discovered | "The pirate operation is funded by a rogue faction within the Commerce Guild. They call themselves The Ledger. Goal: destabilize shipping, monopolize security, control the Expanse. Evidence recovered. Base neutralized. Leaders escaped." |
| M17 | `auto_m17_horizon` | Act One complete | "Act One concluded. The Ledger is exposed but not destroyed. Uncharted coordinates recovered from the base — more operations beyond the Expanse's borders. The factions are talking. It's a start." |

**Total auto entries**: 17 (one per mission). Some have conditional text based on player choices or crew presence.

---

## Player Entry Interface

### Creating an Entry

1. Player opens journal (galaxy map button or pause menu)
2. Taps "New Entry" button
3. Text input field appears (multi-line, max ~500 characters)
4. Optional: select a tag from 4 buttons (People / Places / Suspicions / Goals)
5. Confirm to save, or cancel to discard

### Editing an Entry

1. Player selects their own entry in the journal list
2. Taps "Edit" button (only visible on player entries)
3. Text field becomes editable, tag can be changed
4. Confirm to save changes, or cancel

### Deleting an Entry

1. Player selects their own entry
2. Taps "Delete" button (only visible on player entries)
3. Confirmation prompt: "Delete this entry?"
4. Entry is permanently removed

### Visual Distinction

| Element | Auto Entries | Player Entries |
|---------|-------------|----------------|
| Background | Subtle dark tint (system-generated feel) | Slightly warmer tint (personal feel) |
| Icon | Small terminal/log icon | Small pen/quill icon |
| Controls | None (read-only) | Edit, Delete buttons |
| Header | "Day X — [System Name]" | "Day X — [System Name] — [Tag]" |
| Text style | Standard font | Same font (player entries aren't visually lesser) |

---

## Journal View

### Layout

```
┌──────────────────────────────────────────────────────┐
│  JOURNAL                                    [Close]  │
├──────────────────────────────────────────────────────┤
│  [New Entry]                                         │
│  Filter: [All] [People] [Places] [Suspicions] [Goals]│
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Day 47 — Nexus Prime ────────── [auto] ──────┐  │
│  │ Met Elena Reeves at Nexus Prime. Freelance     │  │
│  │ navigator, ex-Commerce Guild. Offered to       │  │
│  │ optimize routes in exchange for a berth.       │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ Day 47 — Nexus Prime ─── [Suspicions] ── ✎ ✕ ┐  │
│  │ Elena left the Guild but still folds her       │  │
│  │ shirts in regulation creases. What happened    │  │
│  │ that made her leave?                           │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ Day 52 — Breakstone ─────────── [auto] ──────┐  │
│  │ Earned trade access at Breakstone by           │  │
│  │ delivering food to the miners' commissary...   │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  (scrollable)                                        │
└──────────────────────────────────────────────────────┘
```

### Controls

- **New Entry** button: opens text input panel
- **Filter buttons**: toggle tag filter (All shows everything, tag buttons show matching + all auto entries, or only matching tag)
- **Entry cards**: scrollable list, newest at top
- **Edit (✎)** and **Delete (✕)**: only on player entries
- **Close**: return to previous view

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Escape | Close journal |
| N | New entry |
| Tab | Cycle tag filter |
| Up/Down | Scroll entries |

---

## Integration Points

### Game Engine (game.py)

```python
# Add journal auto-entry when mission reaches a story beat
def _add_journal_entry(self, entry_id: str, text: str, mission_id: str = "") -> None:
    """Add an auto journal entry at the current game state."""
    self.player.journal.add_auto_entry(
        entry_id=entry_id,
        text=text,
        game_day=self.player.game_day,
        system_id=self.player.current_system,
        mission_id=mission_id,
    )
```

Auto entries are triggered from:
- `check_missions()` — when a mission completes or hits a key objective
- Dialogue `set_flag` actions — some flags also trigger a journal entry
- Specific story events (distress signal, summit, etc.)

### Galaxy Map View

Add "Journal" button to the galaxy map button bar (8th button, alongside Missions, Character, Crew, etc.).

### Pause Menu

Add "Journal" option to pause overlay. Opens JournalView with `return_state` set to resume current view.

### Save/Load

Journal serializes inside Player:
```python
# Player.to_dict()
"journal": self.journal.to_dict()

# Player.from_dict()
journal=Journal.from_dict(data.get("journal", {}))
```

### Notification

When an auto entry is added, display a brief notification on the galaxy map: *"Journal updated"* — subtle, non-intrusive, dismisses after 3 seconds.

---

## Tag Filtering Behavior

| Filter Selected | Shows |
|----------------|-------|
| All | Every entry (auto + player), chronological |
| People | Player entries tagged "people" + auto entries mentioning NPCs |
| Places | Player entries tagged "places" + auto entries mentioning locations |
| Suspicions | Player entries tagged "suspicions" only |
| Goals | Player entries tagged "goals" only |

**Note**: Auto entries don't have tags. Under "People" and "Places" filters, auto entries could optionally be shown based on content (contains NPC name or system name). Simpler alternative: tag filters only apply to player entries; auto entries always show unless a tag filter is active. This avoids complex auto-tagging logic.

**Recommended**: Tag filters apply to player entries only. When a tag filter is active, auto entries are hidden. "All" shows everything. This is simplest to implement and makes tags feel like the player's own organizational tool.

---

## File Locations

| Component | File |
|-----------|------|
| Model | `spacegame/models/journal.py` |
| View | `spacegame/views/journal_view.py` |
| Tests | `tests/test_models/test_journal.py` |
| Integration | `spacegame/engine/game.py` (auto-entry triggers) |
| Data | Auto-entry text lives in mission JSON or a dedicated `data/journal/entries.json` |

---

## Resolved Design Questions

| Question | Decision |
|----------|----------|
| Auto-entry text storage | **Separate JSON file** (`data/journal/entries.json`). Clean separation from mission definitions. |
| Tag filter behavior | **Hide auto entries** when a tag filter is active. Tags are the player's tool. "All" shows everything. |
| Player entry length | **500 characters**. ~3-4 sentences. Encourages concise notes. |
| Quick-add from other views | **Yes**. Small "Add Note" button or keyboard shortcut (J) available from multiple views. Opens a lightweight overlay panel for quick entry, not the full journal view. |

---

## Quick-Add Overlay

A lightweight note-entry panel that can appear over any view without leaving it.

### Trigger
- **Keyboard**: Press `J` from any view that supports it (galaxy map, trading, dialogue post-conversation, combat outcome)
- **Button**: Small journal icon button in the corner of supported views

### Layout
```
┌─────────────────────────────────┐
│  Quick Note            [Cancel] │
├─────────────────────────────────┤
│  ┌─────────────────────────── ┐ │
│  │ (text input, 500 chars)   │ │
│  │                           │ │
│  └─────────────────────────── ┘ │
│  Tag: [None] [People] [Places]  │
│       [Suspicions] [Goals]      │
│                       [Save]    │
└─────────────────────────────────┘
```

### Behavior
- Opens as a modal overlay — underlying view is dimmed but not destroyed
- Text field auto-focuses
- Tag selection is optional (default: none)
- Save creates a player entry with current game_day and system_id, then closes overlay
- Cancel (or Escape) discards and closes
- The overlay does NOT need the full journal scroll list — it's just for writing

### Views That Support Quick-Add
- Galaxy map (always)
- Trading view (between transactions)
- Dialogue view (after conversation ends, before returning)
- Combat outcome screen (after battle results shown)
- Mission log view
- Crew roster view
- Character screen

Views that do NOT support quick-add (too transient or input-heavy):
- Active combat (player input phase)
- Travel animation
- Name input / character creation
- Main menu

---

## Auto-Entry JSON Format

File: `data/journal/entries.json`

```json
{
  "journal_entries": [
    {
      "entry_id": "auto_m01_permit",
      "mission_id": "m01_bill_of_landing",
      "trigger_flag": "nexus_prime_permit",
      "text": "Acquired bill of landing at Nexus Prime. 250 credits for the privilege of trading. Officer Larsen warned about dangerous systems and unarmed travel."
    },
    {
      "entry_id": "auto_m07_tomas_accepted",
      "mission_id": "m07_drifters_deal",
      "trigger_flag": "accepted_drifter_deal",
      "text": "Met Tomas Drifter at Haven's Rest. Accepted a gray-market trade — rerouting supplies past Guild tariffs to people who need them. Haven's Rest runs on handshakes and trust."
    },
    {
      "entry_id": "auto_m07_tomas_declined",
      "mission_id": "m07_drifters_deal",
      "trigger_flag": "declined_drifter_deal",
      "text": "Met Tomas Drifter at Haven's Rest. Declined his gray-market offer. The rules exist for a reason — even if the reason isn't always fair."
    }
  ]
}
```

**Conditional entries**: Entries with different `trigger_flag` values handle branching. When a flag is set, the game engine checks if any journal entry should fire for that flag. Only one entry per `entry_id` prefix fires (first match wins for entries sharing a mission).

**DataLoader integration**: `load_all()` loads journal entries. Game engine checks pending entries when flags change.
