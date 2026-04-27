# Sub-Reputation System Design

**Sprint**: SA-B-EXT-1  
**Status**: Locked (ready for consumer sprints)

Resolves the open question at `requirements/station_anchors.md` line 253 (save-chain reuse).

---

## What Sub-Reputation Is (and Isn't)

Sub-reputation tracks a player's standing within a specific **organization** (Wreckers' Guild,
Stellaris Auctioneer relationship, etc.) independently of the faction that controls the local
star system.

- **Is**: per-organization progression points that unlock tiers (apprentice, journeyman, master;
  or bidder, preferred, elite; etc.)
- **Is not**: a parallel faction system. Faction reputation and sub-reputation are orthogonal.
  Modifying one does not affect the other.
- **Is not**: a lockout mechanism. Lockouts (e.g. Wreckers' failed-contract bans) live on a
  separate time-windowed field (e.g. `wreckers_guild_state["lockout_until_day"]`) owned by the
  consumer sprint. Sub-rep is membership progression, not a ban toggle.
- **Is not**: automatically tied to faction-rep gain. Consumer sprints decide when to award
  sub-rep (contract completion, bids won, etc.).

---

## Model Shape

```python
@dataclass(frozen=True)
class OrganizationTier:
    id: str           # snake_case stable identifier
    name: str         # Display name
    rank: int         # Ordering: higher rank = higher tier
    min_rep: int      # Minimum sub-rep value to be in this tier

@dataclass(frozen=True)
class OrganizationConfig:
    id: str
    name: str
    tiers: tuple[OrganizationTier, ...]  # Ascending by rank and min_rep
    min_rep: int = 0    # Clamp floor (default 0 — no negatives in v1)
    max_rep: int = 100  # Clamp ceiling

@dataclass(frozen=True)
class SubReputationDelta:
    org_id: str
    effective_amount: int   # Actual delta after clamping
    old_tier: OrganizationTier
    new_tier: OrganizationTier
```

`OrganizationTier` supports `>=` / `<` comparison by `rank` so consumer code can write
`current_tier >= JOURNEYMAN_TIER` without reaching into `.rank`.

---

## Registry Pattern

SA-B-EXT-1 ships **zero concrete configs**. Consumer sprints own their own configs:

| Consumer sprint | File | Config name |
|---|---|---|
| SA-1 (Wreckers' Guild Hall) | `spacegame/models/wreckers_guild.py` | `WRECKERS_GUILD_CONFIG` |
| SA-B3 (Stellaris Auction) | `spacegame/models/bidding.py` | `STELLARIS_AUCTIONEER_CONFIG` |
| SA-B4 (Crimson Reach auctions) | reuses SA-1's config | — |

No global registry dict is needed. Consumers import the config directly. The `Player` helpers
accept a config as a parameter so they work with any config without any central lookup.

---

## Range and Clamping Rules

- Default range: `[0, 100]`. Override via `OrganizationConfig.min_rep` / `max_rep`.
- Consumers wanting negative ranges (e.g. "blacklisted bidder") set `min_rep = -50`.
- `Player.modify_sub_reputation` clamps to `[config.min_rep, config.max_rep]`. The effective
  delta (after clamping) is what's reported in the return message and stored in the delta.
- Clamping at the ceiling does not queue a `SubReputationDelta` unless the tier actually changes.

---

## Notification Queue Contract

```python
# On Player (not serialized, ephemeral UI state):
_pending_sub_rep_deltas: list[SubReputationDelta]
```

- Lazily initialized (not a dataclass field). Mirrors `_pending_faction_deltas`.
- Populated by `modify_sub_reputation` whenever a tier threshold is crossed.
- Drained per-frame by consumer views (same drain pattern as `engine/game.py:5386`).
- **NOT serialized.** The queue is ephemeral; a round-trip drops it.

Consumer views drain with:
```python
deltas = getattr(player, "_pending_sub_rep_deltas", [])
player._pending_sub_rep_deltas = []
for delta in deltas:
    # show tier-up/tier-down notification
```

---

## Save Chain Reuse

Reuses the existing `Player` serialization chain. No separate save manager.

**Serialization** (in `save_manager._player_to_dict`):
```python
"sub_reputation": player.sub_reputation,  # dict[str, int]
```
Written next to `"faction_reputation"`.

**Deserialization** (in `save_manager._player_from_dict`):
```python
player.sub_reputation = data.get("sub_reputation", {})
```
Default `{}` ensures legacy saves load without crash.

**Why Player chain**: zero migration risk; matches `faction_reputation`'s precedent exactly;
consumers don't need to learn a new save mechanism.

---

## Default-Tier Semantics

- `Player.get_sub_reputation(org_id)` returns `0` when the org is absent.
- `Player.get_sub_reputation_tier(org_id, config)` returns the **lowest** tier (the one with
  the smallest `min_rep` still <= 0).
- **Consumer responsibility**: distinguish "player enrolled" from "player's current standing"
  via their own state (e.g. `wreckers_guild_state["enrolled"]`). Sub-rep does not track
  membership — only standing once a player is in the system.

---

## Illustrative Configurations (Owned by Consumer Sprints)

These shapes are shown here for design clarity. They are **not implemented in SA-B-EXT-1**.
Consumer sprints own the authoritative tier names and thresholds.

### Wreckers' Guild (SA-1 owns this)

```python
WRECKERS_GUILD_CONFIG = OrganizationConfig(
    id="wreckers_guild",
    name="Wreckers' Guild",
    tiers=(
        OrganizationTier(id="apprentice", name="Apprentice", rank=1, min_rep=0),
        OrganizationTier(id="journeyman", name="Journeyman", rank=2, min_rep=30),
        OrganizationTier(id="master",     name="Master",     rank=3, min_rep=70),
    ),
    min_rep=0,
    max_rep=100,
)
```

### Stellaris Auctioneer (SA-B3 owns this)

```python
STELLARIS_AUCTIONEER_CONFIG = OrganizationConfig(
    id="stellaris_auctioneer",
    name="Stellaris Auctioneer",
    tiers=(
        OrganizationTier(id="registered",  name="Registered",  rank=1, min_rep=0),
        OrganizationTier(id="preferred",   name="Preferred",   rank=2, min_rep=25),
        OrganizationTier(id="trusted",     name="Trusted",     rank=3, min_rep=55),
        OrganizationTier(id="elite",       name="Elite",       rank=4, min_rep=80),
    ),
    min_rep=0,
    max_rep=100,
)
```
