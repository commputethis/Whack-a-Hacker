#!/usr/bin/env python3
"""
Whack-a-Hacker: A Cyber Security themed Whack-a-Mole game
Features: Boss moles, power-ups, deceptive entities (phishing/social engineers),
          combo system, procedural sounds & sprites, persistent leaderboard.
Controls: Numpad 1-9 (or regular 1-9) or Mouse Click, Ctrl+Shift+C to reset leaderboard.
"""
import sys
import os

# Fix path resolution for PyInstaller / Frozen apps
if getattr(sys, 'frozen', False):
    # We are running as a bundled executable (PyInstaller)
    # sys._MEIPASS is the temporary folder where PyInstaller extracts files
    application_path = sys._MEIPASS
else:
    # We are running as a standard script
    application_path = os.path.dirname(os.path.abspath(__file__))

import pygame
import random
import json
import os
import sys
import time
import math
import array
from pathlib import Path

# ===========================================================================
# CONFIGURATION — Edit these to re-theme the entire game
# ===========================================================================

GAME_TITLE = "Whack-a-Hacker!"
GAME_DURATION = 60  # seconds
FPS = 60
POST_GAME_IDLE_TIMEOUT_MS = 120000

# _DATA_DIR = os.environ.get("WHACK_DATA_DIR", "/tmp/whack-a-hacker")
# if not _DATA_DIR:
#    _DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "whack-a-hacker")
_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "whack-a-hacker")
os.makedirs(_DATA_DIR, exist_ok=True)
LEADERBOARD_FILE = os.path.join(_DATA_DIR, "leaderboard.json")

# Look for user assets first, fall back to bundled assets
_USER_ASSETS = os.path.join(_DATA_DIR, "assets")
_BUNDLED_ASSETS = os.path.join(application_path, "assets")
ASSETS_DIR = _USER_ASSETS if os.path.exists(_USER_ASSETS) else _BUNDLED_ASSETS

GRID_COLS = 3
GRID_ROWS = 3
HOLE_WIDTH = 200
HOLE_HEIGHT = 170

# ---- Timing (ms) ----
MOLE_MIN_SHOW_TIME = 900
MOLE_MAX_SHOW_TIME = 2400
MOLE_MIN_SPAWN_DELAY = 250
MOLE_MAX_SPAWN_DELAY = 1000
INITIAL_MAX_ACTIVE = 2

# ---- Scoring ----
SCORE_HIT_HACKER = 2
SCORE_HIT_APT = 3
SCORE_HIT_BOSS = 8
SCORE_HIT_SOCIAL_ENGINEER = 3
SCORE_HIT_PHISHING = 2
SCORE_HIT_FRIENDLY = -1


COMBO_THRESHOLD = 3
COMBO_BONUS = 1

# ---- Difficulty ramp ----
RAMP_INTERVAL = 15       # seconds between difficulty bumps
SPEED_REDUCTION_MS = 80  # ms shaved off show-time per bump

# ---- Boss ----
BOSS_FIRST_SPAWN = 15    # seconds into the game
BOSS_SPAWN_INTERVAL = 20  # seconds between bosses after the first
BOSS_HITS_REQUIRED = 3
BOSS_SHOW_TIME_MULT = 2.5

# ---- Power-ups ----
POWERUP_INTERVAL_MIN = 12   # seconds
POWERUP_INTERVAL_MAX = 20
POWERUP_SHOW_TIME = 3500    # ms visible
POWERUP_FREEZE_DUR = 3000   # ms
POWERUP_DOUBLE_DUR = 5000
POWERUP_SLOW_DUR = 4000
POWERUP_TIME_BONUS = 5      # seconds added

# ---- Spawn weights (relative, any positive number) ----
SPAWN_WEIGHTS = {
    "hacker": 45,
    "apt": 10,
    "phishing": 12,
    "social_engineer": 8,
    "shield": 10,
    "it_admin": 8,
    "lock": 7,
}

# ---- Optional image overrides (place PNGs in assets/) ----
MOLE_IMAGE_PATHS = {
    "hacker": [f"{ASSETS_DIR}/hacker1.png", f"{ASSETS_DIR}/hacker2.png", f"{ASSETS_DIR}/hacker3.png"],
    "apt": [f"{ASSETS_DIR}/apt.png"],
    "boss": [f"{ASSETS_DIR}/boss.png"],
    "social_engineer": [f"{ASSETS_DIR}/social_eng.png"],
    "phishing": [f"{ASSETS_DIR}/phishing.png"],
}
FRIENDLY_IMAGE_PATHS = {
    "shield": [f"{ASSETS_DIR}/shield.png"],
    "it_admin": [f"{ASSETS_DIR}/it_admin.png"],
    "lock": [f"{ASSETS_DIR}/lock.png"],
}

# ---- Colors ----
C_BG            = (15, 15, 35)
C_HOLE          = (30, 30, 50)
C_HOLE_BORDER   = (0, 200, 255)
C_TEXT          = (0, 255, 200)
C_SCORE         = (255, 255, 255)
C_WARNING       = (255, 80, 80)
C_COMBO         = (255, 215, 0)
C_TIMER         = (0, 200, 255)
C_TIMER_LOW     = (255, 50, 50)
C_HIT_FLASH     = (255, 255, 100)
C_MISS_FLASH    = (255, 50, 50)
C_BOSS_HP       = (255, 50, 50)
C_BOSS_HP_BG    = (60, 60, 60)
C_PU_GLOW       = (255, 215, 0)
C_FREEZE        = (100, 200, 255)
C_DOUBLE        = (255, 215, 0)
C_TIME          = (100, 255, 100)
C_SLOW          = (200, 150, 255)

# ---- Key maps ----
NUMPAD_MAP = {
    pygame.K_KP7: (0, 0), pygame.K_KP8: (0, 1), pygame.K_KP9: (0, 2),
    pygame.K_KP4: (1, 0), pygame.K_KP5: (1, 1), pygame.K_KP6: (1, 2),
    pygame.K_KP1: (2, 0), pygame.K_KP2: (2, 1), pygame.K_KP3: (2, 2),
}
NUMBER_MAP = {
    pygame.K_7: (0, 0), pygame.K_8: (0, 1), pygame.K_9: (0, 2),
    pygame.K_4: (1, 0), pygame.K_5: (1, 1), pygame.K_6: (1, 2),
    pygame.K_1: (2, 0), pygame.K_2: (2, 1), pygame.K_3: (2, 2),
}

MAX_LEADERBOARD = 20

GAME_MODES = {
    "quick": {
        "label": "Quick Play",
        "instruction": "Hit everything!",
        "friendlies_enabled": False,
        "powerups_enabled": False,
        "clean_run_enabled": False,
    },
    "challenge": {
        "label": "Cyber Challenge",
        "instruction": "Stop threats. Protect friendlies. Collect power-ups.",
        "friendlies_enabled": True,
        "powerups_enabled": True,
        "clean_run_enabled": True,
    },
}


# ===========================================================================
# PROCEDURAL SOUND GENERATOR
# ===========================================================================

class SFX:
    """Builds short sound-effect buffers from math — no WAV files needed."""

    SR = 22050  # sample-rate (Hz)

    # -- low-level helpers --------------------------------------------------

    @staticmethod
    def _buf(freq, ms, vol=0.3, wave="square", fade=True,
             vib_hz=0, vib_depth=0):
        n = max(1, int(SFX.SR * ms / 1000))
        out = array.array("h", [0] * n)
        for i in range(n):
            t = i / SFX.SR
            f = freq + (vib_depth * math.sin(2 * math.pi * vib_hz * t)
                        if vib_hz else 0)
            if f <= 0:
                v = 0.0
            elif wave == "sine":
                v = math.sin(2 * math.pi * f * t)
            elif wave == "square":
                v = 1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0
            elif wave == "saw":
                p = SFX.SR / f
                v = 2.0 * ((i % max(1, int(p))) / max(1, p)) - 1.0
            elif wave == "tri":
                p = SFX.SR / f
                pos = (i % max(1, int(p))) / max(1, p)
                v = 4.0 * abs(pos - 0.5) - 1.0
            elif wave == "noise":
                v = random.uniform(-1, 1)
            else:
                v = 0.0
            env = max(0.0, 1.0 - i / n) if fade else 1.0
            out[i] = max(-32768, min(32767, int(v * env * vol * 32767)))
        return out

    @staticmethod
    def _mix(a, b):
        ln = max(len(a), len(b))
        r = array.array("h", [0] * ln)
        for i in range(ln):
            v = (a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)
            r[i] = max(-32768, min(32767, v))
        return r

    @staticmethod
    def _cat(*bufs):
        r = array.array("h")
        for b in bufs:
            r.extend(b)
        return r

    @staticmethod
    def _snd(buf):
        try:
            return pygame.mixer.Sound(buffer=bytes(buf))
        except Exception:
            return None

    # -- named effects ------------------------------------------------------

    @classmethod
    def whack_hit(cls):
        return cls._snd(cls._mix(
            cls._buf(0, 30, 0.25, "noise"),
            cls._buf(300, 80, 0.2, "sine")))

    @classmethod
    def whack_miss(cls):
        return cls._snd(cls._buf(100, 50, 0.1, "noise"))

    @classmethod
    def friendly_hit(cls):
        return cls._snd(cls._cat(
            cls._buf(300, 120, 0.2, "square"),
            cls._buf(200, 180, 0.2, "square")))

    @classmethod
    def phishing_trap(cls):
        return cls._snd(cls._cat(
            cls._buf(250, 100, 0.2, "sine"),
            cls._buf(150, 200, 0.2, "sine")))

    @classmethod
    def social_hit(cls):
        return cls._snd(cls._cat(
            cls._buf(500, 80, 0.2, "sine"),
            cls._buf(700, 150, 0.2, "sine")))

    @classmethod
    def combo(cls, level=1):
        f = 400 + min(level, 12) * 60
        return cls._snd(cls._buf(f, 100, 0.2, "sine"))

    @classmethod
    def boss_hit(cls):
        return cls._snd(cls._mix(
            cls._buf(0, 50, 0.3, "noise"),
            cls._buf(150, 120, 0.25, "sine")))

    @classmethod
    def boss_defeated(cls):
        return cls._snd(cls._cat(
            cls._buf(400, 120, 0.2, "sine"),
            cls._buf(500, 120, 0.2, "sine"),
            cls._buf(700, 250, 0.25, "sine")))

    @classmethod
    def powerup(cls):
        return cls._snd(cls._cat(
            cls._buf(600, 60, 0.15, "sine"),
            cls._buf(800, 60, 0.15, "sine"),
            cls._buf(1000, 60, 0.15, "sine"),
            cls._buf(1200, 120, 0.2, "sine")))

    @classmethod
    def freeze(cls):
        return cls._snd(
            cls._buf(1000, 300, 0.15, "sine", vib_hz=20, vib_depth=200))

    @classmethod
    def speed_up(cls):
        return cls._snd(cls._cat(
            cls._buf(600, 100, 0.15, "square"),
            cls._buf(800, 100, 0.15, "square"),
            cls._buf(600, 100, 0.15, "square"),
            cls._buf(800, 150, 0.15, "square")))

    @classmethod
    def game_over(cls):
        return cls._snd(cls._cat(
            cls._buf(400, 200, 0.2, "sine"),
            cls._buf(300, 200, 0.2, "sine"),
            cls._buf(200, 400, 0.2, "sine")))

    @classmethod
    def tick(cls):
        return cls._snd(cls._buf(800, 30, 0.15, "sine"))

    @classmethod
    def game_start(cls):
        return cls._snd(cls._cat(
            cls._buf(400, 100, 0.15, "sine"),
            cls._buf(500, 100, 0.15, "sine"),
            cls._buf(700, 200, 0.2, "sine")))


# ===========================================================================
# PROCEDURAL SPRITE GENERATOR
# ===========================================================================

