# Refining System

## Overview
Process raw materials into valuable goods through queue-based crafting.

## Recipes

| Recipe | Input | Output | Time | Location |
|--------|-------|--------|------|----------|
| Smelt Iron | 10 raw_ore | 2 common_metals | 5s | Forgeworks, Iron Depths |
| Refine Iron Ore | 6 iron_ore | 3 common_metals | 6s | Forgeworks, Iron Depths |
| Refine Crystal | 5 crystal_ore | 1 rare_metals | 8s | Axiom Labs, Nova Research |
| Process Electronics | 3 rare_metals + 2 common_metals | 2 electronics | 12s | Axiom Labs, Nova Research |
| Craft Medical* | 2 crystal_ore + 1 electronics | 1 medical | 15s | Axiom Labs, Nova Research |
| Process Scrap | 8 scrap_metal | 1 common_metals | 4s | Forgeworks |

*Requires Refining Knowledge skill

## Queue System
- Up to 5 jobs can queue simultaneously
- Jobs process in real-time with progress bars
- Outputs automatically added to cargo on completion
- Jobs continue processing while you browse recipes

## Resource Flow
```
Raw Ore -----> Common Metals -----> Electronics
Iron Ore --/                   |
Crystal Ore -> Rare Metals ---/+--> Medical Supplies
Scrap Metal -> Common Metals
```
