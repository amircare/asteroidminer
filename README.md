# Asteroid Miner

A space mining game where you pilot a ship, mine asteroids, and upgrade your equipment!

## Quick Start

**Windows:** Double-click `asteroidminer.bat`

**Linux/Mac:** Run `./asteroidminer.sh` or `python3 launcher.py`

The launcher will automatically install pygame if needed.

## Controls

### Keyboard
- **W** - Thrust forward
- **A/D** - Rotate left/right
- **SPACE** - Fire weapon
- **E** - Sell cargo (when at base)
- **P** - Enter Power Shop (when at power shop)
- **ESC** - Save and return to menu (with confirmation)
- **Click on carried items** - Drop resources

## Multiplayer

### Hosting
1. Main Menu → Multiplayer → Host Game
2. Select existing world or create new one
3. Share your IP with friends (port 5555)

### Joining
1. Main Menu → Multiplayer → Join Game
2. Enter host's IP and port
3. Click Connect

## Gameplay

- Mine asteroids by shooting them (spawn outside camera)
- Collect floating loot resources (Iron, Gold, Diamond, Power Cores, etc.)
- Use Loot Magnet power to auto-collect loot from a distance
- Click on carried resources to drop them and swap for better ones
- Return to the **blue base** to sell cargo and upgrade
- Watch resources turn into coins and fly to your money counter!
- **Build Power Shop** by dropping materials into the build zone:
  - 10 Iron, 5 Copper, 3 Titanium, 2 Uranium, 1 Power Core
- Visit the **purple Power Shop** (near base) to buy powers (Press P)
- Asteroids scale smoothly with distance from base
- Golden asteroids drop Power Cores (30% chance) - green text
- Boss chance increases as you explore farther
- More asteroids spawn when you travel far from base

### Upgrades

Different upgrade costs (at base):
- Speed (cheapest) - Move faster
- Storage - Carry more cargo
- Shooting Speed - Fire faster
- Damage (most expensive) - Deal more damage

### Superpowers

Visit the Power Shop to buy and upgrade abilities:

- **Damage Orbs** ($500) - Orbs orbit and damage asteroids
- **Bullet Split** ($600) - Bullets split on hit
- **Auto Aim** ($800) - Bullets track asteroids
- **Ultra Fire** ($700) - Extreme fire rate
- **Loot Magnet** ($550) - Auto-collect loot from distance
- **Explosive Shots** ($900) - Bullets explode on impact
- **Piercing Shots** ($1000) - Bullets pierce through multiple asteroids

Each power upgrades up to 5 levels!

### Quests & Cosmetics

Complete quests to unlock cosmetic rewards:
- **Ship Designs** - Arrow, Wide Wing, Needle, Delta
- **Fire Effects** - Blue Flame, Green Plasma, Purple Energy, Rainbow

Quests include destroying asteroids, collecting resources, and earning coins!

## Requirements

- Python 3.8+
- pygame 2.5.0+ (auto-installed by launcher)

## Troubleshooting

**Game won't start?**
- Make sure Python 3.8+ is installed
- Run: `pip install pygame`

**Multiplayer not working?**
- Check firewall (allow port 5555)
- Use "localhost" for same-computer play