class Sprites:
    """Draws every entity type in code so the game works with zero image files."""

    @staticmethod
    def hacker(sz, variant=0):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        col = [(200, 40, 40), (180, 50, 180), (160, 60, 40)][variant % 3]
        pygame.draw.rect(s, col, (cx - 30, cy, 60, 45), border_radius=8)
        pygame.draw.circle(s, (220, 180, 150), (cx, cy - 8), 22)
        pygame.draw.arc(s, col, (cx - 28, cy - 35, 56, 50), 0, math.pi, 8)
        pygame.draw.rect(s, col, (cx - 28, cy - 14, 56, 10))
        pygame.draw.rect(s, (0, 255, 0), (cx - 12, cy - 12, 8, 4))
        pygame.draw.rect(s, (0, 255, 0), (cx + 4, cy - 12, 8, 4))
        pygame.draw.rect(s, (30, 30, 30), (cx - 18, cy - 4, 36, 10),
                         border_radius=3)
        pygame.draw.rect(s, (80, 80, 80), (cx - 18, cy + 10, 36, 22),
                         border_radius=2)
        pygame.draw.rect(s, (0, 200, 0), (cx - 14, cy + 14, 28, 14),
                         border_radius=2)
        pygame.draw.circle(s, (0, 80, 0), (cx, cy + 19), 4)
        return s

    @staticmethod
    def apt(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        pygame.draw.rect(s, (40, 0, 60), (cx - 30, cy, 60, 45),
                         border_radius=8)
        pygame.draw.circle(s, (180, 150, 130), (cx, cy - 8), 22)
        pygame.draw.arc(s, (40, 0, 60), (cx - 28, cy - 35, 56, 50),
                        0, math.pi, 8)
        pygame.draw.rect(s, (40, 0, 60), (cx - 28, cy - 14, 56, 10))
        pygame.draw.rect(s, (255, 0, 0), (cx - 12, cy - 12, 8, 4))
        pygame.draw.rect(s, (255, 0, 0), (cx + 4, cy - 12, 8, 4))
        pts = [(cx - 10, cy - 28), (cx - 8, cy - 36), (cx - 3, cy - 30),
               (cx, cy - 38), (cx + 3, cy - 30), (cx + 8, cy - 36),
               (cx + 10, cy - 28)]
        pygame.draw.polygon(s, (255, 215, 0), pts)
        pygame.draw.rect(s, (20, 20, 20), (cx - 18, cy - 4, 36, 10),
                         border_radius=3)
        pygame.draw.rect(s, (60, 60, 60), (cx - 18, cy + 10, 36, 22),
                         border_radius=2)
        pygame.draw.rect(s, (200, 0, 0), (cx - 14, cy + 14, 28, 14),
                         border_radius=2)
        return s

    @staticmethod
    def boss(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        for r in range(3, 0, -1):
            pygame.draw.circle(s, (255, 50, 0, 30 * r), (cx, cy), 38 + r * 3)
        pygame.draw.rect(s, (150, 0, 0), (cx - 35, cy - 2, 70, 48),
                         border_radius=10)
        pygame.draw.circle(s, (200, 160, 130), (cx, cy - 14), 25)
        pygame.draw.arc(s, (30, 0, 0), (cx - 32, cy - 42, 64, 55),
                        0, math.pi, 10)
        pygame.draw.rect(s, (30, 0, 0), (cx - 32, cy - 18, 64, 12))
        pygame.draw.rect(s, (255, 100, 0), (cx - 14, cy - 18, 10, 6))
        pygame.draw.rect(s, (255, 100, 0), (cx + 4, cy - 18, 10, 6))
        pygame.draw.rect(s, (255, 255, 0), (cx - 12, cy - 17, 6, 4))
        pygame.draw.rect(s, (255, 255, 0), (cx + 6, cy - 17, 6, 4))
        pygame.draw.circle(s, (255, 255, 255), (cx, cy + 12), 8)
        pygame.draw.rect(s, (255, 255, 255), (cx - 6, cy + 18, 12, 6))
        pygame.draw.rect(s, (30, 0, 0), (cx - 4, cy + 8, 3, 3))
        pygame.draw.rect(s, (30, 0, 0), (cx + 1, cy + 8, 3, 3))
        try:
            f = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f.render("BOSS", True, (255, 255, 0)),
                   (cx - 12, cy + 30))
        except Exception:
            pass
        return s

    @staticmethod
    def social_engineer(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        pygame.draw.rect(s, (40, 120, 80), (cx - 28, cy + 2, 56, 40),
                         border_radius=6)
        pygame.draw.polygon(s, (60, 160, 100),
                            [(cx - 3, cy + 2), (cx + 3, cy + 2),
                             (cx + 2, cy + 20), (cx, cy + 22),
                             (cx - 2, cy + 20)])
        pygame.draw.circle(s, (220, 180, 150), (cx, cy - 10), 20)
        pygame.draw.arc(s, (50, 30, 20), (cx - 20, cy - 30, 40, 30),
                        0, math.pi, 5)
        pygame.draw.circle(s, (200, 200, 200), (cx - 8, cy - 12), 7, 2)
        pygame.draw.circle(s, (200, 200, 200), (cx + 8, cy - 12), 7, 2)
        pygame.draw.line(s, (200, 200, 200), (cx - 1, cy - 12),
                         (cx + 1, cy - 12), 2)
        pygame.draw.arc(s, (200, 100, 100), (cx - 8, cy - 6, 16, 10),
                        3.3, 6.1, 2)
        pygame.draw.ellipse(s, (0, 0, 0, 140), (cx - 15, cy - 16, 12, 6))
        pygame.draw.ellipse(s, (0, 0, 0, 140), (cx + 3, cy - 16, 12, 6))
        try:
            f = pygame.font.SysFont("monospace", 9, bold=True)
            s.blit(f.render("SPY", True, (255, 200, 50)),
                   (cx - 8, cy + 30))
        except Exception:
            pass
        return s

    @staticmethod
    def phishing(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        r = pygame.Rect(cx - 30, cy - 10, 60, 40)
        pygame.draw.rect(s, (220, 80, 40), r, border_radius=4)
        pygame.draw.rect(s, (255, 120, 60), r, width=2, border_radius=4)
        pygame.draw.polygon(s, (200, 60, 30),
                            [(cx - 30, cy - 10), (cx, cy + 10),
                             (cx + 30, cy - 10)])
        pygame.draw.polygon(s, (255, 120, 60),
                            [(cx - 30, cy - 10), (cx, cy + 10),
                             (cx + 30, cy - 10)], 2)
        hx, hy = cx + 15, cy - 25
        pygame.draw.line(s, (180, 180, 180), (hx, hy - 10), (hx, hy + 5), 2)
        pygame.draw.arc(s, (180, 180, 180), (hx - 5, hy, 10, 12),
                        3.14, 6.28, 2)
        try:
            f = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f.render("MAIL", True, (255, 255, 200)),
                   (cx - 12, cy + 3))
            s.blit(f.render("TRAP!", True, (255, 200, 50)),
                   (cx - 14, cy + 30))
        except Exception:
            pass
        return s

    @staticmethod
    def shield(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        pts = [(cx, cy - 30), (cx + 25, cy - 15), (cx + 20, cy + 15),
               (cx, cy + 30), (cx - 20, cy + 15), (cx - 25, cy - 15)]
        pygame.draw.polygon(s, (50, 150, 255), pts)
        pygame.draw.polygon(s, (100, 200, 255), pts, 3)
        pygame.draw.lines(s, (255, 255, 255), False,
                          [(cx - 10, cy), (cx - 2, cy + 10),
                           (cx + 12, cy - 10)], 4)
        return s

    @staticmethod
    def it_admin(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        pygame.draw.rect(s, (50, 100, 200), (cx - 25, cy + 2, 50, 35),
                         border_radius=6)
        pygame.draw.circle(s, (220, 180, 150), (cx, cy - 10), 20)
        pygame.draw.circle(s, (200, 200, 200), (cx - 8, cy - 12), 7, 2)
        pygame.draw.circle(s, (200, 200, 200), (cx + 8, cy - 12), 7, 2)
        pygame.draw.line(s, (200, 200, 200), (cx - 1, cy - 12),
                         (cx + 1, cy - 12), 2)
        pygame.draw.arc(s, (200, 100, 100), (cx - 8, cy - 6, 16, 10),
                        3.3, 6.1, 2)
        pygame.draw.rect(s, (0, 200, 100), (cx - 6, cy + 6, 12, 14),
                         border_radius=2)
        pygame.draw.rect(s, (255, 255, 255), (cx - 3, cy + 9, 6, 4))
        return s

    @staticmethod
    def lock(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        pygame.draw.arc(s, (200, 200, 50), (cx - 15, cy - 35, 30, 30),
                        0, math.pi, 5)
        pygame.draw.rect(s, (220, 200, 50), (cx - 20, cy - 10, 40, 35),
                         border_radius=4)
        pygame.draw.rect(s, (180, 160, 30), (cx - 20, cy - 10, 40, 35),
                         width=2, border_radius=4)
        pygame.draw.circle(s, (80, 60, 10), (cx, cy + 2), 6)
        pygame.draw.rect(s, (80, 60, 10), (cx - 3, cy + 2, 6, 12))
        return s

    @staticmethod
    def _pu_base(sz):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        pygame.draw.circle(s, (255, 215, 0, 60), (cx, cy), 35)
        pygame.draw.circle(s, (255, 230, 100, 40), (cx, cy), 30)
        return s, cx, cy

    @staticmethod
    def pu_freeze(sz):
        s, cx, cy = Sprites._pu_base(sz)
        for a in range(0, 360, 60):
            r = math.radians(a)
            x2 = cx + int(20 * math.cos(r))
            y2 = cy + int(20 * math.sin(r))
            pygame.draw.line(s, (100, 200, 255), (cx, cy), (x2, y2), 3)
            bx = cx + int(12 * math.cos(r))
            by = cy + int(12 * math.sin(r))
            for ba in (a - 30, a + 30):
                br = math.radians(ba)
                pygame.draw.line(s, (150, 220, 255), (bx, by),
                                 (bx + int(6 * math.cos(br)),
                                  by + int(6 * math.sin(br))), 2)
        pygame.draw.circle(s, (200, 230, 255), (cx, cy), 5)
        return s

    @staticmethod
    def pu_double(sz):
        s, cx, cy = Sprites._pu_base(sz)
        try:
            f = pygame.font.SysFont("monospace", 32, bold=True)
            t = f.render("2X", True, (255, 50, 50))
            s.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))
        except Exception:
            pygame.draw.circle(s, (255, 50, 50), (cx, cy), 15)
        return s

    @staticmethod
    def pu_time(sz):
        s, cx, cy = Sprites._pu_base(sz)
        pygame.draw.circle(s, (100, 255, 100), (cx, cy), 18, 3)
        pygame.draw.line(s, (100, 255, 100), (cx, cy), (cx, cy - 14), 3)
        pygame.draw.line(s, (100, 255, 100), (cx, cy), (cx + 10, cy), 2)
        try:
            f = pygame.font.SysFont("monospace", 12, bold=True)
            s.blit(f.render("+5s", True, (255, 255, 200)),
                   (cx - 9, cy + 20))
        except Exception:
            pass
        return s

    @staticmethod
    def pu_slow(sz):
        s, cx, cy = Sprites._pu_base(sz)
        pygame.draw.arc(s, (200, 150, 255), (cx - 15, cy - 15, 30, 25),
                        0, math.pi, 4)
        pygame.draw.ellipse(s, (200, 150, 255), (cx - 18, cy + 2, 36, 14))
        try:
            f = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f.render("SLOW", True, (255, 255, 200)),
                   (cx - 12, cy + 20))
        except Exception:
            pass
        return s
    
    # ==== Configurable generators (driven by custom_sprites.json) ====

    @staticmethod
    def gen_hacker(sz, variant, color, features):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        pygame.draw.rect(s, color, (cx - 30, cy, 60, 45), border_radius=8)
        pygame.draw.circle(s, (220, 180, 150), (cx, cy - 8), 22)
        if features.get("has_ski_mask", False):
            pygame.draw.circle(s, (40, 40, 40), (cx, cy - 8), 22)
            pygame.draw.rect(s, (220, 180, 150), (cx - 14, cy - 14, 28, 12))
            pygame.draw.circle(s, (255, 255, 255), (cx - 7, cy - 12), 5)
            pygame.draw.circle(s, (255, 255, 255), (cx + 7, cy - 12), 5)
            pygame.draw.circle(s, (0, 0, 0), (cx - 7, cy - 12), 2)
            pygame.draw.circle(s, (0, 0, 0), (cx + 7, cy - 12), 2)
        else:
            pygame.draw.arc(s, color, (cx - 28, cy - 35, 56, 50), 0, math.pi, 8)
            pygame.draw.rect(s, color, (cx - 28, cy - 14, 56, 10))
            pygame.draw.rect(s, (0, 255, 0), (cx - 12, cy - 12, 8, 4))
            pygame.draw.rect(s, (0, 255, 0), (cx + 4, cy - 12, 8, 4))
            pygame.draw.rect(s, (30, 30, 30), (cx - 18, cy - 4, 36, 10), border_radius=3)
        if features.get("has_money_bag", False):
            pygame.draw.circle(s, (80, 140, 60), (cx + 22, cy + 15), 14)
            pygame.draw.circle(s, (60, 120, 40), (cx + 22, cy + 15), 14, 2)
            try:
                f = pygame.font.SysFont("monospace", 14, bold=True)
                sym = features.get("money_symbol", "$")
                s.blit(f.render(sym, True, (255, 255, 0)), (cx + 17, cy + 8))
            except Exception:
                pass
        else:
            pygame.draw.rect(s, (80, 80, 80), (cx - 18, cy + 10, 36, 22), border_radius=2)
            pygame.draw.rect(s, (0, 200, 0), (cx - 14, cy + 14, 28, 14), border_radius=2)
            pygame.draw.circle(s, (0, 80, 0), (cx, cy + 19), 4)
        return s

    @staticmethod
    def gen_apt(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        colors = cfg.get("colors", {})
        feat = cfg.get("features", {})
        body = colors.get("body", [40, 0, 60])
        tie = colors.get("tie", [255, 215, 0])
        hair = colors.get("hair", [30, 20, 10])
        pygame.draw.rect(s, body, (cx - 30, cy, 60, 45), border_radius=8)
        pygame.draw.polygon(s, tie, [(cx-3,cy),(cx+3,cy),(cx+2,cy+25),(cx,cy+28),(cx-2,cy+25)])
        pygame.draw.circle(s, (200, 160, 130), (cx, cy - 8), 22)
        pygame.draw.arc(s, hair, (cx-22, cy-30, 44, 30), 0, math.pi, 8)
        if feat.get("has_sunglasses", True):
            pygame.draw.rect(s, (20,20,20), (cx-16,cy-14,12,8), border_radius=2)
            pygame.draw.rect(s, (20,20,20), (cx+4,cy-14,12,8), border_radius=2)
            pygame.draw.line(s, (20,20,20), (cx-4,cy-11), (cx+4,cy-11), 2)
        pygame.draw.arc(s, (150,80,80), (cx-6,cy-2,12,8), 3.3, 6.1, 2)
        if feat.get("has_pyramid", True):
            pygame.draw.polygon(s, (255,215,0,80), [(cx-25,cy+42),(cx,cy+20),(cx+25,cy+42)])
        label = feat.get("label", "APT")
        try:
            f = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f.render(label, True, (255, 50, 50)), (cx - 14, cy + 30))
        except Exception:
            pass
        return s

    @staticmethod
    def gen_boss(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        feat = cfg.get("features", {})
        aura = cfg.get("aura_colors", [[255,50,0,30],[255,50,0,60],[255,50,0,90]])
        body_col = cfg.get("body_color", [20, 20, 20])
        for i, c in enumerate(aura):
            pygame.draw.circle(s, c, (cx, cy), 38 + i * 3)
        pygame.draw.rect(s, body_col, (cx-35,cy-2,70,48), border_radius=10)
        if feat.get("has_chain", True):
            pygame.draw.arc(s, (255,215,0), (cx-12,cy,24,16), 3.14, 6.28, 3)
        pygame.draw.circle(s, (200,160,130), (cx, cy-14), 25)
        if feat.get("has_top_hat", True):
            pygame.draw.rect(s, (10,10,10), (cx-18,cy-42,36,25), border_radius=3)
            pygame.draw.rect(s, (10,10,10), (cx-24,cy-20,48,8), border_radius=2)
            pygame.draw.rect(s, (255,215,0), (cx-18,cy-20,36,4))
        if feat.get("has_monocle", True):
            pygame.draw.circle(s, (255,215,0), (cx+10,cy-16), 8, 2)
            pygame.draw.line(s, (255,215,0), (cx+10,cy-8), (cx+10,cy), 1)
        pygame.draw.arc(s, (255,255,255), (cx-10,cy-6,20,14), 3.3, 6.1, 2)
        eye_sym = feat.get("eye_symbol", "$")
        label = feat.get("label", "BOSS")
        try:
            f = pygame.font.SysFont("monospace", 12, bold=True)
            s.blit(f.render(eye_sym, True, (0,255,0)), (cx-12,cy-22))
            s.blit(f.render(eye_sym, True, (0,255,0)), (cx+4,cy-22))
            f2 = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f2.render(label, True, (255,255,0)), (cx-12,cy+30))
        except Exception:
            pass
        return s

    @staticmethod
    def gen_social_engineer(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        feat = cfg.get("features", {})
        body_col = cfg.get("body_color", [40, 120, 80])
        tie_col = cfg.get("tie_color", [60, 160, 100])
        pygame.draw.rect(s, body_col, (cx-28,cy+2,56,40), border_radius=6)
        pygame.draw.polygon(s, tie_col, [(cx-3,cy+2),(cx+3,cy+2),(cx+2,cy+20),(cx,cy+22),(cx-2,cy+20)])
        pygame.draw.circle(s, (220,180,150), (cx, cy-10), 20)
        pygame.draw.arc(s, (50,30,20), (cx-20,cy-30,40,30), 0, math.pi, 5)
        pygame.draw.circle(s, (255,255,255), (cx-8,cy-12), 6)
        pygame.draw.circle(s, (255,255,255), (cx+8,cy-12), 6)
        pygame.draw.circle(s, (0,0,0), (cx-6,cy-12), 3)
        pygame.draw.circle(s, (0,0,0), (cx+10,cy-12), 3)
        if feat.get("has_sweat", True):
            pygame.draw.circle(s, (100,200,255), (cx+18,cy-8), 3)
        if feat.get("has_phone", True):
            pygame.draw.rect(s, (40,40,40), (cx-28,cy+15,10,16), border_radius=2)
            pygame.draw.rect(s, (0,200,0), (cx-26,cy+17,6,10), border_radius=1)
        label = feat.get("label", "SPY")
        try:
            f = pygame.font.SysFont("monospace", 9, bold=True)
            s.blit(f.render(label, True, (255,200,50)), (cx-16,cy+30))
        except Exception:
            pass
        return s

    @staticmethod
    def gen_phishing(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        feat = cfg.get("features", {})
        env_col = cfg.get("envelope_color", [200, 170, 50])
        brd_col = cfg.get("border_color", [255, 215, 0])
        flp_col = cfg.get("flap_color", [180, 150, 40])
        r = pygame.Rect(cx-30, cy-10, 60, 40)
        pygame.draw.rect(s, env_col, r, border_radius=4)
        pygame.draw.rect(s, brd_col, r, width=2, border_radius=4)
        pygame.draw.polygon(s, flp_col, [(cx-30,cy-10),(cx,cy+10),(cx+30,cy-10)])
        pygame.draw.polygon(s, brd_col, [(cx-30,cy-10),(cx,cy+10),(cx+30,cy-10)], 2)
        text = feat.get("text", "$$$")
        label = feat.get("label", "GET RICH")
        sublabel = feat.get("sublabel", "QUICK!")
        try:
            f = pygame.font.SysFont("monospace", 18, bold=True)
            s.blit(f.render(text, True, (0,180,0)), (cx-14,cy-6))
            f2 = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f2.render(label, True, (255,50,50)), (cx-22,cy+22))
            s.blit(f2.render(sublabel, True, (255,50,50)), (cx-16,cy+32))
        except Exception:
            pass
        if feat.get("has_hook", True):
            hx, hy = cx+15, cy-25
            pygame.draw.line(s, (180,180,180), (hx,hy-10), (hx,hy+5), 2)
            pygame.draw.arc(s, (180,180,180), (hx-5,hy,10,12), 3.14, 6.28, 2)
        return s

    @staticmethod
    def gen_shield(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        main = cfg.get("main_color", [50, 150, 255])
        border = cfg.get("border_color", [100, 200, 255])
        check = cfg.get("check_color", [255, 255, 255])
        pts = [(cx,cy-30),(cx+25,cy-15),(cx+20,cy+15),(cx,cy+30),(cx-20,cy+15),(cx-25,cy-15)]
        pygame.draw.polygon(s, main, pts)
        pygame.draw.polygon(s, border, pts, 3)
        pygame.draw.lines(s, check, False, [(cx-10,cy),(cx-2,cy+10),(cx+12,cy-10)], 4)
        return s

    @staticmethod
    def gen_it_admin(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        feat = cfg.get("features", {})
        body_col = cfg.get("body_color", [50, 100, 200])
        pygame.draw.rect(s, body_col, (cx-25,cy+2,50,35), border_radius=6)
        pygame.draw.circle(s, (220,180,150), (cx,cy-10), 20)
        if feat.get("has_glasses", True):
            pygame.draw.circle(s, (200,200,200), (cx-8,cy-12), 7, 2)
            pygame.draw.circle(s, (200,200,200), (cx+8,cy-12), 7, 2)
            pygame.draw.line(s, (200,200,200), (cx-1,cy-12), (cx+1,cy-12), 2)
        pygame.draw.arc(s, (200,100,100), (cx-6,cy-2,12,8), 3.3, 6.1, 2)
        if feat.get("has_briefcase", True):
            pygame.draw.rect(s, (100,60,20), (cx-8,cy+24,16,12), border_radius=2)
            pygame.draw.rect(s, (140,90,30), (cx-8,cy+24,16,12), 1, border_radius=2)
            pygame.draw.rect(s, (140,90,30), (cx-3,cy+22,6,4))
        if feat.get("has_id_badge", True):
            pygame.draw.rect(s, (255,255,255), (cx+14,cy+6,10,14), border_radius=2)
            pygame.draw.circle(s, (0,150,0), (cx+19,cy+10), 3)
        return s

    @staticmethod
    def gen_lock(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        body_col = cfg.get("body_color", [220, 200, 50])
        border_col = cfg.get("border_color", [180, 160, 30])
        shackle_col = cfg.get("shackle_color", [80, 60, 10])
        pygame.draw.arc(s, shackle_col, (cx-15,cy-35,30,30), 0, math.pi, 5)
        pygame.draw.rect(s, body_col, (cx-20,cy-10,40,35), border_radius=4)
        pygame.draw.rect(s, border_col, (cx-20,cy-10,40,35), width=2, border_radius=4)
        pygame.draw.circle(s, (80,60,10), (cx,cy+2), 6)
        pygame.draw.rect(s, (80,60,10), (cx-3,cy+2,6,12))
        return s

    @staticmethod
    def _gen_pu_base(sz, cfg):
        s = pygame.Surface(sz, pygame.SRCALPHA)
        cx, cy = sz[0] // 2, sz[1] // 2
        outer = cfg.get("outer_glow", [255, 215, 0, 60])
        inner = cfg.get("inner_glow", [255, 230, 100, 40])
        pygame.draw.circle(s, outer, (cx, cy), 35)
        pygame.draw.circle(s, inner, (cx, cy), 30)
        return s, cx, cy

    @staticmethod
    def gen_pu_freeze(sz, cfg):
        base_cfg = cfg.get("base", {})
        s, cx, cy = Sprites._gen_pu_base(sz, base_cfg)
        color = cfg.get("color", [100, 200, 255])
        center = cfg.get("center_color", [200, 230, 255])
        for a in range(0, 360, 60):
            r = math.radians(a)
            x2 = cx + int(20 * math.cos(r))
            y2 = cy + int(20 * math.sin(r))
            pygame.draw.line(s, color, (cx, cy), (x2, y2), 3)
            bx = cx + int(12 * math.cos(r))
            by = cy + int(12 * math.sin(r))
            for ba in (a - 30, a + 30):
                br = math.radians(ba)
                pygame.draw.line(s, (150,220,255), (bx,by),
                                 (bx+int(6*math.cos(br)), by+int(6*math.sin(br))), 2)
        pygame.draw.circle(s, center, (cx, cy), 5)
        return s

    @staticmethod
    def gen_pu_double(sz, cfg):
        base_cfg = cfg.get("base", {})
        s, cx, cy = Sprites._gen_pu_base(sz, base_cfg)
        text = cfg.get("text", "2X")
        text_col = cfg.get("text_color", [255, 50, 50])
        try:
            f = pygame.font.SysFont("monospace", 32, bold=True)
            t = f.render(text, True, text_col)
            s.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))
        except Exception:
            pygame.draw.circle(s, text_col, (cx, cy), 15)
        return s

    @staticmethod
    def gen_pu_time(sz, cfg):
        base_cfg = cfg.get("base", {})
        s, cx, cy = Sprites._gen_pu_base(sz, base_cfg)
        clk = cfg.get("clock_color", [100, 255, 100])
        text = cfg.get("text", "+5s")
        text_col = cfg.get("text_color", [255, 255, 200])
        pygame.draw.circle(s, clk, (cx, cy), 18, 3)
        pygame.draw.line(s, clk, (cx, cy), (cx, cy-14), 3)
        pygame.draw.line(s, clk, (cx, cy), (cx+10, cy), 2)
        try:
            f = pygame.font.SysFont("monospace", 12, bold=True)
            s.blit(f.render(text, True, text_col), (cx-9, cy+20))
        except Exception:
            pass
        return s

    @staticmethod
    def gen_pu_slow(sz, cfg):
        base_cfg = cfg.get("base", {})
        s, cx, cy = Sprites._gen_pu_base(sz, base_cfg)
        color = cfg.get("color", [200, 150, 255])
        text = cfg.get("text", "SLOW")
        text_col = cfg.get("text_color", [255, 255, 200])
        pygame.draw.arc(s, color, (cx-15,cy-15,30,25), 0, math.pi, 4)
        pygame.draw.ellipse(s, color, (cx-18,cy+2,36,14))
        try:
            f = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f.render(text, True, text_col), (cx-12, cy+20))
        except Exception:
            pass
        return s

# ===========================================================================
# LEADERBOARD
# ===========================================================================

class Leaderboard:
    def __init__(self, path):
        self.path = path
        self.entries = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    entries = json.load(f)
                    # Keep old leaderboard files usable. Missing fields are
                    # handled with defaults when entries are displayed.
                    self.entries = ([e for e in entries if isinstance(e, dict)]
                                    if isinstance(entries, list) else [])
        except (json.JSONDecodeError, IOError):
            self.entries = []

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.entries, f, indent=2)
        except IOError:
            pass

    @staticmethod
    def _mode(entry):
        mode = entry.get("mode", "challenge")
        return mode if mode in GAME_MODES else "challenge"

    @staticmethod
    def _number(entry, field):
        try:
            return int(entry.get(field, 0))
        except (TypeError, ValueError):
            return 0

    def entries_for(self, mode):
        entries = [e for e in self.entries if self._mode(e) == mode]
        return sorted(entries, key=lambda e: self._number(e, "score"),
                      reverse=True)[:MAX_LEADERBOARD]

    def add(self, name, score, combo, bosses, friendlies_hit, mode):
        self.entries.append({
            "name": name, "score": score, "combo": combo,
            "bosses": bosses, "friendlies_hit": friendlies_hit,
            "mode": mode,
            "date": time.strftime("%Y-%m-%d %H:%M")})
        keep = self.entries_for(mode)
        self.entries = [e for e in self.entries
                        if self._mode(e) != mode] + keep
        self._save()

    def reset(self):
        self.entries = []
        self._save()

    def qualifies(self, score, mode):
        entries = self.entries_for(mode)
        return (len(entries) < MAX_LEADERBOARD or
                score > self._number(entries[-1], "score"))


# ===========================================================================
# HOLE (one of the nine game slots)
# ===========================================================================

class Hole:
    def __init__(self, row, col, x, y, w, h):
        self.row, self.col = row, col
        self.x, self.y, self.w, self.h = x, y, w, h
        self.clear()

    def clear(self):
        self.active = False
        self.etype = None
        self.is_enemy = False
        self.is_powerup = False
        self.pu_type = None
        self.image = None
        self.timer = 0
        self.duration = 0
        self.hit = False
        self.flash_timer = 0
        self.flash_kind = None
        self.pop = 0.0
        self.popping_up = False
        self.popping_dn = False
        self.boss_hp = 0
        self.boss_max = 0
        self.frozen = False
        self.shake_t = 0
        self.shake_xy = (0, 0)

    def spawn(self, etype, enemy, img, dur, *, powerup=False,
              pu_type=None, boss_hp=0):
        if self.active:
            return False
        self.clear()
        self.active = True
        self.etype = etype
        self.is_enemy = enemy
        self.is_powerup = powerup
        self.pu_type = pu_type
        self.image = img
        self.duration = dur
        self.timer = dur
        self.boss_hp = boss_hp
        self.boss_max = boss_hp
        self.popping_up = True
        return True
    
    def contains(self, mx, my):
        """Check if mouse coordinates fall within this hole."""
        return (self.x <= mx <= self.x + self.w and
                self.y <= my <= self.y + self.h)

    def update(self, dt, global_freeze):
        if self.popping_up:
            self.pop = min(1.0, self.pop + dt * 6)
            if self.pop >= 1.0:
                self.popping_up = False

        if self.popping_dn:
            self.pop = max(0.0, self.pop - dt * 5)
            if self.pop <= 0:
                self.popping_dn = False
                info = (self.is_enemy, self.hit, self.etype)
                self.clear()
                return info  # (was_enemy, was_hit, entity_type)

        if self.active and not self.hit and not self.popping_up:
            if not (global_freeze and self.frozen):
                self.timer -= dt * 1000
                if self.timer <= 0:
                    self.popping_dn = True

        if self.shake_t > 0:
            self.shake_t -= dt * 1000
            self.shake_xy = (random.randint(-3, 3), random.randint(-3, 3))
            if self.shake_t <= 0:
                self.shake_xy = (0, 0)

        if self.flash_timer > 0:
            self.flash_timer -= dt * 1000
            if self.flash_timer <= 0:
                self.flash_kind = None

        return None

    def whack(self):
        """Returns (result_tag, detail) — or (None, None) if nothing happens."""
        if not self.active or self.hit or self.popping_dn:
            return None, None

        # Boss: multiple hits needed
        if self.etype == "boss" and self.boss_hp > 1:
            self.boss_hp -= 1
            self.shake_t = 200
            self.flash_timer = 200
            self.flash_kind = "boss_hit"
            return "boss_hit", "boss"

        if self.is_powerup:
            self.hit = True
            self.popping_dn = True
            return "powerup", self.pu_type

        self.hit = True
        self.popping_dn = True
        self.flash_timer = 400

        if self.etype == "boss":
            self.flash_kind = "boss_ko"
            return "boss_ko", "boss"
        if self.is_enemy:
            self.flash_kind = "hit"
            return "hit", self.etype
        self.flash_kind = "bad"
        return "bad", self.etype


# ===========================================================================
# PARTICLES
# ===========================================================================

class _P:
    __slots__ = ("x", "y", "c", "vx", "vy", "life", "ml", "sz")

    def __init__(self, x, y, c, vx, vy, life, sz):
        self.x, self.y, self.c = x, y, c
        self.vx, self.vy = vx, vy
        self.life = self.ml = life
        self.sz = sz

    def tick(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 250 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        a = max(0, self.life / self.ml)
        r = max(1, int(self.sz * a))
        col = tuple(min(255, int(c * (0.3 + 0.7 * a))) for c in self.c[:3])
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)


class Particles:
    def __init__(self, cap=200):
        self.ps = []
        self.cap = cap

    def emit(self, x, y, col, n=12, spread=150, spd=200):
        for _ in range(n):
            if len(self.ps) >= self.cap:
                break
            self.ps.append(_P(
                x, y, col,
                random.uniform(-spread, spread),
                random.uniform(-spd, -spd * 0.3),
                random.uniform(0.3, 0.9),
                random.randint(2, 7)))

    def burst(self, x, y, col, n=25, spd=300):
        for _ in range(n):
            if len(self.ps) >= self.cap:
                break
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(spd * 0.3, spd)
            self.ps.append(_P(
                x, y, col,
                math.cos(a) * v, math.sin(a) * v - 100,
                random.uniform(0.4, 1.2),
                random.randint(3, 8)))

    def update(self, dt):
        self.ps = [p for p in self.ps if p.tick(dt)]

    def draw(self, surf):
        for p in self.ps:
            p.draw(surf)


# ===========================================================================
# ACTIVE POWER-UP EFFECTS TRACKER
# ===========================================================================

class Effects:
    def __init__(self):
        self.fx = {}  # name → remaining_ms

    def activate(self, name, ms):
        self.fx[name] = ms

    def update(self, dt):
        expired = []
        for k in list(self.fx):
            self.fx[k] -= dt * 1000
            if self.fx[k] <= 0:
                expired.append(k)
                del self.fx[k]
        return expired

    def on(self, name):
        return name in self.fx

    def remaining(self, name):
        return self.fx.get(name, 0)

    def clear(self):
        self.fx.clear()


# ===========================================================================
# MAIN GAME
# ===========================================================================

class Game:
    def __init__(self):
        self.audio_ok = True
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            self.audio_ok = False

        pygame.init()
        
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h

        if self.audio_ok:
            try:
                pygame.mixer.init()
            except pygame.error:
                self.audio_ok = False

        self.scr = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            pygame.FULLSCREEN | pygame.DOUBLEBUF
        )
        
        pygame.display.set_caption(GAME_TITLE)

        # Set window icon
        icon = self._make_window_icon()
        if icon:
            pygame.display.set_icon(icon)
                    
        # Custom hammer cursor
        self.hammer_surf = self._make_hammer_cursor()
        self.show_hammer = False
        self.hammer_pos = (0, 0)
        self.hammer_timer = 0
        self.hammer_swinging = False
        self.clock = pygame.time.Clock()

        self.f_lg = pygame.font.SysFont("monospace", 48, bold=True)
        self.f_md = pygame.font.SysFont("monospace", 36, bold=True)
        self.f_sm = pygame.font.SysFont("monospace", 28)
        self.f_sm_bold = pygame.font.SysFont("monospace", 28, bold=True)
        self.f_xs = pygame.font.SysFont("monospace", 20)
        self.f_xs_bold = pygame.font.SysFont("monospace", 20, bold=True)
        self.f_xx = pygame.font.SysFont("monospace", 16)
        self._keymap_fonts = {}

        self.imgs = {}
        self.snds = {}
        
        # Load theme configuration
        self._load_theme_config()

        # Load custom sprites configuration
        self._load_sprites_config()
        
        self._load_sprites()
        self._load_sounds()

        self.lb = Leaderboard(LEADERBOARD_FILE)
        self.ptcl = Particles(200)
        self.eff = Effects()

        self.selected_mode = "quick"
        self.leaderboard_mode = self.selected_mode
        self.state = "menu"
        self.post_game_idle_state = None
        self.post_game_idle_started_at = 0
        self._reset()
        self.pname = ""
        self.cur_blink = 0
        self.title_p = 0
        self.flashes = []
        self.last_tick_s = -1

    # ---- asset loading ----------------------------------------------------

    def _load_theme_config(self):
        """Load theme configuration from JSON file"""
        config_path = os.path.join(_DATA_DIR, "theme_config.json")
        
        # Default configuration
        default_config = {
            "theme": {
                "title": "Whack-a-Hacker!",
                "subtitle": "Cyber Security Whack-a-Mole",
                "game_over_title": "GAME OVER",
                "high_score_title": "NEW HIGH SCORE!",
                "score_label": "Score:"
            },
            "enemies": {
                "hacker": "HACKER",
                "apt": "APT THREAT",
                "boss": "BOSS HACKER",
                "social_engineer": "SOCIAL ENGINEER",
                "phishing": "PHISHING EMAIL"
            },
            "friendlies": {
                "shield": "SHIELD",
                "it_admin": "IT ADMIN",
                "lock": "LOCK"
            },
            "powerups": {
                "freeze": "FREEZE",
                "double": "DOUBLE POINTS",
                "time_bonus": "TIME BONUS",
                "slow_mo": "SLOW MOTION"
            },
            "descriptions": {
                "hacker": "WHACK! +2 pts",
                "apt": "WHACK! +3 pts (fast!)",
                "boss": "WHACK x3! +8 pts",
                "social_engineer": "WHACK! +3 pts",
                "phishing": "WHACK! +2 pts",
                "shield": "SKIP! -1 pt",
                "it_admin": "SKIP! -1 pt",
                "lock": "SKIP! -1 pt"
            },
            "messages": {
                "boss_spawn": "!! BOSS HACKER !!",
                "boss_hit": "BOSS HIT! ({hits_left} left)",
                "boss_ko": "BOSS K.O.! +{pts}",
                "hit_hacker": "+{pts}",
                "hit_apt": "+{pts}",
                "hit_social": "SPY CAUGHT! +{pts}",
                "hit_phishing": "PHISHING BLOCKED! +{pts}",
                "hit_friendly": "FRIENDLY HIT! {pts}",
                "combo": "COMBO x{combo}! +{pts}",
                "freeze": "FREEZE!",
                "double": "DOUBLE POINTS! +{pts}",
                "time_bonus": "+{seconds} SECONDS!",
                "slow_mo": "SLOW MOTION!",
                "speed_up": "SPEED UP!"
            },
            "ui_labels": {
                "modes": {
                    "select": "SELECT MODE",
                    "quick": "Quick Play",
                    "quick_instruction": "Hit everything!",
                    "challenge": "Cyber Challenge",
                    "challenge_instruction": "Stop threats. Protect friendlies. Collect power-ups.",
                    "quick_leaderboard": "QUICK PLAY LEADERBOARD",
                    "challenge_leaderboard": "CYBER CHALLENGE LEADERBOARD",
                    "threats_hit": "Threats Hit",
                    "threats_missed": "Threats Missed"
                },
                "guide": {
                    "title": "POINTS GUIDE",
                    "hit": "HIT",
                    "protect": "PROTECT",
                    "collect": "COLLECT",
                    "bonus_points": "BONUS POINTS",
                    "number_keys": "NUMBER KEYS 1-9 TO WHACK",
                    "hit_everything": "HIT EVERYTHING!",
                    "boss_hits": "{hits} HITS",
                    "combo_bonus": "COMBO {threshold}+  +{bonus} PT"
                },
                "stats": {
                    "hits": "Hackers Whacked",
                    "missed": "Hackers Missed",
                    "f_hits": "Friendlies Hit",
                    "ph_hits": "Phishing Traps Blocked",
                    "se_hits": "Spies Caught",
                    "bosses_k": "Bosses Defeated",
                    "pu_got": "Power-ups Collected",
                    "max_combo": "Max Combo"
                },
                "buttons": {
                    "start": "Press ENTER or Green Button to Start",
                    "leaderboard": "Press L or Yellow Button for Leaderboard",
                    "quit": "Press ESC or Red Button to Quit",
                    "play_again": "ENTER or Green Button to Play Again",
                    "menu": "M or Red Button for Menu",
                    "view_leaderboard": "L or Yellow Button for Leaderboard",
                    "enter_name": "Enter your name:",
                    "confirm_name": "ENTER to confirm (max 20 chars)"
                }
            }
        }
        
        # Initialize with defaults
        self.config = default_config
        
        # Try to load from file
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    # Update the config with file values
                    self._update_config(self.config, file_config)
        except (json.JSONDecodeError, IOError):
            # If file doesn't exist or is invalid, use defaults
            pass

        # Update window title with theme configuration
        pygame.display.set_caption(self.config["theme"]["title"])

    def _load_sprites_config(self):
        """Load custom sprites configuration from JSON file"""
        sprites_config_path = os.path.join(_DATA_DIR, "custom_sprites.json")
        self.sprites_config = {}
        try:
            if os.path.exists(sprites_config_path):
                with open(sprites_config_path, 'r') as f:
                    self.sprites_config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    def _update_config(self, target, source):
        """Update target dictionary with values from source"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_config(target[key], value)
            else:
                target[key] = value

    def _mode_config(self):
        return GAME_MODES[self.selected_mode]

    def _mode_label(self, mode=None):
        mode = mode or self.selected_mode
        return self.config["ui_labels"]["modes"].get(
            mode, GAME_MODES[mode]["label"])

    def _mode_instruction(self, mode=None):
        mode = mode or self.selected_mode
        return self.config["ui_labels"]["modes"].get(
            f"{mode}_instruction", GAME_MODES[mode]["instruction"])

    def _deep_merge(self, default, custom):
        """Deep merge two dictionaries"""
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _try_img(self, filename, sz, fallback):
        """Check user assets first, then bundled assets, then use fallback."""
        for assets_dir in [_USER_ASSETS, _BUNDLED_ASSETS]:
            path = os.path.join(assets_dir, filename)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.smoothscale(img, sz)
                except Exception:
                    pass
        return fallback

    def _load_sprites(self):
        sz = (80, 80)
        m = self.imgs

        # --- Hacker (multiple variants) ---
        m["hacker"] = []
        hacker_cfg = self.sprites_config.get("hacker", {})
        num_variants = hacker_cfg.get("variants", 3)
        custom_colors = hacker_cfg.get("colors", [])
        custom_features = hacker_cfg.get("features", {})
        
        filenames = MOLE_IMAGE_PATHS.get("hacker", [])
        for i in range(max(num_variants, len(filenames))):
            # Try PNG first
            if i < len(filenames):
                png = self._try_img(filenames[i], sz, None)
                if png:
                    m["hacker"].append(png)
                    continue
            # Use custom config sprite if config exists, else default
            if custom_colors or custom_features:
                default_colors = [(200, 40, 40), (180, 50, 180), (160, 60, 40)]
                colors = custom_colors if custom_colors else default_colors
                col = colors[i % len(colors)]
                m["hacker"].append(Sprites.gen_hacker(sz, i, col, custom_features))
            else:
                m["hacker"].append(Sprites.hacker(sz, i))

        # --- Single-variant enemies ---
        enemy_map = [
            ("apt",              Sprites.apt,              Sprites.gen_apt),
            ("boss",             Sprites.boss,             Sprites.gen_boss),
            ("social_engineer",  Sprites.social_engineer,  Sprites.gen_social_engineer),
            ("phishing",         Sprites.phishing,         Sprites.gen_phishing),
        ]
        for key, default_gen, custom_gen in enemy_map:
            filenames = MOLE_IMAGE_PATHS.get(key, [])
            fn = filenames[0] if filenames else ""
            png = self._try_img(fn, sz, None)
            if png:
                m[key] = [png]
            elif key in self.sprites_config:
                m[key] = [custom_gen(sz, self.sprites_config[key])]
            else:
                m[key] = [default_gen(sz)]

        # --- Friendlies ---
        friendly_map = [
            ("shield",    Sprites.shield,    Sprites.gen_shield),
            ("it_admin",  Sprites.it_admin,  Sprites.gen_it_admin),
            ("lock",      Sprites.lock,      Sprites.gen_lock),
        ]
        for key, default_gen, custom_gen in friendly_map:
            filenames = FRIENDLY_IMAGE_PATHS.get(key, [])
            fn = filenames[0] if filenames else ""
            png = self._try_img(fn, sz, None)
            if png:
                m[key] = [png]
            elif key in self.sprites_config:
                m[key] = [custom_gen(sz, self.sprites_config[key])]
            else:
                m[key] = [default_gen(sz)]

        # --- Power-ups ---
        pu_cfg = self.sprites_config.get("powerups", {})
        pu_map = [
            ("pu_freeze",     "freeze",     Sprites.pu_freeze,  Sprites.gen_pu_freeze),
            ("pu_double",     "double",     Sprites.pu_double,  Sprites.gen_pu_double),
            ("pu_time_bonus", "time_bonus", Sprites.pu_time,    Sprites.gen_pu_time),
            ("pu_slow_mo",    "slow_mo",    Sprites.pu_slow,    Sprites.gen_pu_slow),
        ]
        for img_key, cfg_key, default_gen, custom_gen in pu_map:
            if cfg_key in pu_cfg:
                m[img_key] = [custom_gen(sz, pu_cfg[cfg_key])]
            else:
                m[img_key] = [default_gen(sz)]

    def _load_sounds(self):
        if not self.audio_ok:
            return
        try:
            s = self.snds
            s["hit"] = SFX.whack_hit()
            s["miss"] = SFX.whack_miss()
            s["friendly"] = SFX.friendly_hit()
            s["phishing"] = SFX.phishing_trap()
            s["social"] = SFX.social_hit()
            s["boss_hit"] = SFX.boss_hit()
            s["boss_ko"] = SFX.boss_defeated()
            s["pu"] = SFX.powerup()
            s["freeze"] = SFX.freeze()
            s["speed"] = SFX.speed_up()
            s["over"] = SFX.game_over()
            s["tick"] = SFX.tick()
            s["start"] = SFX.game_start()
            s["combo"] = {i: SFX.combo(i) for i in range(1, 15)}
        except Exception:
            self.audio_ok = False

    def _play(self, name, combo_lvl=None):
        if not self.audio_ok:
            return
        try:
            if name == "combo" and combo_lvl is not None:
                snd = self.snds.get("combo", {}).get(min(combo_lvl, 14))
            else:
                snd = self.snds.get(name)
            if snd:
                snd.play()
        except Exception:
            pass

    # ---- custom hammer cursor --------------------------------------------------

    def _make_hammer_cursor(self):
        sz = 40
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        # Handle
        pygame.draw.line(s, (160, 120, 60), (10, 38), (22, 18), 5)
        pygame.draw.line(s, (130, 95, 45), (11, 37), (23, 17), 2)
        # Head
        pygame.draw.rect(s, (140, 140, 150), (14, 4, 22, 16), border_radius=3)
        pygame.draw.rect(s, (180, 180, 190), (14, 4, 22, 16), 2, border_radius=3)
        # Shine
        pygame.draw.line(s, (220, 220, 230), (18, 7), (18, 14), 2)
        return s

    # ---- game state -------------------------------------------------------

    def _reset(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hits = 0
        self.f_hits = 0
        self.ph_hits = 0
        self.se_hits = 0
        self.missed = 0
        self.bosses_k = 0
        self.pu_got = 0
        self.time_left = GAME_DURATION
        self.spawn_t = 800
        self.diff = 0
        self.max_active = INITIAL_MAX_ACTIVE
        self.boss_t = BOSS_FIRST_SPAWN
        self.boss_up = False
        self.pu_t = random.uniform(POWERUP_INTERVAL_MIN, POWERUP_INTERVAL_MAX)
        self.pu_up = False
        self.mode_intro_t = 2200
        self.last_tick_s = -1
        self.eff.clear()
        self.ptcl.ps = []
        self.flashes = []

        self.holes = []
        gx = (self.screen_width - GRID_COLS * HOLE_WIDTH) // 2
        gy = 135
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = gx + c * HOLE_WIDTH + (HOLE_WIDTH - 140) // 2
                y = gy + r * HOLE_HEIGHT + (HOLE_HEIGHT - 120) // 2
                self.holes.append(Hole(r, c, x, y, 140, 120))

    def _hole(self, r, c):
        for h in self.holes:
            if h.row == r and h.col == c:
                return h
        return None

    def _flash(self, txt, col, ms=800):
        self.flashes.append([txt, col, ms])

    # ---- spawn logic ------------------------------------------------------

    def _img(self, key):
        ls = self.imgs.get(key, [])
        return random.choice(ls) if ls else None

    def _dur(self, etype):
        red = self.diff * SPEED_REDUCTION_MS
        slow = 1.5 if self.eff.on("slow_mo") else 1.0
        lo = max(400, MOLE_MIN_SHOW_TIME - red)
        hi = max(600, MOLE_MAX_SHOW_TIME - red)
        base = random.randint(int(lo), int(hi))
        mult = {"apt": 0.6, "boss": BOSS_SHOW_TIME_MULT,
                "social_engineer": 0.9}.get(etype, 1.0)
        return int(base * mult * slow)

    def _choose_type(self):
        allowed = (SPAWN_WEIGHTS if self._mode_config()["friendlies_enabled"]
                   else {key: weight for key, weight in SPAWN_WEIGHTS.items()
                         if key in self._ENEMIES})
        types = list(allowed.keys())
        weights = list(allowed.values())
        return random.choices(types, weights=weights, k=1)[0]

    _ENEMIES = {"hacker", "apt", "boss", "social_engineer", "phishing"}

    def _spawn(self):
        avail = [h for h in self.holes if not h.active]
        if not avail:
            return
        if sum(1 for h in self.holes if h.active) >= self.max_active:
            return
        hole = random.choice(avail)
        et = self._choose_type()
        img = self._img(et)
        if not img:
            return
        hole.spawn(et, et in self._ENEMIES, img, self._dur(et))
        if self.eff.on("freeze"):
            hole.frozen = True

    def _spawn_boss(self):
        if self.boss_up:
            return
        avail = [h for h in self.holes if not h.active]
        if not avail:
            return
        hole = random.choice(avail)
        img = self._img("boss")
        if not img:
            return
        hole.spawn("boss", True, img, self._dur("boss"),
                   boss_hp=BOSS_HITS_REQUIRED)
        if self.eff.on("freeze"):
            hole.frozen = True
        self.boss_up = True
        self._flash(self.config["messages"]["boss_spawn"], (255, 100, 0), 1500)

    def _spawn_pu(self):
        if self.pu_up:
            return
        avail = [h for h in self.holes if not h.active]
        if not avail:
            return
        hole = random.choice(avail)
        pt = random.choice(["freeze", "double", "time_bonus", "slow_mo"])
        key = f"pu_{pt}"
        img = self._img(key)
        if not img:
            return
        hole.spawn(key, False, img, POWERUP_SHOW_TIME,
                   powerup=True, pu_type=pt)
        if self.eff.on("freeze"):
            hole.frozen = True
        self.pu_up = True

    # ---- whack handler ----------------------------------------------------

    def _whack(self, r, c):
        h = self._hole(r, c)
        if not h:
            return
        px, py = h.x + h.w // 2, h.y + h.h // 2

        if not h.active or h.hit:
            h.flash_timer = 200
            h.flash_kind = "miss"
            self._play("miss")
            return

        tag, detail = h.whack()

        if tag is None:
            h.flash_timer = 200
            h.flash_kind = "miss"
            self._play("miss")
            return

        mul = 2 if self.eff.on("double") else 1

        if tag == "boss_hit":
            self._play("boss_hit")
            self.ptcl.emit(px, py, (255, 150, 0), 8)
            self._flash(self.config["messages"]["boss_hit"].format(hits_left=h.boss_hp), (255, 150, 0), 600)

        elif tag == "boss_ko":
            pts = SCORE_HIT_BOSS * mul
            self.score += pts
            self.bosses_k += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.hits += 1
            self.boss_up = False
            self._play("boss_ko")
            self.ptcl.burst(px, py, C_COMBO, 30)
            self._flash(self.config["messages"]["boss_ko"].format(pts=pts), C_COMBO, 1500)

        elif tag == "powerup":
            self._activate_pu(detail)
            self.pu_up = False
            self.pu_got += 1
            self._play("pu")
            self.ptcl.burst(px, py, C_PU_GLOW, 15)

        elif tag == "hit":
            base = {"hacker": SCORE_HIT_HACKER, "apt": SCORE_HIT_APT,
                    "social_engineer": SCORE_HIT_SOCIAL_ENGINEER,
                    "phishing": SCORE_HIT_PHISHING
                    }.get(detail, SCORE_HIT_HACKER)
            pts = base * mul
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.hits += 1
            if detail == "social_engineer":
                self.se_hits += 1
                self._play("social")
                self._flash(self.config["messages"]["hit_social"].format(pts=pts), (100, 255, 200), 800)
            elif detail == "phishing":
                pts = SCORE_HIT_PHISHING
                self.ph_hits += 1
                self._play("phishing")
                self._flash(self.config["messages"]["hit_phishing"].format(pts=pts), C_TEXT, 800)
            elif detail != "social_engineer":
                self._play("hit")
                self._flash(self.config["messages"]["hit_hacker"].format(pts=pts), C_TEXT, 500)
            if self.combo >= COMBO_THRESHOLD:
                bonus = COMBO_BONUS * mul
                pts += bonus
                self._play("combo", self.combo)
                self._flash(self.config["messages"]["combo"].format(combo=self.combo, pts=pts), C_COMBO, 600)
            self.score += pts
            if detail == "social_engineer":
                self.ptcl.emit(px, py, (100, 255, 200), 15)
            else:
                self._play("hit")
                self.ptcl.emit(px, py, (0, 255, 200), 12)

        elif tag == "bad":
            pts = SCORE_HIT_FRIENDLY
            self.f_hits += 1
            self._play("friendly")
            self._flash(self.config["messages"]["hit_friendly"].format(pts=pts), C_WARNING, 800)
            self.score += pts
            self.combo = 0 if detail != "phishing" else self.combo
            self.ptcl.emit(px, py, (255, 50, 50), 8)

    def _activate_pu(self, pt):
        if pt == "freeze":
            self.eff.activate("freeze", POWERUP_FREEZE_DUR)
            for h in self.holes:
                if h.active:
                    h.frozen = True
            self._flash(self.config["messages"]["freeze"], C_FREEZE, 1000)
            self._play("freeze")
        elif pt == "double":
            self.eff.activate("double", POWERUP_DOUBLE_DUR)
            self._flash(self.config["messages"]["double"], C_DOUBLE, 1000)
        elif pt == "time_bonus":
            self.time_left += POWERUP_TIME_BONUS
            self._flash(self.config["messages"]["time_bonus"].format(seconds=POWERUP_TIME_BONUS), C_TIME, 1000)
        elif pt == "slow_mo":
            self.eff.activate("slow_mo", POWERUP_SLOW_DUR)
            self._flash(self.config["messages"]["slow_mo"], C_SLOW, 1000)

    # ---- update -----------------------------------------------------------

    def _update_play(self, dt):
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0
            self._play("over")
            self.state = ("name" if self.lb.qualifies(
                self.score, self.selected_mode) else "over")
            self.pname = ""
            return

        sec = int(self.time_left)
        if self.time_left <= 10 and sec != self.last_tick_s:
            self.last_tick_s = sec
            self._play("tick")

        expired_fx = self.eff.update(dt)
        if "freeze" in expired_fx:
            for h in self.holes:
                h.frozen = False

        elapsed = GAME_DURATION - self.time_left
        new_diff = int(elapsed // RAMP_INTERVAL)
        if new_diff != self.diff:
            self.diff = new_diff
            self.max_active = min(9, INITIAL_MAX_ACTIVE + self.diff)
            self._flash(self.config["messages"]["speed_up"], (255, 200, 0), 1000)
            self._play("speed")

        frozen = self.eff.on("freeze")

        self.boss_t -= dt
        if self.boss_t <= 0 and not self.boss_up:
            self._spawn_boss()
            self.boss_t = BOSS_SPAWN_INTERVAL

        if self._mode_config()["powerups_enabled"]:
            self.pu_t -= dt
            if self.pu_t <= 0 and not self.pu_up:
                self._spawn_pu()
                self.pu_t = random.uniform(POWERUP_INTERVAL_MIN,
                                           POWERUP_INTERVAL_MAX)

        if not frozen:
            self.spawn_t -= dt * 1000
            if self.spawn_t <= 0:
                self._spawn()
                red = self.diff * 50
                lo = max(100, MOLE_MIN_SPAWN_DELAY - red)
                hi = max(300, MOLE_MAX_SPAWN_DELAY - red)
                self.spawn_t = random.randint(int(lo), int(hi))

        for h in self.holes:
            info = h.update(dt, frozen)
            if info:
                was_enemy, was_hit, etype = info
                if was_enemy and not was_hit:
                    self.missed += 1
                    self.combo = 0
                if etype == "boss" and not was_hit:
                    self.boss_up = False
                if etype and etype.startswith("pu_"):
                    self.pu_up = False

        self.ptcl.update(dt)
        self.flashes = [[t, c, ms - dt * 1000]
                        for t, c, ms in self.flashes if ms - dt * 1000 > 0]
        self.mode_intro_t = max(0, self.mode_intro_t - dt * 1000)
        
        # Hammer swing animation
        if self.hammer_timer > 0:
            self.hammer_timer -= dt * 1000
            if self.hammer_timer <= 0:
                self.hammer_swinging = False

    # ---- drawing ----------------------------------------------------------

    def _draw_hole(self, h):
        # base ellipse
        pygame.draw.ellipse(self.scr, C_HOLE,
                            (h.x, h.y + h.h - 25, h.w, 25))
        pygame.draw.ellipse(self.scr, C_HOLE_BORDER,
                            (h.x, h.y + h.h - 25, h.w, 25), 2)
        # number label
        num = (2 - h.row) * 3 + h.col + 1
        lbl = self.f_xs.render(str(num), True, (100, 100, 120))
        self.scr.blit(lbl, (h.x + h.w // 2 - lbl.get_width() // 2,
                             h.y + h.h - 18))

        # entity sprite
        if h.active and h.image and h.pop > 0:
            iw, ih = h.image.get_size()
            sw = int(iw * min(1.0, h.pop + 0.2))
            sh = int(ih * h.pop)
            if sw > 0 and sh > 0:
                img = pygame.transform.scale(h.image, (sw, sh))
                dx = h.x + (h.w - sw) // 2 + h.shake_xy[0]
                dy = h.y + h.h - 25 - sh + h.shake_xy[1]

                # friendly glow
                if (not h.is_enemy and not h.is_powerup):
                    g = pygame.Surface((sw + 8, sh + 8), pygame.SRCALPHA)
                    pygame.draw.rect(g, (50, 255, 100, 60), g.get_rect(),
                                     border_radius=8)
                    self.scr.blit(g, (dx - 4, dy - 4))

                # powerup glow
                if h.is_powerup:
                    pulse = abs(math.sin(pygame.time.get_ticks() / 200))
                    g = pygame.Surface((sw + 12, sh + 12), pygame.SRCALPHA)
                    pygame.draw.rect(g, (255, 215, 0, int(40 + 40 * pulse)),
                                     g.get_rect(), border_radius=10)
                    self.scr.blit(g, (dx - 6, dy - 6))

                # freeze tint
                if h.frozen and self.eff.on("freeze"):
                    ice = pygame.Surface((sw, sh), pygame.SRCALPHA)
                    ice.fill((100, 200, 255, 60))
                    img.blit(ice, (0, 0))

                self.scr.blit(img, (dx, dy))

                # boss HP bar
                if h.etype == "boss" and h.boss_max > 0 and not h.hit:
                    bw, bh = 60, 8
                    bx = h.x + (h.w - bw) // 2
                    by = dy - 14
                    frac = h.boss_hp / h.boss_max
                    pygame.draw.rect(self.scr, C_BOSS_HP_BG,
                                     (bx, by, bw, bh), border_radius=3)
                    pygame.draw.rect(self.scr, C_BOSS_HP,
                                     (bx, by, int(bw * frac), bh),
                                     border_radius=3)
                    pygame.draw.rect(self.scr, (200, 200, 200),
                                     (bx, by, bw, bh), 1, border_radius=3)

        # flash overlay
        if h.flash_timer > 0 and h.flash_kind:
            a = int(180 * (h.flash_timer / 400))
            fs = pygame.Surface((h.w, h.h), pygame.SRCALPHA)
            label = ""
            if h.flash_kind == "hit":
                fs.fill((*C_HIT_FLASH[:3], a))
                label = "HIT!"
            elif h.flash_kind == "boss_ko":
                fs.fill((255, 215, 0, a))
                label = "K.O.!"
            elif h.flash_kind == "boss_hit":
                fs.fill((255, 150, 0, a))
                label = "HIT!"
            elif h.flash_kind == "bad":
                fs.fill((*C_MISS_FLASH[:3], a))
                label = "NO!"
            elif h.flash_kind == "miss":
                fs.fill((100, 100, 100, a // 3))
            self.scr.blit(fs, (h.x, h.y))
            if label:
                t = self.f_sm.render(label, True, (255, 255, 255))
                self.scr.blit(t, (h.x + h.w // 2 - t.get_width() // 2,
                                   h.y + h.h // 2 - t.get_height() // 2))

    def _draw_hud(self):
        self.scr.blit(self.f_md.render(f"Score: {self.score}", True, C_SCORE),
                      (20, 12))
        mode_text = self.f_xs.render(self._mode_label().upper(), True,
                                     C_HOLE_BORDER)
        self.scr.blit(mode_text,
                      (self.screen_width // 2 - mode_text.get_width() // 2, 12))
        if self.combo >= 2:
            col = C_COMBO if self.combo >= COMBO_THRESHOLD else (200, 200, 200)
            self.scr.blit(
                self.f_sm.render(f"Combo: {self.combo}x", True, col),
                (20, 46))

        # timer bar
        bw, bh = 280, 22
        bx = self.screen_width - bw - 20
        by = 15
        frac = max(0, self.time_left / GAME_DURATION)
        tc = C_TIMER if frac > 0.15 else C_TIMER_LOW
        pygame.draw.rect(self.scr, (40, 40, 60), (bx, by, bw, bh),
                         border_radius=5)
        if frac > 0:
            pygame.draw.rect(self.scr, tc,
                             (bx, by, int(bw * frac), bh), border_radius=5)
        pygame.draw.rect(self.scr, (100, 100, 120), (bx, by, bw, bh),
                         2, border_radius=5)
        tt = self.f_sm.render(f"{int(self.time_left)}s", True, C_SCORE)
        self.scr.blit(tt, (bx + bw // 2 - tt.get_width() // 2, by + 1))

        # active effects
        ey = by + bh + 6
        for name, rem in self.eff.fx.items():
            rs = rem / 1000
            col, lbl = {
                "freeze": (C_FREEZE, f"FREEZE {rs:.1f}s"),
                "double": (C_DOUBLE, f"2X PTS {rs:.1f}s"),
                "slow_mo": (C_SLOW, f"SLOW {rs:.1f}s"),
            }.get(name, ((200, 200, 200), f"{name} {rs:.1f}s"))
            et = self.f_xs.render(lbl, True, col)
            pill = pygame.Rect(bx + bw - et.get_width() - 12, ey - 2,
                               et.get_width() + 10, et.get_height() + 4)
            pygame.draw.rect(self.scr, (20, 20, 40), pill, border_radius=8)
            pygame.draw.rect(self.scr, col, pill, 1, border_radius=8)
            self.scr.blit(et, (pill.x + 5, pill.y + 2))
            ey += et.get_height() + 8

        # flashes
        fy = 95
        for txt, col, _ in self.flashes:
            ft = self.f_md.render(txt, True, col)
            self.scr.blit(ft, (self.screen_width // 2 - ft.get_width() // 2, fy))
            fy += 32

        if self.mode_intro_t > 0:
            instruction = self.f_sm.render(
                self._mode_instruction().upper(), True, C_COMBO)
            self.scr.blit(instruction,
                          (self.screen_width // 2 - instruction.get_width() // 2,
                           62))

        # footer
        self.scr.blit(
            self.f_xs.render("Numpad 1-9: Whack  |  ESC/Red Button: Menu", True,
                             (100, 100, 120)),
            (self.screen_width // 2 - 150, self.screen_height - 25))

    def _draw_play(self):
        self.scr.fill(C_BG)

        if self.eff.on("freeze"):
            ov = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            ov.fill((100, 200, 255, 15))
            self.scr.blit(ov, (0, 0))
        if self.eff.on("double"):
            p = abs(math.sin(pygame.time.get_ticks() / 300))
            ov = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            ov.fill((255, 215, 0, int(8 * p)))
            self.scr.blit(ov, (0, 0))

        gw = GRID_COLS * HOLE_WIDTH + 20
        gh = GRID_ROWS * HOLE_HEIGHT + 20
        gx = (self.screen_width - gw) // 2
        pygame.draw.rect(self.scr, (20, 20, 40), (gx, 125, gw, gh),
                         border_radius=12)
        pygame.draw.rect(self.scr, (0, 80, 120), (gx, 125, gw, gh),
                         1, border_radius=12)

        for h in self.holes:
            self._draw_hole(h)
        self.ptcl.draw(self.scr)
        self._draw_hud()

        # Hammer cursor
        if self.hammer_pos:
            img = self.hammer_surf
            if self.hammer_swinging:
                img = pygame.transform.rotate(self.hammer_surf, -30)
            self.scr.blit(img, (self.hammer_pos[0] - 10,
                                self.hammer_pos[1] - 10))

    def _draw_guide_item(self, key, label, details, center_x, y,
                         color=C_TEXT, size=56):
        """Draw a centered label, pixel-art sprite, and detail lines."""
        name = self.f_xx.render(label, True, color)
        self.scr.blit(name, (center_x - name.get_width() // 2, y))
        sprite_y = y + name.get_height() + 2
        images = self.imgs.get(key, [])
        if images:
            sprite = pygame.transform.scale(images[0], (size, size))
            self.scr.blit(sprite, (center_x - size // 2, sprite_y))
        detail_lines = ((details,) if isinstance(details, str)
                        else tuple(details))
        detail_y = sprite_y + size + 1
        for detail in detail_lines:
            value = self.f_xx.render(detail, True, (190, 195, 210))
            self.scr.blit(value,
                          (center_x - value.get_width() // 2, detail_y))
            detail_y += value.get_height()
        return detail_y

    def _draw_guide_row(self, items, region, y, sprite_size):
        """Evenly distribute guide items across a bounded region."""
        column_width = region.width / len(items)
        bottom = y
        for index, (key, label, details, color) in enumerate(items):
            center_x = int(region.x + column_width * (index + 0.5))
            bottom = max(bottom, self._draw_guide_item(
                key, label, details, center_x, y, color, sprite_size))
        return bottom

    def _draw_guide_group(self, heading, items, region, y, color,
                          sprite_size, box_bottom=None, center_content=False):
        """Draw a bordered category with a centered heading and item row."""
        title = self.f_xs_bold.render(heading, True, color)
        title_x = region.centerx - title.get_width() // 2
        row_y = y + title.get_height() + 2
        if box_bottom is not None and center_content:
            detail_count = max(
                (1 if isinstance(details, str) else len(tuple(details)))
                for _, _, details, _ in items)
            natural_height = (self.f_xx.get_height() + 2 + sprite_size + 1
                              + detail_count * self.f_xx.get_height())
            available_height = box_bottom - 5 - row_y
            row_y += max(0, (available_height - natural_height) // 2)
        content_bottom = self._draw_guide_row(
            items, region, row_y, sprite_size)
        box_top = y + title.get_height() // 2
        bottom = box_bottom if box_bottom is not None else content_bottom + 5
        box = pygame.Rect(region.x, box_top, region.width, bottom - box_top)
        pygame.draw.rect(self.scr, color, box, 1, border_radius=7)
        legend_bg = pygame.Rect(title_x - 7, y, title.get_width() + 14,
                                title.get_height())
        pygame.draw.rect(self.scr, C_BG, legend_bg)
        self.scr.blit(title, (title_x, y))
        return box.bottom

    def _guide_group_bottom(self, items, y, sprite_size):
        """Calculate a category's natural bottom edge without drawing it."""
        detail_count = max(
            (1 if isinstance(details, str) else len(tuple(details)))
            for _, _, details, _ in items)
        item_height = (self.f_xx.get_height() + 2 + sprite_size + 1
                       + detail_count * self.f_xx.get_height())
        return y + self.f_xs_bold.get_height() + 2 + item_height + 5

    def _draw_bonus_guide(self, heading, combo, region, y, color):
        """Draw the combo rule in its own bordered bonus category."""
        title = self.f_xs_bold.render(heading, True, color)
        combo_text = self.f_xs_bold.render(combo, True, color)
        title_x = region.centerx - title.get_width() // 2
        combo_y = y + title.get_height() + 2
        box_top = y + title.get_height() // 2
        box = pygame.Rect(region.x, box_top, region.width,
                          combo_y + combo_text.get_height() + 5 - box_top)
        pygame.draw.rect(self.scr, color, box, 1, border_radius=7)
        legend_bg = pygame.Rect(title_x - 7, y, title.get_width() + 14,
                                title.get_height())
        pygame.draw.rect(self.scr, C_BG, legend_bg)
        self.scr.blit(title, (title_x, y))
        self.scr.blit(combo_text,
                      (region.centerx - combo_text.get_width() // 2, combo_y))
        return box.bottom

    def _keymap_font(self, size):
        """Cache the responsive bold fonts used by the keymap guide."""
        if size not in self._keymap_fonts:
            self._keymap_fonts[size] = pygame.font.SysFont(
                "monospace", size, bold=True)
        return self._keymap_fonts[size]

    def _keymap_layout(self, y):
        """Choose the largest keymap typography that fits above the footer."""
        footer_y = self.screen_height - self.f_xx.get_height() - 12
        band_height = max(0, footer_y - y)
        selected = None
        for grid_size in range(34, 7, -1):
            heading_size = min(26, max(10, grid_size - 6))
            heading_font = self._keymap_font(heading_size)
            grid_font = self._keymap_font(grid_size)
            heading_gap = max(2, min(8, grid_size // 5))
            row_gap = max(2, min(8, grid_size // 5))
            line_step = grid_font.get_height() + row_gap
            content_height = (heading_font.get_height() + heading_gap
                              + grid_font.get_height() + 2 * line_step)
            if content_height + 8 <= band_height:
                selected = {
                    "heading_size": heading_size,
                    "grid_size": grid_size,
                    "heading_font": heading_font,
                    "grid_font": grid_font,
                    "heading_gap": heading_gap,
                    "row_gap": row_gap,
                    "line_step": line_step,
                    "content_height": content_height,
                }
                break

        if selected is None:
            heading_font = self._keymap_font(8)
            grid_font = self._keymap_font(8)
            selected = {
                "heading_size": 8,
                "grid_size": 8,
                "heading_font": heading_font,
                "grid_font": grid_font,
                "heading_gap": 2,
                "row_gap": 2,
                "line_step": grid_font.get_height() + 2,
            }
            selected["content_height"] = (
                heading_font.get_height() + selected["heading_gap"]
                + grid_font.get_height() + 2 * selected["line_step"])

        selected["y"] = y + max(0, (band_height
                                     - selected["content_height"]) // 2)
        selected["footer_y"] = footer_y
        return selected

    def _draw_keymap_guide(self, y):
        """Show a responsive spatial number-key mapping above the footer."""
        label = self.config["ui_labels"]["guide"]["number_keys"]
        layout = self._keymap_layout(y)
        heading = layout["heading_font"].render(
            label, True, (120, 130, 150))
        self.scr.blit(heading,
                      (self.screen_width // 2 - heading.get_width() // 2,
                       layout["y"]))
        grid_y = (layout["y"] + heading.get_height()
                  + layout["heading_gap"])
        lines = ("7   8   9", "4   5   6", "1   2   3")
        for index, line in enumerate(lines):
            text = layout["grid_font"].render(
                line, True, (120, 130, 150))
            self.scr.blit(text,
                          (self.screen_width // 2 - text.get_width() // 2,
                           grid_y + index * layout["line_step"]))

    def _draw_points_guide(self, y):
        """Draw the illustrated guide for the currently selected mode."""
        labels = self.config["ui_labels"]["guide"]
        heading = self.f_sm_bold.render(
            labels["title"], True, (180, 180, 200))
        self.scr.blit(heading,
                      (self.screen_width // 2 - heading.get_width() // 2, y))

        guide_width = max(960, min(1120, int(self.screen_width * 0.80)))
        guide_width = min(guide_width, self.screen_width - 40)
        guide_region = pygame.Rect(
            (self.screen_width - guide_width) // 2, 0, guide_width, 0)
        target_size = max(56, min(68, int(self.screen_width * 0.045)))
        lower_size = max(40, min(54, int(self.screen_height * 0.056)))

        enemy_items = [
            ("hacker", self.config["enemies"]["hacker"],
             f"+{SCORE_HIT_HACKER} PT", (220, 60, 60)),
            ("apt", self.config["enemies"]["apt"],
             f"+{SCORE_HIT_APT} PT", (190, 80, 210)),
            ("social_engineer", self.config["enemies"]["social_engineer"],
             f"+{SCORE_HIT_SOCIAL_ENGINEER} PT", (80, 200, 150)),
            ("phishing", self.config["enemies"].get(
                "phishing", self.config["friendlies"].get(
                    "phishing", "PHISHING EMAIL")),
             f"+{SCORE_HIT_PHISHING} PT", (220, 140, 50)),
            ("boss", self.config["enemies"]["boss"],
             f"+{SCORE_HIT_BOSS} PT · " + labels["boss_hits"].format(
                 hits=BOSS_HITS_REQUIRED), (255, 100, 0)),
        ]
        hit_y = y + heading.get_height() + 2
        enemy_bottom = self._draw_guide_group(
            labels["hit"], enemy_items, guide_region, hit_y,
            C_WARNING, target_size)

        lower_y = enemy_bottom + 5
        combo = labels["combo_bonus"].format(
            threshold=COMBO_THRESHOLD, bonus=COMBO_BONUS)
        if self.selected_mode == "quick":
            rule = self.f_md.render(labels["hit_everything"], True, C_COMBO)
            self.scr.blit(rule,
                          (self.screen_width // 2 - rule.get_width() // 2,
                           lower_y))
            bonus_width = min(520, int(guide_width * 0.52))
            bonus_region = pygame.Rect(
                self.screen_width // 2 - bonus_width // 2, 0,
                bonus_width, 0)
            bonus_bottom = self._draw_bonus_guide(
                labels["bonus_points"], combo, bonus_region,
                lower_y + rule.get_height() + 4, C_TEXT)
            self._draw_keymap_guide(bonus_bottom)
            return

        gap = max(24, int(guide_width * 0.025))
        protect_width = int((guide_width - gap) * 0.42)
        protect_region = pygame.Rect(
            guide_region.x, 0, protect_width, 0)
        collect_region = pygame.Rect(
            protect_region.right + gap, 0,
            guide_region.right - protect_region.right - gap, 0)
        friendly_items = [
            ("shield", self.config["friendlies"]["shield"]),
            ("it_admin", self.config["friendlies"]["it_admin"]),
            ("lock", self.config["friendlies"]["lock"]),
        ]
        friendly_items = [
            (key, label, f"{SCORE_HIT_FRIENDLY} PT", C_HOLE_BORDER)
            for key, label in friendly_items
        ]

        powerup_items = [
            ("pu_freeze", self.config["powerups"]["freeze"]),
            ("pu_double", self.config["powerups"]["double"]),
            ("pu_time_bonus", self.config["powerups"]["time_bonus"]),
            ("pu_slow_mo", self.config["powerups"]["slow_mo"]),
        ]
        powerup_items = [(key, label, (), C_COMBO)
                         for key, label in powerup_items]
        shared_bottom = self._guide_group_bottom(
            friendly_items, lower_y, lower_size)
        protect_bottom = self._draw_guide_group(
            labels["protect"], friendly_items, protect_region, lower_y,
            C_HOLE_BORDER, lower_size, shared_bottom)
        collect_bottom = self._draw_guide_group(
            labels["collect"], powerup_items, collect_region, lower_y,
            C_COMBO, lower_size, shared_bottom, center_content=True)
        bonus_width = min(520, int(guide_width * 0.52))
        bonus_region = pygame.Rect(
            self.screen_width // 2 - bonus_width // 2, 0,
            bonus_width, 0)
        bonus_bottom = self._draw_bonus_guide(
            labels["bonus_points"], combo, bonus_region,
            max(protect_bottom, collect_bottom) + 5, C_TEXT)
        self._draw_keymap_guide(bonus_bottom)

    def _draw_menu(self):
        self.scr.fill(C_BG)
        self.title_p += 0.05
        p = abs(math.sin(self.title_p)) * 30
        tc = (int(min(255, C_TEXT[0] + p)), C_TEXT[1],
            int(min(255, C_TEXT[2] + p)))

        title_font = pygame.font.SysFont("monospace", 64, bold=True)
        t = title_font.render(self.config["theme"]["title"], True, tc)
        y = 5
        self.scr.blit(t, (self.screen_width // 2 - t.get_width() // 2, y))

        subtitle_font = pygame.font.SysFont("monospace", 36, bold=True)
        t2 = subtitle_font.render(self.config["theme"]["subtitle"], True,
                                (100, 220, 150))
        y += 65
        self.scr.blit(t2, (self.screen_width // 2 - t2.get_width() // 2, y))

        y += 49
        select = self.f_sm.render(
            self.config["ui_labels"]["modes"]["select"], True,
            (180, 180, 200))
        self.scr.blit(select,
                      (self.screen_width // 2 - select.get_width() // 2, y))
        y += 35

        mode_cards = self._menu_mode_rects(y)
        for key, number in (("quick", "1"), ("challenge", "2")):
            selected = key == self.selected_mode
            box = mode_cards[key]
            pygame.draw.rect(self.scr, (28, 45, 58) if selected else (25, 25, 45),
                             box, border_radius=10)
            pygame.draw.rect(self.scr, C_COMBO if selected else (70, 90, 110),
                             box, 3 if selected else 1, border_radius=10)
            marker = ">" if selected else " "
            label = f"{marker} {number} — {self._mode_label(key).upper()}"
            self.scr.blit(self.f_md.render(label, True,
                                           C_COMBO if selected else C_TEXT),
                          (box.x + 22, box.y + 6))
            self.scr.blit(self.f_xs.render(self._mode_instruction(key), True,
                                           (180, 190, 205)),
                          (box.x + 70, box.y + 48))
            y += 78

        self._draw_points_guide(y + 4)

        controls = [
            ("ENTER / GREEN — START SELECTED MODE", C_TEXT),
            ("L / YELLOW — LEADERBOARD", C_COMBO),
            ("ESC / RED — QUIT", C_WARNING),
        ]
        footer_y = self.screen_height - self.f_xx.get_height() - 12
        column_width = self.screen_width / len(controls)
        for index, (text_value, color) in enumerate(controls):
            rendered = self.f_xx.render(text_value, True, color)
            center_x = int(column_width * (index + 0.5))
            self.scr.blit(rendered,
                          (center_x - rendered.get_width() // 2, footer_y))

    def _draw_quit_confirm(self):
        """Draw quit confirmation dialog over the menu"""
        # First draw the menu in background
        self._draw_menu()
        
        # Darken the background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.scr.blit(overlay, (0, 0))
        
        # Draw confirmation dialog box
        box_w, box_h = 700, 200
        box_x = (self.screen_width - box_w) // 2
        box_y = (self.screen_height - box_h) // 2
        
        pygame.draw.rect(self.scr, (40, 40, 60), (box_x, box_y, box_w, box_h), border_radius=12)
        pygame.draw.rect(self.scr, (255, 80, 80), (box_x, box_y, box_w, box_h), 3, border_radius=12)
        
        # Draw confirmation text
        title_font = pygame.font.SysFont("monospace", 42, bold=True)
        t = title_font.render("QUIT GAME?", True, (255, 80, 80))
        self.scr.blit(t, (self.screen_width // 2 - t.get_width() // 2, box_y + 30))
        
        # Draw options
        option_font = pygame.font.SysFont("monospace", 28, bold=True)
        
        enter_text = option_font.render("Green Button or ENTER - Yes, Exit Game", True, (100, 255, 150))
        self.scr.blit(enter_text, (self.screen_width // 2 - enter_text.get_width() // 2, box_y + 90))
        
        esc_text = option_font.render("Red Button or ESC - No, Return to Menu", True, (255, 100, 100))
        self.scr.blit(esc_text, (self.screen_width // 2 - esc_text.get_width() // 2, box_y + 130))

    def _draw_over(self):
        self.scr.fill(C_BG)
        t = self.f_lg.render(self.config["theme"]["game_over_title"], True, C_WARNING)
        self.scr.blit(t, (self.screen_width // 2 - t.get_width() // 2, 30))
        mode = self.f_sm.render(self._mode_label().upper(), True, C_HOLE_BORDER)
        self.scr.blit(mode, (self.screen_width // 2 - mode.get_width() // 2, 82))
        t2 = self.f_lg.render(f"{self.config['theme']['score_label']}: {self.score}", True, C_TEXT)
        self.scr.blit(t2, (self.screen_width // 2 - t2.get_width() // 2, 115))

        if self.selected_mode == "quick":
            mode_labels = self.config["ui_labels"]["modes"]
            stats = [
                f"{mode_labels['threats_hit']}: {self.hits}",
                f"{mode_labels['threats_missed']}: {self.missed}",
                f"{self.config['ui_labels']['stats']['bosses_k']}: {self.bosses_k}",
                f"{self.config['ui_labels']['stats']['max_combo']}: {self.max_combo}x",
            ]
        else:
            stats = [
                f"{self.config['ui_labels']['stats']['hits']}: {self.hits}",
                f"{self.config['ui_labels']['stats']['missed']}: {self.missed}",
                f"{self.config['ui_labels']['stats']['f_hits']}: {self.f_hits}",
                f"{self.config['ui_labels']['stats']['ph_hits']}: {self.ph_hits}",
                f"{self.config['ui_labels']['stats']['se_hits']}: {self.se_hits}",
                f"{self.config['ui_labels']['stats']['bosses_k']}: {self.bosses_k}",
                f"{self.config['ui_labels']['stats']['pu_got']}: {self.pu_got}",
                f"{self.config['ui_labels']['stats']['max_combo']}: {self.max_combo}x",
            ]
        y = 175
        for s in stats:
            r = self.f_md.render(s, True, (180, 180, 200))
            self.scr.blit(r, (self.screen_width // 2 - r.get_width() // 2, y))
            y += 35

        if (self._mode_config()["clean_run_enabled"] and self.f_hits == 0):
            r = self.f_md.render("CLEAN RUN", True, C_COMBO)
            self.scr.blit(r, (self.screen_width // 2 - r.get_width() // 2, y))
            y += 35

        y += 12
        r1 = self.f_md.render(self.config["ui_labels"]["buttons"]["play_again"], True, C_TEXT)
        self.scr.blit(r1, (self.screen_width // 2 - r1.get_width() // 2, y))
        r2 = self.f_sm.render(self.config["ui_labels"]["buttons"]["menu"], True, (220, 60, 60))
        self.scr.blit(r2, (self.screen_width // 2 - r2.get_width() // 2, y + 38))
        r3 = self.f_sm.render(self.config["ui_labels"]["buttons"]["view_leaderboard"], True, (255, 215, 0))
        self.scr.blit(r3, (self.screen_width // 2 - r3.get_width() // 2, y + 66))

    def _draw_name(self):
        self.scr.fill(C_BG)
        t = self.f_lg.render(self.config["theme"]["high_score_title"], True, C_COMBO)
        self.scr.blit(t, (self.screen_width // 2 - t.get_width() // 2, 60))
        t2 = self.f_lg.render(f"{self.config['theme']['score_label']}: {self.score}", True, C_TEXT)
        self.scr.blit(t2, (self.screen_width // 2 - t2.get_width() // 2, 130))
        mode = self.f_sm.render(self._mode_label().upper(), True, C_HOLE_BORDER)
        self.scr.blit(mode, (self.screen_width // 2 - mode.get_width() // 2, 190))
        self.scr.blit(
            self.f_md.render(self.config["ui_labels"]["buttons"]["enter_name"], True, (200, 200, 220)),
            (self.screen_width // 2 - 200, 230))

        self.cur_blink += 0.08
        cur = "|" if math.sin(self.cur_blink) > 0 else " "
        bg = pygame.Rect(self.screen_width // 2 - 200, 280, 400, 60)
        pygame.draw.rect(self.scr, (30, 30, 50), bg, border_radius=8)
        pygame.draw.rect(self.scr, C_HOLE_BORDER, bg, 2, border_radius=8)
        nt = self.f_lg.render(self.pname + cur, True, C_SCORE)
        self.scr.blit(nt, (self.screen_width // 2 - nt.get_width() // 2, 288))
        self.scr.blit(
            self.f_sm.render(self.config["ui_labels"]["buttons"]["confirm_name"], True,
                            (130, 130, 150)),
            (self.screen_width // 2 - 280, 360))

    def _draw_lb(self):
        self.scr.fill(C_BG)
        modes = self.config["ui_labels"]["modes"]
        title = modes[f"{self.leaderboard_mode}_leaderboard"]
        t = self.f_lg.render(title, True, C_TEXT)
        self.scr.blit(t, (self.screen_width // 2 - t.get_width() // 2, 30))

        entries = self.lb.entries_for(self.leaderboard_mode)
        if not entries:
            r = self.f_md.render("No scores yet!", True, (150, 150, 170))
            self.scr.blit(r, (self.screen_width // 2 - r.get_width() // 2, 140))
        else:
            # Use a compact font so every competitive metric remains readable.
            if self.leaderboard_mode == "quick":
                row_format = "{:<5}{:<22}{:>11}{:>13}{:>10}  {:<16}"
                hdr = row_format.format("Rank", "Name", "Score", "Max Combo",
                                        "Bosses", "Date")
            else:
                row_format = "{:<5}{:<20}{:>10}{:>12}{:>9}{:>15}  {:<16}"
                hdr = row_format.format("Rank", "Name", "Score", "Max Combo",
                                        "Bosses", "Friendly Hits", "Date")
            row_height = min(30, max(18, (self.screen_height - 350) //
                                         MAX_LEADERBOARD))
            table_font = self.f_xs if row_height >= 24 else self.f_xx
            total_width = table_font.size(hdr)[0]
            start_x = (self.screen_width - total_width) // 2
            y = 135

            self.scr.blit(table_font.render(hdr, True, C_HOLE_BORDER),
                        (start_x, 100))
            pygame.draw.line(self.scr, C_HOLE_BORDER, (start_x, y),
                            (start_x + total_width, y))
            y += 5
            for i, e in enumerate(entries):
                col = C_COMBO if i == 0 else (200, 200, 220)
                values = [i + 1, str(e.get("name", "???"))[:19],
                          self.lb._number(e, "score"),
                          self.lb._number(e, "combo"),
                          self.lb._number(e, "bosses")]
                if self.leaderboard_mode == "challenge":
                    values.append(self.lb._number(e, "friendlies_hit"))
                values.append(str(e.get("date", ""))[:16])
                line = row_format.format(*values)
                self.scr.blit(table_font.render(line, True, col), (start_x, y))
                y += row_height

        other_mode = "challenge" if self.leaderboard_mode == "quick" else "quick"
        y = self.screen_height - 105
        controls = [
            (f"L / YELLOW — {modes[f'{other_mode}_leaderboard']}", C_COMBO),
            (f"ENTER / GREEN — PLAY {self._mode_label(self.leaderboard_mode).upper()}", C_TEXT),
            ("ESC / RED — MAIN MENU", C_WARNING),
        ]
        for text_value, color in controls:
            rendered = self.f_xs.render(text_value, True, color)
            self.scr.blit(rendered,
                          (self.screen_width // 2 - rendered.get_width() // 2, y))
            y += 27
    
    def _make_window_icon(self):
        # Try loading external icon first
        for path in [
            os.path.join(_DATA_DIR, "whack-a-hacker.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "whack-a-hacker.png"),
        ]:
            if os.path.exists(path):
                try:
                    return pygame.image.load(path).convert_alpha()
                except Exception:
                    pass

        # Generate one procedurally
        sz = 64
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        # Background circle
        pygame.draw.circle(s, (10, 20, 15), (32, 32), 30)
        pygame.draw.circle(s, (0, 180, 80), (32, 32), 30, 2)
        # Hammer head
        pygame.draw.rect(s, (140, 140, 150), (18, 8, 28, 14), border_radius=3)
        pygame.draw.rect(s, (180, 180, 190), (18, 8, 28, 14), 2, border_radius=3)
        # Hammer handle
        pygame.draw.line(s, (160, 120, 60), (32, 22), (32, 52), 5)
        # Money bag instead of hacker head
        pygame.draw.circle(s, (80, 140, 60), (32, 38), 8)
        pygame.draw.circle(s, (60, 120, 40), (32, 38), 8, 1)
        try:
            f = pygame.font.SysFont("monospace", 10, bold=True)
            s.blit(f.render("$", True, (255, 255, 0)), (28, 32))
        except Exception:
            pass
        return s

    # ---- main loop --------------------------------------------------------

    def _menu_mode_rects(self, top=154):
        """Return the clickable rectangles used by the menu mode cards."""
        x = self.screen_width // 2 - 410
        return {
            "quick": pygame.Rect(x, top, 820, 72),
            "challenge": pygame.Rect(x, top + 78, 820, 72),
        }

    def _note_post_game_activity(self):
        if self.state in ("over", "lb"):
            self.post_game_idle_state = self.state
            self.post_game_idle_started_at = pygame.time.get_ticks()

    def _update_post_game_idle(self):
        if self.state not in ("over", "lb"):
            self.post_game_idle_state = None
            return

        now = pygame.time.get_ticks()
        if self.post_game_idle_state != self.state:
            self.post_game_idle_state = self.state
            self.post_game_idle_started_at = now
        elif now - self.post_game_idle_started_at >= POST_GAME_IDLE_TIMEOUT_MS:
            if self.state == "lb":
                self.selected_mode = self.leaderboard_mode
            self.state = "menu"
            self.post_game_idle_state = None

    def _select_menu_mode(self, key):
        """Handle menu-only selection keys without starting a game."""
        if key == pygame.K_UP:
            if self.selected_mode == "challenge":
                self.selected_mode = "quick"
            return True
        if key == pygame.K_DOWN:
            if self.selected_mode == "quick":
                self.selected_mode = "challenge"
            return True
        if key in (pygame.K_1, pygame.K_KP1):
            self.selected_mode = "quick"
            return True
        if key in (pygame.K_2, pygame.K_KP2):
            self.selected_mode = "challenge"
            return True
        return False

    def _start_mode(self, mode=None):
        if mode is not None:
            self.selected_mode = mode
        self.leaderboard_mode = self.selected_mode
        self._reset()
        self.state = "play"
        self._play("start")

    def run(self):
        alive = True
        while alive:
            dt = min(self.clock.tick(FPS) / 1000, 0.1)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    alive = False

                elif ev.type == pygame.KEYDOWN:
                    self._note_post_game_activity()
                    mods = pygame.key.get_mods()

                    # global: Ctrl+Shift+C → reset leaderboard
                    if (ev.key == pygame.K_c
                            and mods & pygame.KMOD_CTRL
                            and mods & pygame.KMOD_SHIFT):
                        self.lb.reset()
                        self._flash("Leaderboard Reset!", C_WARNING, 1500)
                        continue

                    # ---- per-state input ----
                    if self.state == "menu":
                        if self._select_menu_mode(ev.key):
                            pass
                        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self._start_mode()
                        elif ev.key == pygame.K_l:
                            self.leaderboard_mode = self.selected_mode
                            self.state = "lb"
                        elif ev.key == pygame.K_ESCAPE:
                            self.state = "quit_confirm"
                    elif self.state == "quit_confirm":
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            alive = False
                        elif ev.key == pygame.K_ESCAPE:
                            self.state = "menu"

                    elif self.state == "play":
                        if ev.key == pygame.K_ESCAPE:
                            self.state = "menu"
                        else:
                            pos = NUMPAD_MAP.get(ev.key)
                            if pos is None:
                                pos = NUMBER_MAP.get(ev.key)
                            if pos:
                                self._whack(*pos)

                    elif self.state == "over":
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self._start_mode()
                        elif ev.key == pygame.K_l:
                            self.leaderboard_mode = self.selected_mode
                            self.state = "lb"
                        elif ev.key in (pygame.K_m, pygame.K_ESCAPE):
                            self.state = "menu"

                    elif self.state == "name":
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            nm = self.pname.strip() or "Anonymous"
                            self.lb.add(nm, self.score, self.max_combo,
                                        self.bosses_k, self.f_hits,
                                        self.selected_mode)
                            self.leaderboard_mode = self.selected_mode
                            self.state = "over"
                        elif ev.key == pygame.K_BACKSPACE:
                            self.pname = self.pname[:-1]
                        elif (len(self.pname) < 20
                            and ev.unicode.isprintable()
                            and ev.unicode):
                            self.pname += ev.unicode

                    elif self.state == "lb":
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self._start_mode(self.leaderboard_mode)
                        elif ev.key == pygame.K_l:
                            self.leaderboard_mode = (
                                "challenge" if self.leaderboard_mode == "quick"
                                else "quick")
                        elif ev.key in (pygame.K_ESCAPE, pygame.K_m):
                            self.selected_mode = self.leaderboard_mode
                            self.state = "menu"

                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    self._note_post_game_activity()
                    if ev.button != 1:
                        continue
                    if self.state == "play":
                        self.hammer_swinging = True
                        self.hammer_timer = 150
                        mx, my = ev.pos
                        for h in self.holes:
                            if h.contains(mx, my):
                                self._whack(h.row, h.col)
                                break
                    elif self.state == "menu":
                        for mode, box in self._menu_mode_rects().items():
                            if box.collidepoint(ev.pos):
                                self.selected_mode = mode
                                break
                    elif self.state == "over":
                        self._start_mode()
                    elif self.state == "quit_confirm":
                        self.state = "menu"

                elif ev.type == pygame.MOUSEMOTION:
                    self.hammer_pos = ev.pos

            # update
            if self.state == "play":
                self._update_play(dt)
            self._update_post_game_idle()

            # Hide system cursor during gameplay, show it otherwise
            if self.state == "play":
                if not self.show_hammer:
                    pygame.mouse.set_visible(False)
                    self.show_hammer = True
            else:
                if self.show_hammer:
                    pygame.mouse.set_visible(True)
                    self.show_hammer = False

            # draw
            {"menu": self._draw_menu,
            "play": self._draw_play,
            "over": self._draw_over,
            "name": self._draw_name,
            "lb":   self._draw_lb,
            "quit_confirm": self._draw_quit_confirm,
            }.get(self.state, self._draw_menu)()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# ===========================================================================
if __name__ == "__main__":
    Game().run()
