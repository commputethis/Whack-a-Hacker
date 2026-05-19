# Building from Source

## Build Your Own AppImage

### Requirements

- Ubuntu 22.04 (matching target system GLIBC)
- Python 3.8+
- `python3-pygame` installed

### Steps

```bash
git clone https://github.com/commputethis/Whack-a-Hacker.git
cd whack-a-hacker

# Build
./build-easy.sh
```

#### Output: ./AppImages/whack-a-hacker-x86_64.AppImage

## Development Tools

### Export Sprites

#### Generate PNG files of all procedurally generated sprites for documentation

```bash
python3 export_sprites.py
```

Creates images/sprites/ directory with all game assets as PNG files.

## Contributing

Contributions welcome for:

- New enemy types
- Additional power-ups
- Theme variations
- Performance improvements
- Hardware enhancements

### Submit pull requests on GitHub
