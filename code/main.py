#!/usr/bin/env python3
"""
Whack-a-Hacker: A Cyber Security themed Whack-a-Mole game
Features: Boss moles, power-ups, deceptive entities (phishing/social engineers),
          combo system, procedural sounds & sprites, persistent leaderboard.
Controls: Numpad 1-9 (or regular 1-9) or Mouse Click, Ctrl+Shift+C to reset leaderboard.
"""

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
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60

_DATA_DIR = os.environ.get("WHACK_DATA_DIR", "")
if not _DATA_DIR:
    _DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "whack-a-hacker")
os.makedirs(_DATA_DIR, exist_ok=True)
LEADERBOARD_FILE = os.path.join(_DATA_DIR, "leaderboard.json")

# Look for user assets first, fall back to bundled assets
_USER_ASSETS = os.path.join(_DATA_DIR, "assets")
_BUNDLED_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
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
            cls._buf(250, 100, 0.2, "saw"),
            cls._buf(150, 200, 0.2, "saw")))

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
                    self.entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.entries = []

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.entries, f, indent=2)
        except IOError:
            pass

    def add(self, name, score, combo, accuracy, bosses):
        self.entries.append({
            "name": name, "score": score, "combo": combo,
            "acc": int(accuracy), "bosses": bosses,
            "date": time.strftime("%Y-%m-%d %H:%M")})
        self.entries.sort(key=lambda e: e["score"], reverse=True)
        self.entries = self.entries[:MAX_LEADERBOARD]
        self._save()

    def reset(self):
        self.entries = []
        self._save()

    def qualifies(self, score):
        return (len(self.entries) < MAX_LEADERBOARD or
                score > self.entries[-1]["score"])


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

        if self.audio_ok:
            try:
                pygame.mixer.init()
            except pygame.error:
                self.audio_ok = False

        self.scr = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                           pygame.DOUBLEBUF)
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
        self.f_xs = pygame.font.SysFont("monospace", 20)
        self.f_xx = pygame.font.SysFont("monospace", 16)

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

        self.state = "menu"
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
                "stats": {
                    "hits": "Hackers Whacked",
                    "missed": "Hackers Missed",
                    "f_hits": "Friendlies Hit",
                    "ph_hits": "Phishing Traps Blocked",
                    "se_hits": "Spies Caught",
                    "bosses_k": "Bosses Defeated",
                    "pu_got": "Power-ups Collected",
                    "max_combo": "Max Combo",
                    "accuracy": "Accuracy"
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
            ("phishing",  Sprites.phishing,  Sprites.gen_phishing),
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
        self.whacks = 0
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
        self.last_tick_s = -1
        self.eff.clear()
        self.ptcl.ps = []
        self.flashes = []

        self.holes = []
        gx = (SCREEN_WIDTH - GRID_COLS * HOLE_WIDTH) // 2
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
        types = list(SPAWN_WEIGHTS.keys())
        weights = list(SPAWN_WEIGHTS.values())
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
        self.whacks += 1
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
                    "social_engineer": SCORE_HIT_SOCIAL_ENGINEER
                    }.get(detail, SCORE_HIT_HACKER)
            pts = base * mul
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.hits += 1
            if detail == "social_engineer":
                self.se_hits += 1
                self._play("social")
                self._flash(self.config["messages"]["hit_social"].format(pts=pts), (100, 255, 200), 800)
            if self.combo >= COMBO_THRESHOLD:
                bonus = COMBO_BONUS * mul
                pts += bonus
                self._play("combo", self.combo)
                self._flash(self.config["messages"]["combo"].format(combo=self.combo, pts=pts), C_COMBO, 600)
            elif detail != "social_engineer":
                self._flash(self.config["messages"]["hit_hacker"].format(pts=pts), C_TEXT, 500)
            self.score += pts
            if detail == "social_engineer":
                self.ptcl.emit(px, py, (100, 255, 200), 15)
            else:
                self._play("hit")
                self.ptcl.emit(px, py, (0, 255, 200), 12)

        elif tag == "bad":
            if detail == "phishing":
                pts = SCORE_HIT_PHISHING
                self.ph_hits += 1
                self._play("phishing")
                self._flash(self.config["messages"]["hit_phishing"].format(pts=pts), C_TEXT, 800)
            else:
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
            self.state = "name" if self.lb.qualifies(self.score) else "over"
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
        if self.combo >= 2:
            col = C_COMBO if self.combo >= COMBO_THRESHOLD else (200, 200, 200)
            self.scr.blit(
                self.f_sm.render(f"Combo: {self.combo}x", True, col),
                (20, 46))

        # timer bar
        bw, bh = 280, 22
        bx = SCREEN_WIDTH - bw - 20
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
            self.scr.blit(ft, (SCREEN_WIDTH // 2 - ft.get_width() // 2, fy))
            fy += 32

        # footer
        self.scr.blit(
            self.f_xs.render("Numpad 1-9: Whack  |  ESC/Red Button: Menu", True,
                             (100, 100, 120)),
            (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 25))

    def _draw_play(self):
        self.scr.fill(C_BG)

        if self.eff.on("freeze"):
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            ov.fill((100, 200, 255, 15))
            self.scr.blit(ov, (0, 0))
        if self.eff.on("double"):
            p = abs(math.sin(pygame.time.get_ticks() / 300))
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            ov.fill((255, 215, 0, int(8 * p)))
            self.scr.blit(ov, (0, 0))

        gw = GRID_COLS * HOLE_WIDTH + 20
        gh = GRID_ROWS * HOLE_HEIGHT + 20
        gx = (SCREEN_WIDTH - gw) // 2
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

    def _draw_menu(self):
        self.scr.fill(C_BG)
        self.title_p += 0.05
        p = abs(math.sin(self.title_p)) * 30
        tc = (int(min(255, C_TEXT[0] + p)), C_TEXT[1],
            int(min(255, C_TEXT[2] + p)))

        title_font = pygame.font.SysFont("monospace", 64, bold=True)
        t = title_font.render(self.config["theme"]["title"], True, tc)
        y = 40
        self.scr.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, y))

        subtitle_font = pygame.font.SysFont("monospace", 36, bold=True)
        t2 = subtitle_font.render(self.config["theme"]["subtitle"], True,
                                (100, 220, 150))
        y += 68
        self.scr.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, y))

        opts = [
            (self.config["ui_labels"]["buttons"]["start"], C_TEXT),
            (self.config["ui_labels"]["buttons"]["leaderboard"], (255, 215, 0)),
            (self.config["ui_labels"]["buttons"]["quit"], (220, 60, 60)),
        ]
        y += 80
        for txt, col in opts:
            r = subtitle_font.render(txt, True, col)
            self.scr.blit(r, (SCREEN_WIDTH // 2 - r.get_width() // 2, y))
            y += 40

        y += 40
        self.scr.blit(subtitle_font.render("========= ENTITY GUIDE =========", True,
                                            (180, 180, 200)),
                        (SCREEN_WIDTH // 2 - 350, y))
        y += 45

        SPR = 44   # sprite render size in pixels
        LINE = 50  # row height
        GAP = 14   # gap between sprites and text

        guide = [
            (["hacker"], f"{self.config['enemies']['hacker']} — {self.config['descriptions']['hacker']}", (220, 60, 60)),
            (["apt"], f"{self.config['enemies']['apt']} — {self.config['descriptions']['apt']}", (180, 50, 180)),
            (["boss"], f"{self.config['enemies']['boss']} — {self.config['descriptions']['boss']}", (255, 100, 0)),
            (["social_engineer"], f"{self.config['enemies']['social_engineer']} — {self.config['descriptions']['social_engineer']}", (80, 200, 150)),
            (["phishing"], f"{self.config['enemies']['phishing']} — {self.config['descriptions']['phishing']}", (220, 120, 40)),
            (["shield", "it_admin", "lock"], f"{self.config['friendlies']['shield']}/{self.config['friendlies']['it_admin']}/{self.config['friendlies']['lock']} — {self.config['descriptions']['shield']}", (50, 150, 255)),
            (["pu_freeze", "pu_double", "pu_time_bonus", "pu_slow_mo"], f"POWER-UPS — COLLECT!", (255, 215, 0)),
        ]

        for sprite_keys, txt, col in guide:
            sprites = []
            for key in sprite_keys:
                imgs = self.imgs.get(key, [])
                if imgs:
                    sprites.append(
                        pygame.transform.smoothscale(imgs[0], (SPR, SPR)))

            r = self.f_md.render(txt, True, col)

            sprites_w = len(sprites) * SPR + max(0, len(sprites) - 1) * 4
            total_w = sprites_w + GAP + r.get_width()
            sx = SCREEN_WIDTH // 2 - total_w // 2

            for i, spr in enumerate(sprites):
                self.scr.blit(spr, (sx + i * (SPR + 4),
                                    y + (LINE - SPR) // 2))

            self.scr.blit(r, (sx + sprites_w + GAP,
                            y + (LINE - r.get_height()) // 2))
            y += LINE

        y += 20
        for line in [
            "Numpad 1-9 (or regular number keys) to whack:  ",
            "7  8  9    60 seconds  |  Combos at 3+ streak   ",
            "4  5  6    Boss every ~20s  |  Power-ups appear ",
            "1  2  3    Watch for disguised spies & phishing!",
        ]:
            r = self.f_md.render(line, True, (120, 120, 140))
            self.scr.blit(r, (SCREEN_WIDTH // 2 - r.get_width() // 2, y))
            y += 30

    def _draw_over(self):
        self.scr.fill(C_BG)
        t = self.f_lg.render(self.config["theme"]["game_over_title"], True, C_WARNING)
        self.scr.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 30))
        t2 = self.f_lg.render(f"{self.config['theme']['score_label']}: {self.score}", True, C_TEXT)
        self.scr.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 90))

        acc = (self.hits / self.whacks * 100) if self.whacks else 0
        stats = [
            f"{self.config['ui_labels']['stats']['hits']}: {self.hits}",
            f"{self.config['ui_labels']['stats']['missed']}: {self.missed}",
            f"{self.config['ui_labels']['stats']['f_hits']}: {self.f_hits}",
            f"{self.config['ui_labels']['stats']['ph_hits']}: {self.ph_hits}",
            f"{self.config['ui_labels']['stats']['se_hits']}: {self.se_hits}",
            f"{self.config['ui_labels']['stats']['bosses_k']}: {self.bosses_k}",
            f"{self.config['ui_labels']['stats']['pu_got']}: {self.pu_got}",
            f"{self.config['ui_labels']['stats']['max_combo']}: {self.max_combo}x",
            f"{self.config['ui_labels']['stats']['accuracy']}: {acc:.1f}%",
        ]
        y = 160
        for s in stats:
            r = self.f_md.render(s, True, (180, 180, 200))
            self.scr.blit(r, (SCREEN_WIDTH // 2 - r.get_width() // 2, y))
            y += 35

        y += 12
        r1 = self.f_md.render(self.config["ui_labels"]["buttons"]["play_again"], True, C_TEXT)
        self.scr.blit(r1, (SCREEN_WIDTH // 2 - r1.get_width() // 2, y))
        r2 = self.f_sm.render(self.config["ui_labels"]["buttons"]["menu"], True, (220, 60, 60))
        self.scr.blit(r2, (SCREEN_WIDTH // 2 - r2.get_width() // 2, y + 38))
        r3 = self.f_sm.render(self.config["ui_labels"]["buttons"]["view_leaderboard"], True, (255, 215, 0))
        self.scr.blit(r3, (SCREEN_WIDTH // 2 - r3.get_width() // 2, y + 66))

    def _draw_name(self):
        self.scr.fill(C_BG)
        t = self.f_lg.render(self.config["theme"]["high_score_title"], True, C_COMBO)
        self.scr.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 60))
        t2 = self.f_lg.render(f"{self.config['theme']['score_label']}: {self.score}", True, C_TEXT)
        self.scr.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 130))
        self.scr.blit(
            self.f_md.render(self.config["ui_labels"]["buttons"]["enter_name"], True, (200, 200, 220)),
            (SCREEN_WIDTH // 2 - 200, 220))

        self.cur_blink += 0.08
        cur = "|" if math.sin(self.cur_blink) > 0 else " "
        bg = pygame.Rect(SCREEN_WIDTH // 2 - 200, 270, 400, 60)
        pygame.draw.rect(self.scr, (30, 30, 50), bg, border_radius=8)
        pygame.draw.rect(self.scr, C_HOLE_BORDER, bg, 2, border_radius=8)
        nt = self.f_lg.render(self.pname + cur, True, C_SCORE)
        self.scr.blit(nt, (SCREEN_WIDTH // 2 - nt.get_width() // 2, 278))
        self.scr.blit(
            self.f_sm.render(self.config["ui_labels"]["buttons"]["confirm_name"], True,
                            (130, 130, 150)),
            (SCREEN_WIDTH // 2 - 280, 350))

    def _draw_lb(self):
        self.scr.fill(C_BG)
        t = self.f_lg.render("LEADERBOARD", True, C_TEXT)
        self.scr.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 30))

        if not self.lb.entries:
            r = self.f_md.render("No scores yet!", True, (150, 150, 170))
            self.scr.blit(r, (SCREEN_WIDTH // 2 - r.get_width() // 2, 140))
        else:
            # Calculate the total width needed for the centered table
            col_widths = [120, 400, 160, 180, 150, 150, 320]  # Approximate widths for each column
            total_width = sum(col_widths)
            start_x = (SCREEN_WIDTH - total_width) // 2
            y = 135
            
            hdr = (f"{'#':<4}{'Name':<20}{'Score':<8}{'Combo':<7}"
                f"{'Boss':<6}{'Acc%':<6}{'Date'}")
            self.scr.blit(self.f_md.render(hdr, True, C_HOLE_BORDER),
                        (start_x, 100))
            pygame.draw.line(self.scr, C_HOLE_BORDER, (start_x, y),
                            (start_x + total_width, y))
            y += 5
            for i, e in enumerate(self.lb.entries):
                col = C_COMBO if i == 0 else (200, 200, 220)
                line = (f"{i + 1:<4}{e.get('name', '???'):<20}"
                        f"{e.get('score', 0):<8}{e.get('combo', 0):<7}"
                        f"{e.get('bosses', 0):<6}{e.get('acc', 0):<6}"
                        f"{e.get('date', '')}")
                self.scr.blit(self.f_md.render(line, True, col), (start_x, y))
                y += 35

        y = SCREEN_HEIGHT - 200
        self.scr.blit(
            self.f_md.render("ESC, M, or Red Button for Menu", True, (220, 60, 60)),
            (SCREEN_WIDTH // 2 - 300, y))
        self.scr.blit(
            self.f_md.render(self.config["ui_labels"]["buttons"]["start"], True,
                            C_TEXT),
            (SCREEN_WIDTH // 2 - 375, y + 40))
    
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

    def run(self):
        alive = True
        while alive:
            dt = min(self.clock.tick(FPS) / 1000, 0.1)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    alive = False

                elif ev.type == pygame.KEYDOWN:
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
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self._reset()
                            self.state = "play"
                            self._play("start")
                        elif ev.key == pygame.K_l:
                            self.state = "lb"
                        elif ev.key == pygame.K_ESCAPE:
                            alive = False

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
                            self._reset()
                            self.state = "play"
                            self._play("start")
                        elif ev.key == pygame.K_l:
                            self.state = "lb"
                        elif ev.key in (pygame.K_m, pygame.K_ESCAPE):
                            self.state = "menu"

                    elif self.state == "name":
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            nm = self.pname.strip() or "Anonymous"
                            acc = ((self.hits / self.whacks * 100)
                                if self.whacks else 0)
                            self.lb.add(nm, self.score, self.max_combo,
                                        acc, self.bosses_k)
                            self.state = "over"
                        elif ev.key == pygame.K_BACKSPACE:
                            self.pname = self.pname[:-1]
                        elif (len(self.pname) < 20
                            and ev.unicode.isprintable()
                            and ev.unicode):
                            self.pname += ev.unicode

                    elif self.state == "lb":
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self._reset()
                            self.state = "play"
                            self._play("start")
                        if ev.key in (pygame.K_ESCAPE, pygame.K_m):
                            self.state = "menu"

                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.state == "play":
                        self.hammer_swinging = True
                        self.hammer_timer = 150
                        mx, my = ev.pos
                        for h in self.holes:
                            if h.contains(mx, my):
                                self._whack(h.row, h.col)
                                break
                    elif self.state == "menu":
                        self._reset()
                        self.state = "play"
                        self._play("start")
                    elif self.state == "over":
                        self._reset()
                        self.state = "play"
                        self._play("start")

                elif ev.type == pygame.MOUSEMOTION:
                    self.hammer_pos = ev.pos

            # update
            if self.state == "play":
                self._update_play(dt)

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
            }.get(self.state, self._draw_menu)()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# ===========================================================================
if __name__ == "__main__":
    Game().run()
