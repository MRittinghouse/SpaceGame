# Salvage System

## Overview
Grid-based scanning and extraction puzzle at industrial/frontier systems (Forgeworks, Crimson Reach).

## Mechanics

### Grid
- 5x5 grid (default) representing a derelict hull
- ~40% of cells contain salvageable items
- Items hidden until scanned

### Scanning
- Costs 1 scan charge to reveal a cell's contents
- Strategic: choose where to scan based on spatial reasoning
- Reveals: item type or "empty"

### Extraction
- Click scanned items to extract (takes time based on rarity)
- Only one extraction at a time
- Yields added to cargo on completion

### Item Types
| Type | Commodity | Extract Time | Yield |
|------|-----------|-------------|-------|
| Scrap Metal | scrap_metal | 1.0s | 1-3 |
| Electronics | salvaged_electronics | 2.0s | 1-2 |
| Rare Parts | rare_parts | 3.0s | 1 |

### Charge System
- 10 charges (default), regenerate 1 every 5 seconds
- Configurable per-system

### Skill Bonuses
- **Keen Scanner**: +1 scan charge per level
- **Master Extractor**: -20% extraction time per level

### Locations
- Forgeworks: 50% scrap, 35% electronics, 15% rare parts
- Crimson Reach: 30% scrap, 40% electronics, 30% rare parts (rarer finds)
