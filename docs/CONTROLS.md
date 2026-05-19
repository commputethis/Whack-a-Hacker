# Controls & Gamepad

## Keyboard Controls

### Game Controls

| Key | Action |
| --- | ------ |
| **Numpad 1-9** or **Number keys 1-9** | Whack corresponding hole |
| **Mouse Click** | Whack hole directly with hammer cursor |
| **Enter / Numpad Enter** | Start game / Play again / Confirm name |
| **L** | View leaderboard |
| **M** | Return to menu |
| **ESC** | Quit game / Return to menu |
| **Ctrl+Shift+C** | Reset leaderboard |

### Hole Layout

[7] [8] [9]  
[4] [5] [6]  
[1] [2] [3]  

## DIY Hardware Gamepad (Optional)

Build a physical arcade button box for enhanced gameplay.

### Components

- **ESP32-S3 DevKitC-1 Development Board recommended** ([Amazon link](https://amzn.to/3ProuoK))
- **12x 30mm Arcade Buttons** ([Amazon link](https://amzn.to/3PC8kbY))
  - 9 black/white buttons for game controls (1-9)
  - 3 colored buttons for system controls (Menu/Quit, Leaderboard, Enter)
- **Jumper Wires**
- **USB Cable**

### Wiring

| Button | ESP32-S3 Pin | Function |
| ------ | ------------ | -------- |
| 7 | GPIO 1 | Numpad 7 |
| 8 | GPIO 2 | Numpad 8 |
| 9 | GPIO 3 | Numpad 9 |
| 4 | GPIO 4 | Numpad 4 |
| 5 | GPIO 5 | Numpad 5 |
| 6 | GPIO 6 | Numpad 6 |
| 1 | GPIO 7 | Numpad 1 |
| 2 | GPIO 8 | Numpad 2 |
| 3 | GPIO 9 | Numpad 3 |
| Enter | GPIO 10 | Start/Confirm |
| Leaderboard | GPIO 11 | L key |
| Menu/Quit | GPIO 12 | Escape |

### Arduino Code

See [gamepad.ino](code/gamepad.ino) in the repository for the full ESP32-S3 USB HID keyboard emulation code.

### Assembly

1. Install ESP32 support in Arduino IDE
2. Install Bounce2 library
3. Upload code to ESP32-S3
4. Wire buttons to GPIO pins (COM to GND, NO to GPIO)
5. Assemble in 3D printed enclosure

See [stl/](stl/) folder for 3D printable enclosure files.
