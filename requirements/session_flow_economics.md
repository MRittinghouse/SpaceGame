# Session Flow Economics Analysis

> Credit and XP flow through the first 30 minutes of gameplay.
> Validates that the player can afford meaningful choices by session end.

## First Session Credit Flow

| Event | Credits | Running Total | XP | Total XP |
|-------|---------|---------------|-----|----------|
| Game start | +4,000 | 4,000 | 0 | 0 |
| Ship parts (tutorial) | -1,900 | 2,100 | - | 0 |
| Bill of Landing fee | -250 | 1,850 | +20 | 20 |
| Iron Delivery reward | +600 | 2,450 | +40 | 60 |
| Elena's lesson reward | +150 | 2,600 | +50 | 110 |
| Buy 5 food (tutorial trade) | -250 | 2,350 | - | 110 |
| Union Territory complete | - | 2,350 | +75 | 185 |
| First real trade (with bonus) | +150 est | 2,500 | +5 | 190 |
| The Foreman's Son (Marcus) | +200 | 2,700 | +60 | 245 |

## Summary at Minute 30

- **Credits**: 4,000 -> 2,700 (net -1,300, invested in ship)
- **XP**: 245 (Level 2 at 130 XP threshold, approaching Level 3 at 320)
- **Systems visited**: 3 (Nexus Prime, Forgeworks, Breakstone)
- **Skills available**: 1 skill point at Level 2
- **Ship**: Self-built shuttle with cockpit, engine, reactor, cargo bay

## Affordability Check

- Fuel refill: ~150 CR (affordable)
- Basic weapon: ~500 CR (affordable)
- Ship mark 2 upgrade: ~2,000 CR (save up through trading)
- Crew hiring: ~800 CR (affordable after a few more trades)

## Assessment

The curve is healthy. The ship building tutorial creates narrative budget tension (spending almost half starting funds) while missions gradually replenish. By minute 30, the player has enough for meaningful choices (weapon vs. more cargo capacity vs. saving for a bigger ship) without feeling flush. The first-trade bonus provides a psychological boost without distorting the economy.

## Tuning Levers (balance.json)

- `starting_conditions.credits`: 4000 (increase for easier start)
- `economy.rest_cost_per_day`: 0 (increase to penalize day-skipping)
- First-trade bonus: 50% markup (hardcoded, could move to balance.json)
