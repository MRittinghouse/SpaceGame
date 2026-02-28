# Mining System

## Overview
Asteroid field mini-game available at mining-type systems (Breakstone, Iron Depths).

## Mechanics

### Rock Types
| Type | Hardness | Yield | Commodity | Color |
|------|----------|-------|-----------|-------|
| Common | 0.5s | 1-3 | Raw Ore | Brown |
| Iron | 1.0s | 1-3 | Iron Ore | Red-brown |
| Crystal | 2.0s | 1-2 | Crystal Ore | Blue |
| Rare | 3.0s | 1-2 | Rare Ore | Purple |

### Energy System
- 20 charges (default), 1 consumed per drill action
- Regenerates 1 charge every 3 seconds
- Configurable per-system via `mining_configs.json`

### Grid
- Default 6x4 grid of rocks
- Rock types distributed randomly per config weights
- Can regenerate field when depleted

### Skill Bonuses
- **Efficient Drills**: -15% drill time per level
- **Rich Veins**: +25% rare ore chance per level (applied to rock distribution)

### Balance
- Breakstone: 50% common, 30% iron, 15% crystal, 5% rare
- Iron Depths: 20% common, 40% iron, 25% crystal, 15% rare (harder, more rewarding)
