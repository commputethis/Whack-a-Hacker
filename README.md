# Whack-a-Hacker

[![Whack-a-Hacker Screenshot](images/MenuScreenshot.png)](images/MenuScreenshot.png)

A fast-paced, cyber security themed whack-a-mole game built with Python and Pygame. Defeat hackers, avoid phishing traps, collect power-ups, and climb the leaderboard.

- [Whack-a-Hacker](#whack-a-hacker)
  - [Quick Start](#quick-start)
  - [Features](#features)
  - [Documentation](#documentation)
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
- Power-Ups: Freeze time, double points, add time to the clock, and slow motion
- Boss Battles: Boss hackers appear every ~30 seconds and require 3 hits to defeat
- Combo System: Chain consecutive hits for bonus points starting at 3 hits in a row
- Procedural Assets: All sprites and sound effects are generated in code — no external files required
- Persistent Leaderboard: Tracks high scores with stats like accuracy and bosses defeated
- Customizable Themes: Easy to re-theme by changing image paths, colors, and text
- Mouse Support: Click to whack with a custom hammer cursor that animates on click

## Documentation

- [Installation Guide](./docs/INSTALL.md) — Setup instructions for Linux, Windows, and macOS
- [Controls & Gamepad](./docs/CONTROLS.md) — Keyboard controls and DIY hardware gamepad build
- [Customization](./docs/CUSTOMIZATION.md) — Themes, custom sprites, and configuration
- [Troubleshooting](./docs/TROUBLESHOOTING.md) — Common issues and solutions
- [Building from Source](./docs/BUILD.md) — Build your own AppImage and development tools

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

High scores are saved to `~/.local/share/whack-a-hacker/leaderboard.json` on your system. The leaderboard tracks:

- Score
- Player name
- Maximum combo achieved
- Accuracy percentage
- Bosses defeated
- Date of achievement

## License

- MIT License — See [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with Pygame
- Sound effects generated using mathematical waveforms
- Sprites generated procedurally using Pygame drawing functions
