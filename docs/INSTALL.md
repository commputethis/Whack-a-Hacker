# Installation Guide

## Prerequisites

- **OS:** Linux (Ubuntu 18.04+), Windows 10/11, or macOS 10.14+
- **Python:** 3.8 or higher (Linux/Windows/Mac)
- **Display:** 1280x720 minimum; 1920x1080 recommended

## Linux

### Option 1: Install via apt (Recommended)

```bash
sudo apt update
sudo apt install python3-pygame

git clone https://github.com/commputethis/Whack-a-Hacker.git
cd whack-a-hacker
python3 main.py
```

### Option 2: Use pip with virtual environment

```bash
sudo apt install python3-full

git clone https://github.com/commputethis/Whack-a-Hacker.git
cd whack-a-hacker

python3 -m venv venv
source venv/bin/activate
pip install pygame

python3 main.py
```

### Option 3: AppImage (Portable)

Download and run without installation:

```bash
wget https://github.com/commputethis/Whack-a-Hacker/releases/download/v1.10/whack-a-hacker-x86_64_v1.10.AppImage
chmod +x whack-a-hacker-x86_64_v1.10.AppImage
./whack-a-hacker-x86_64_v1.10.AppImage
```

AppImage Troubleshooting:

| Issue | Solution |
| - | - |
| "FUSE setup" error | Install libfuse2: `sudo apt install libfuse2` |
| No audio | `SDL_AUDIODRIVER=alsa ./whack-a-hacker.AppImage` |
| "Cannot mount" error | `./whack-a-hacker.AppImage --appimage-extract-and-run` |

## Windows

```powershell
# Install Python from https://python.org

git clone https://github.com/commputethis/Whack-a-Hacker.git
cd whack-a-hacker

pip install pygame
python main.py
```

## macOS

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python sdl2 sdl2_mixer sdl2_image sdl2_ttf portmidi

git clone https://github.com/commputethis/Whack-a-Hacker.git
cd whack-a-hacker

pip3 install pygame
python3 main.py
```

### macOS Notes

- Grant Terminal "Screen Recording" permission in System Preferences > Security & Privacy if the window doesn't appear
- Install portaudio if audio issues: `brew install portaudio`
