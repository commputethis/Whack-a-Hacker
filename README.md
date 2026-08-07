# Whack-a-Hacker

[![Whack-a-Hacker Screenshot](images/MenuScreenshot.png)](images/MenuScreenshot.png)

A fast-paced, cyber security themed whack-a-mole game built with Python and Pygame. Defeat hackers, avoid phishing traps, collect power-ups, and climb the leaderboard.

- [Whack-a-Hacker](#whack-a-hacker)
  - [Quick Start](#quick-start)
  - [Features](#features)
  - [Documentation](#documentation)
  - [Game Modes](#game-modes)
  - [Game Mechanics](#game-mechanics)
    - [Scoring](#scoring)
      - [Enemy Points](#enemy-points)
      - [Friendly Penalties](#friendly-penalties)
      - [Combo Bonus](#combo-bonus)
    - [Power-Ups](#power-ups)
    - [Difficulty Progression](#difficulty-progression)
  - [Leaderboard](#leaderboard)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

## Quick Start

```bash
git clone https://github.com/commputethis/Whack-a-Hacker.git
cd whack-a-hacker
python3 main.py
```

## Features

- Diverse Enemy Types: Regular hackers, APT threats, social engineers, powerful boss hackers, and phishing emails
- Two Game Modes: Welcoming Quick Play and the full Cyber Challenge experience
- Power-Ups: Freeze time, double points, add time to the clock, and slow motion
- Boss Battles: Boss hackers appear every ~30 seconds and require 3 hits to defeat
- Combo System: Chain consecutive hits for bonus points starting at 3 hits in a row
- Procedural Assets: All sprites and sound effects are generated in code — no external files required
- Persistent Leaderboard: Ranks players by score and tracks competitive stats such as maximum combo, bosses defeated, and friendlies hit
- Customizable Themes: Easy to re-theme by changing image paths, colors, and text
- Mouse Support: Click to whack with a custom hammer cursor that animates on click

## Documentation

- [Installation Guide](./docs/INSTALL.md) — Setup instructions for Linux, Windows, and macOS
- [Controls & Gamepad](./docs/CONTROLS.md) — Keyboard controls and DIY hardware gamepad build
- [Customization](./docs/CUSTOMIZATION.md) — Themes, custom sprites, and configuration
- [Troubleshooting](./docs/TROUBLESHOOTING.md) — Common issues and solutions
- [Building from Source](./docs/BUILD.md) — Build your own AppImage and development tools

## Game Modes

- **Quick Play — Hit everything!** Includes every threat type, bosses, combos,
  and normal difficulty progression. Friendlies and power-ups do not spawn.
- **Cyber Challenge — Stop threats. Protect friendlies. Collect power-ups.**
  Preserves the full game with friendly penalties, power-ups, detailed feedback,
  and a Clean Run when no friendlies are hit.

On the menu, use **Up/Down** or press **1** for Quick Play and **2** for Cyber
Challenge, then press **Enter / Green** to start. Selecting a mode does not start
it immediately. The illustrated Points Guide updates with the selected mode.

## Game Mechanics

### Scoring

#### Enemy Points

| Enemy | Base Points | Hits Required | Notes |
| ----- | ----------- | ------------- | ----- |
| Hacker | +2 | 1 | Standard threat |
| APT | +3 | 1 | Faster spawn/despawn |
| Social Engineer | +3 | 1 | Looks like friendly |
| Phishing Email | +2 | 1 | Block the attack |
| Boss Hacker | +8 | 3 | Spawns every ~30 seconds |

#### Friendly Penalties

| Target | Penalty | Reason |
| ------ | ------- | ------ |
| Shield | -1 | Don't hit defenses! |
| IT Admin | -1 | Protect your allies |
| Lock | -1 | Security is friend, not food |

#### Combo Bonus

| Combo Level | Bonus Multiplier | Notes |
| ----------- | ---------------- | - |
| x3+ | +1 points per hit | Resets after miss or whacking a friendly |

### Power-Ups

- **Freeze** (❄️): Freezes all active moles for 3 seconds
- **Double Points** (2X): Doubles all points for 5 seconds
- **Time Bonus** (+5s): Adds 5 seconds to the game clock
- **Slow Motion** (🐌): Moles stay visible 50% longer for 4 seconds

### Difficulty Progression

- Game starts with 2 simultaneous moles max
- Every 15 seconds, spawn rate increases and max active moles increases
- Moles appear for shorter durations as difficulty ramps up
- Boss hackers appear at 25 seconds, then every 30 seconds

## Leaderboard

High scores are saved to `~/.local/share/whack-a-hacker/leaderboard.json` on your
system. Quick Play and Cyber Challenge have separate score-ranked views because
their scores are not directly comparable. Each entry tracks:

- Player name
- Score (the primary ranking metric)
- Maximum combo achieved
- Bosses defeated
- Friendlies hit
- Date of achievement

Press **L / Yellow** on the menu to open the selected mode's leaderboard. On a
leaderboard, the same **L / Yellow** input switches modes, **Enter / Green** starts
the displayed mode, and **Escape / Red** returns to the menu. Yellow is not a
separate input: the arcade button sends the letter `L`.

Leaderboard records created before modes were introduced are treated as Cyber
Challenge scores. New entries record their mode, while legacy files remain usable
without migration.

Accuracy is no longer recorded or displayed. The Game Over screen instead gives
detailed performance feedback, including hackers whacked and missed, friendlies
hit, threats stopped, bosses defeated, power-ups collected, and maximum combo.
A **Clean Run** is awarded only in Cyber Challenge when no friendlies are hit; it
is a visual achievement only and does not affect score or leaderboard ranking.

## License

- MIT License — See [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with Pygame
- Sound effects generated using mathematical waveforms
- Sprites generated procedurally using Pygame drawing functions
