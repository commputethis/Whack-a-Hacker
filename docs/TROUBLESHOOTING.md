# Troubleshooting

## Linux

### "No module named 'pygame'"

- **Fix:** `sudo apt install python3-pygame` or `pip install pygame`

### "externally-managed-environment"

- **Fix:** Use virtual environment (Option 2 in install guide) or `--break-system-packages` flag

### Audio Not Working

- **Fix:** `sudo apt install alsa-utils` or launch with `SDL_AUDIODRIVER=alsa python3 main.py`

### Performance Issues

- Close other applications
- Ensure Python 3.8+
- Try installing pygame via apt instead of pip

## AppImage

### "FUSE setup" error

- **Fix:** `sudo apt install libfuse2`

### "Cannot mount AppImage"

- **Fix:** Use `./whack-a-hacker.AppImage --appimage-extract-and-run`

### "GLIBC_2.38 not found"

- **Fix:** AppImage was built on newer system. Build from source on Ubuntu 22.04 or use source install.

## Windows

### "Python was not found"

- **Fix:** Add Python to PATH during installation or use `py` instead of `python`

### Game window freezes

- **Fix:** Update graphics drivers

## macOS

### "No module named 'pygame'"

- **Fix:** `brew install sdl2` then `pip3 install pygame`

### Game window doesn't appear

- **Fix:** Grant Terminal "Screen Recording" permission in System Preferences > Security & Privacy

### Architecture errors on M1/M2 Macs

- **Fix:** Ensure Python and pygame are installed for Apple Silicon (arm64), not Intel (x86_64)

## Theme Configuration

### Changes not applying

- Restart the game after modifying `theme_config.json`
- Validate JSON syntax: `python3 -m json.tool ~/.local/share/whack-a-hacker/theme_config.json`

### File not found

- Ensure the config is at: `~/.local/share/whack-a-hacker/theme_config.json`

## Leaderboard

### Scores not saving

- Ensure `~/.local/share/whack-a-hacker/` exists and is writable
- Check disk space
- Reset with Ctrl+Shift+C if corrupted
