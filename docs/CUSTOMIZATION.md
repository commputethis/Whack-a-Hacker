# Customization

## Theme Configuration File

Create `~/.local/share/whack-a-hacker/theme_config.json` to customize text without modifying code:

```json
{
  "theme": {
    "title": "Whack-a-Mole!",
    "subtitle": "A Whack-a-Mole",
    "game_over_title": "GAME OVER",
    "score_label": "Score:"
  },
  "enemies": {
    "hacker": "MOLE",
    "boss": "KING MOLE"
  },
  "powerups": {
    "freeze": "FREEZE",
    "double": "DOUBLE POINTS"
  }
}
```

## Custom Sprites

Place PNG files in ~/.local/share/whack-a-hacker/assets/ to override generated sprites:

### Supported filenames:

- Enemies: hacker1.png, hacker2.png, hacker3.png, apt.png, boss.png, social_eng.png, phishing.png
- Friendlies: shield.png, it_admin.png, lock.png

Recommended size: 80x80 pixels

### Direct Code Customization

Edit main.py for advanced changes:

```python
# Change game duration
GAME_DURATION = 90

# Adjust colors
C_BG = (15, 15, 35)
C_TEXT = (0, 255, 200)
```

### Export Sprites for Documentation

#### Generate PNG files of all game sprites

```bash
python3 export_sprites.py
```

Output saved to images/sprites/ directory.
