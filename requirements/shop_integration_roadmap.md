# Shop Integration & Shopping List Roadmap

> **Status**: PLANNING
> **Created**: 2026-03-26
> **Context**: Playtesting revealed significant friction in the Drydock -> Shop -> Loadout
> flow. Each tab operates as an island. The Shop doesn't know what the player built,
> the Loadout doesn't guide the player back to the Shop. This roadmap tightens the
> integration so the flow feels unified and guided.

---

## Design Philosophy

The player built their dream ship. Now they need to equip it. The game should
make this feel like **checking off a list**, not **wandering through a warehouse**.

Every screen should answer: "What do I need? Where do I get it? How close am I?"

---

## Phase SI1: Sub-Tab Need Badges

> **Impact**: HIGH — immediately shows which categories need attention
> **Effort**: LOW — count empty slots per type, render badge on sub-tab buttons

### What It Does
Each Shop sub-tab button shows a badge with the number of empty (unequipped)
slots of that type. "Weapons (4)" means 4 weapon slots need parts.

### Behavior
- Badge appears as a small colored number next to the sub-tab label
- Red when slots are empty, disappears when all slots are equipped
- Updates live when parts are bought (if bought part auto-fills a need)
- Frames tab never has a badge (frames aren't slot-based)

### Data Source
```python
# Count empty slots per type from placed_slots
for ps in build.placed_slots:
    if not ps.equipped_part_id:
        empty_counts[slot_type] += 1
```

---

## Phase SI2: Shopping List Header

> **Impact**: HIGH — tells the player exactly what they need when browsing parts
> **Effort**: LOW-MEDIUM — render header above the parts list

### What It Does
When the player opens a parts sub-tab (e.g., Weapons), a header above the list shows:

```
YOUR SHIP NEEDS: 4 Weapons (2 Small, 2 Large)
You own: 0 | Budget: 515,310 CR
```

### Details
- Counts empty slots by size for the active sub-tab category
- Shows how many compatible parts the player already owns in inventory
- Shows remaining budget (credits)
- When all slots are filled: "All weapon slots equipped!" in green
- Sizes shown help the player buy the RIGHT size parts

### Stretch: Recommended Parts
Below the needs header, optionally highlight "best value" parts:
- Cheapest part that fits each empty slot size
- Most cost-effective (damage per credit for weapons, capacity per credit for cargo)

---

## Phase SI3: Loadout Empty Slot Guidance

> **Impact**: MEDIUM — reduces back-and-forth between tabs
> **Effort**: LOW — add contextual text to the Loadout compatible parts panel

### What It Does
When the player clicks an empty slot in the Loadout tab and has no compatible
parts in inventory, instead of showing an empty list, show:

```
No compatible parts in inventory.

Visit Shop > Weapons to buy parts for this slot.
This is a Large Weapon slot — buy a Medium or Large weapon.
```

### Behavior
- Only shown when the compatible parts list is empty
- Names the specific Shop sub-tab to visit
- Specifies the slot size so the player knows what to buy
- Could include a "Go to Shop" button that switches to the Shop tab
  and selects the right sub-tab automatically

---

## Phase SI4: Post-Drydock Shop Prompt

> **Impact**: MEDIUM — guides the player immediately after building
> **Effort**: LOW — show a one-time prompt when entering Shop after Drydock

### What It Does
When the player confirms a build in the Drydock and arrives at the Shop tab
(or Shipyard), show a brief guidance banner:

```
Build confirmed! Your ship has 28 empty slots.
Browse the Shop tabs to buy parts, then equip them in Loadout.
```

### Behavior
- One-time banner, dismissable
- Shows total empty slot count
- Disappears after the player buys their first part (they understand the flow)
- Only appears after a Drydock confirm, not on every Shop visit

---

## Phase SI5: Quick-Equip from Shop

> **Impact**: MEDIUM-HIGH — reduces the Shop->Loadout->Shop ping-pong
> **Effort**: MEDIUM — requires equip logic in the Shop context

### What It Does
When buying a part in the Shop, if the player has an empty compatible slot,
offer to equip it immediately:

```
Bought Plasma Torpedo for 30,000 CR.
[Equip Now] [Add to Inventory]
```

### Behavior
- "Equip Now" assigns the part to the first compatible empty slot
- "Add to Inventory" stores it for manual assignment in Loadout
- Only offered when there's exactly one best-fit slot (avoid ambiguity)
- If multiple compatible slots exist, goes to inventory (player chooses in Loadout)
- Updates the sub-tab badge count immediately

---

## Phase SI6: Auto-Equip All (Stretch)

> **Impact**: MEDIUM — convenience for players who don't want to manually assign
> **Effort**: MEDIUM — requires matching algorithm

### What It Does
A button in the Loadout tab: "AUTO-EQUIP ALL"

Automatically assigns all unequipped inventory parts to compatible empty slots,
prioritizing: largest parts to largest slots, then by cost (most expensive first).

### Behavior
- Only assigns parts the player already owns (doesn't buy)
- Shows a summary: "Equipped 12 parts. 4 slots remain empty."
- Can be undone (one bulk undo)
- Skips slots that have multiple compatible parts (ambiguous — let player choose)

---

## Implementation Order

| Phase | What | Priority | Effort |
|-------|------|----------|--------|
| **SI1** | Sub-tab need badges | URGENT | Low |
| **SI2** | Shopping list header | URGENT | Low-Medium |
| **SI3** | Loadout empty slot guidance | HIGH | Low |
| **SI4** | Post-Drydock shop prompt | MEDIUM | Low |
| **SI5** | Quick-equip from Shop | MEDIUM | Medium |
| **SI6** | Auto-equip all | STRETCH | Medium |

Recommended: SI1 + SI2 together (one implementation pass), then SI3, then SI4.
SI5 and SI6 are quality-of-life stretch goals.

---

## Success Criteria

After implementing SI1-SI4, a new player should be able to:
1. Build a ship in the Drydock
2. See exactly what parts they need in the Shop (badges + header)
3. Buy parts with confidence (right sizes, right quantities)
4. Equip all parts in the Loadout without going back to the Shop
5. Complete the full Drydock->Shop->Loadout flow in under 5 minutes

The flow should feel like: "I know what I need, I know where to get it, I'm done."
