"""
Pixel-art sprites — all drawn programmatically, child-friendly.
"""
from __future__ import annotations
import pygame
import math
from typing import Dict
import config as C


def _r(surf, x, y, w, h, c):
    pygame.draw.rect(surf, c, (x, y, w, h))


def _c(surf, x, y, c):
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), c)


class SpriteFactory:
    # get_computer() cachea por (estado, % reparación, frame): sin tope la
    # caché crece con cada porcentaje distinto (~2400 sprites). La limitamos.
    CACHE_MAX = 800

    def __init__(self):
        self._cache: Dict[str, pygame.Surface] = {}

    def _put(self, key, surf):
        if len(self._cache) >= self.CACHE_MAX:
            self._cache.clear()
        self._cache[key] = surf
        return surf

    def clear(self):
        self._cache.clear()

    def get_technician(
        self, shirt="blue", hair="brown", facing_right=True, frame=0
    ) -> pygame.Surface:
        shirt_c = {"blue": C.C_SHIRT_BLUE, "green": C.C_SHIRT_GREEN,
                    "orange": C.C_SHIRT_ORANGE, "purple": C.C_SHIRT_PURPLE}.get(shirt, C.C_SHIRT_BLUE)
        hair_c = {"brown": C.C_HAIR_BROWN, "black": C.C_HAIR_BLACK,
                   "blond": C.C_HAIR_BLOND, "red": C.C_HAIR_RED}.get(hair, C.C_HAIR_BROWN)

        key = f"t_{shirt}_{hair}_{facing_right}_{frame % 4}"
        if key in self._cache:
            return self._cache[key]

        s = pygame.Surface((14, 20), pygame.SRCALPHA)
        bob = [0, -1, 0, 1][frame % 4]

        # Hair top
        _r(s, 4, 0+bob, 6, 2, hair_c)
        _r(s, 3, 1+bob, 8, 3, hair_c)
        _r(s, 3, 2+bob, 1, 2, hair_c)

        # Face
        _r(s, 4, 3+bob, 6, 5, C.C_SKIN)
        _c(s, 5, 4+bob, C.C_EYES)
        _c(s, 8, 4+bob, C.C_EYES)
        _r(s, 6, 5+bob, 2, 1, C.C_MOUTH)
        _c(s, 5, 3+bob, C.C_SKIN_SH)
        _c(s, 9, 3+bob, C.C_SKIN_SH)

        # Neck
        _r(s, 6, 8+bob, 2, 1, C.C_SKIN)

        # Shirt / torso
        _r(s, 3, 9+bob, 8, 5, shirt_c)
        _r(s, 4, 9+bob, 6, 1, tuple(min(255, c+30) for c in shirt_c))
        _r(s, 2, 10+bob, 2, 4, C.C_SKIN)   # left arm
        _r(s, 10, 10+bob, 2, 4, C.C_SKIN)   # right arm
        _r(s, 3, 11+bob, 1, 2, C.C_SKIN_SH)

        # Belt
        _r(s, 4, 14+bob, 6, 1, (60, 50, 40))

        # Pants
        _r(s, 4, 15+bob, 2, 3, C.C_PANTS)
        _r(s, 8, 15+bob, 2, 3, C.C_PANTS)
        _r(s, 6, 15+bob, 2, 1, C.C_PANTS)

        # Shoes
        _r(s, 3, 18+bob, 3, 2, C.C_SHOES)
        _r(s, 8, 18+bob, 3, 2, C.C_SHOES)

        if not facing_right:
            s = pygame.transform.flip(s, True, False)

        return self._put(key, s)

    def get_computer(self, state="damaged", repair_pct=0.0, frame=0) -> pygame.Surface:
        key = f"comp_{state}_{int(repair_pct)}_{frame % 6}"
        if key in self._cache:
            return self._cache[key]

        s = pygame.Surface((22, 24), pygame.SRCALPHA)

        # Monitor body
        _r(s, 0, 0, 22, 15, C.C_MONITOR)
        _r(s, 1, 1, 20, 13, C.C_MONITOR_BEZ)

        if state == "damaged":
            _r(s, 2, 2, 18, 11, C.C_SCREEN_DMG)
            # Smoke wisps
            smoke_off = frame % 3
            _c(s, 16+smoke_off, 1, C.C_SMOKE)
            _c(s, 17+smoke_off, 0, C.C_SMOKE)
            _c(s, 15, 1-smoke_off if 1-smoke_off >= 0 else 0, C.C_SMOKE)
            # Crack lines
            _c(s, 8, 4, (120, 50, 50))
            _c(s, 9, 5, (110, 45, 45))
            _c(s, 10, 4, (100, 40, 40))
            _c(s, 11, 6, (120, 50, 50))
            # Warning icon
            flicker = frame % 4
            if flicker < 3:
                _r(s, 5, 6, 4, 5, C.C_YELLOW)
                _c(s, 6, 7, C.C_BLACK)
                _c(s, 7, 7, C.C_BLACK)
                _c(s, 6, 9, C.C_BLACK)
                _c(s, 7, 9, C.C_BLACK)
            # Blinking cursor
            if frame % 2 == 0:
                _r(s, 12, 9, 2, 2, C.C_SCREEN_WARN)

        elif state == "repairing":
            _r(s, 2, 2, 18, 11, C.C_SCREEN_REPAIR)
            bar_w = int(16 * min(repair_pct / 100, 1.0))
            _r(s, 3, 6, 16, 4, (40, 40, 55))
            if bar_w > 0:
                _r(s, 3, 6, bar_w, 4, C.C_GREEN)
                # Shine on bar
                _r(s, 3, 6, bar_w, 1, tuple(min(255, c+60) for c in C.C_GREEN))
            # Blinking sparks
            if frame % 2 == 0:
                _c(s, 4+bar_w//2, 4, C.C_YELLOW)
                _c(s, 6+bar_w//2, 5, C.C_ORANGE)

        elif state == "repaired":
            _r(s, 2, 2, 18, 11, C.C_SCREEN_OK)
            # Bright screen content
            _r(s, 5, 4, 12, 7, C.C_SCREEN_BRIGHT)
            # Checkmark
            _c(s, 8, 6, C.C_WHITE)
            _c(s, 9, 7, C.C_WHITE)
            _c(s, 10, 8, C.C_WHITE)
            _c(s, 11, 7, C.C_WHITE)
            _c(s, 12, 6, C.C_WHITE)
            _c(s, 13, 5, C.C_WHITE)
            # Screen glow pulse
            glow_alpha = int(40 + 30 * math.sin(frame * 0.8))
            glow_c = (55+glow_alpha, 210+min(glow_alpha, 45), 110+min(glow_alpha, 45))
            _r(s, 3, 3, 16, 1, glow_c)

        elif state == "overrepaired":
            _r(s, 2, 2, 18, 11, C.C_SCREEN_OK)
            _r(s, 5, 4, 12, 7, C.C_SCREEN_BRIGHT)
            _c(s, 8, 6, C.C_WHITE)
            _c(s, 9, 7, C.C_WHITE)
            _c(s, 10, 8, C.C_WHITE)
            _c(s, 11, 7, C.C_WHITE)
            _c(s, 12, 6, C.C_WHITE)
            # Yellow warning triangle for over-repair
            _r(s, 15, 2, 4, 3, C.C_YELLOW)
            _c(s, 16, 3, C.C_BLACK)

        # Stand
        _r(s, 8, 15, 6, 3, C.C_STAND)
        _r(s, 5, 18, 12, 2, C.C_BASE)
        _r(s, 3, 20, 16, 2, C.C_BASE)
        # Power LED
        led_c = C.C_GREEN if state == "repaired" else (C.C_RED if state == "damaged" else C.C_YELLOW)
        _c(s, 10, 21, led_c)

        return self._put(key, s)

    def get_component(self, comp_type: int, selected=False, frame=0) -> pygame.Surface:
        key = f"ci_{comp_type}_{selected}_{frame % 8}"
        if key in self._cache:
            return self._cache[key]

        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        color = C.C_COMP_COLORS[comp_type % len(C.C_COMP_COLORS)]

        if selected:
            # Glow border
            for i in range(2):
                _r(s, i, i, 16-2*i, 16-2*i, C.C_GLOW_CYAN)

        inset = 2 if selected else 0
        inner = 16 - inset * 2
        ox, oy = inset, inset

        if comp_type == 0:  # CPU
            _r(s, ox+1, oy+1, inner-2, inner-2, color)
            _r(s, ox+3, oy+3, inner-6, inner-6, (240, 240, 255))
            _r(s, ox+4, oy+4, inner-8, inner-8, color)
            for d in range(0, inner-2, 2):
                _c(s, ox, oy+d, (200, 200, 220))
                _c(s, ox+inner-1, oy+d, (200, 200, 220))
                _c(s, ox+d, oy, (200, 200, 220))
                _c(s, ox+d, oy+inner-1, (200, 200, 220))

        elif comp_type == 1:  # GPU
            _r(s, ox, oy+2, inner, inner-4, color)
            _r(s, ox+1, oy+3, inner-2, inner-6, (85, 145, 65))
            _r(s, ox+2, oy+4, 3, 4, (45, 45, 60))
            _r(s, ox+inner-5, oy+4, 3, 4, (45, 45, 60))
            _c(s, ox+3, oy+5, (100, 100, 125))
            _c(s, ox+inner-4, oy+5, (100, 100, 125))

        elif comp_type == 2:  # RAM
            _r(s, ox+3, oy, inner-6, inner, color)
            _r(s, ox+4, oy+1, inner-8, inner-2, (65, 165, 145))
            for d in range(2, inner-2, 2):
                _r(s, ox+4, oy+d, inner-8, 1, (45, 125, 115))
            _r(s, ox+4, oy+inner-2, inner-8, 1, (200, 200, 220))

        elif comp_type == 3:  # SSD
            _r(s, ox+1, oy+2, inner-2, inner-4, color)
            _r(s, ox+2, oy+3, inner-4, inner-6, (205, 185, 55))
            _r(s, ox+3, oy+4, 4, 4, (165, 145, 45))
            _c(s, ox+inner-4, oy+5, C.C_GREEN)

        elif comp_type == 4:  # PSU
            _r(s, ox+1, oy+1, inner-2, inner-2, color)
            _r(s, ox+2, oy+2, inner-4, inner-4, (145, 95, 55))
            cx, cy = inner//2, inner//2
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx*dx + dy*dy <= 5:
                        _c(s, ox+cx+dx, oy+cy+dy, (85, 65, 45))

        elif comp_type == 5:  # Refrigeración líquida (AIO)
            _r(s, ox+1, oy+1, inner-2, inner-2, color)
            _r(s, ox+2, oy+2, inner-4, inner-6, (120, 180, 210))
            _r(s, ox+2, oy+3, inner-4, 2, (200, 235, 250))
            for d in range(1, inner-1, 3):
                _c(s, ox+d, oy+inner-2, (90, 150, 185))
            _r(s, ox+2, oy+7, inner-4, 1, (90, 150, 185))

        elif comp_type == 6:  # Motherboard
            _r(s, ox, oy+1, inner, inner-2, color)
            _r(s, ox+1, oy+2, inner-2, inner-4, (55, 105, 55))
            for x in range(2, inner-2, 3):
                _r(s, ox+x, oy+3, 1, inner-6, (45, 85, 45))
            _r(s, ox+3, oy+4, 4, 4, (35, 65, 35))
            _r(s, ox+inner-5, oy+3, 3, 3, (75, 75, 95))
            _c(s, ox+2, oy+inner-3, C.C_YELLOW)
            _r(s, ox+6, oy+inner-4, 3, 2, (85, 65, 45))

        elif comp_type == 7:  # Tarjeta de Red / WiFi
            _r(s, ox+1, oy+1, inner-2, inner-6, color)
            _r(s, ox+2, oy+2, inner-4, inner-8, (60, 150, 210))
            _r(s, ox+2, oy+5, inner-4, 1, (40, 110, 170))
            _c(s, ox+3, oy+7, (45, 45, 60))
            _c(s, ox+inner-4, oy+7, (45, 45, 60))
            # antenas WiFi
            _c(s, ox+3, oy+9, (45, 45, 60))
            _c(s, ox+inner-4, oy+9, (45, 45, 60))
            _c(s, ox+3, oy+10, (200, 235, 250))
            _c(s, ox+inner-4, oy+10, (45, 45, 60))

        elif comp_type == 8:  # Sensores / termales
            _r(s, ox+1, oy+1, inner-2, inner-2, color)
            _r(s, ox+2, oy+2, inner-4, inner-4, (200, 90, 135))
            _c(s, ox+4, oy+4, C.C_YELLOW)
            _c(s, ox+7, oy+4, C.C_YELLOW)
            _c(s, ox+5, oy+7, C.C_GLOW_RED)
            _r(s, ox+inner-4, oy+inner-4, 2, 2, (255, 180, 200))

        return self._put(key, s)

    def get_gear(self, frame=0) -> pygame.Surface:
        key = f"gear_{frame % 8}"
        if key in self._cache:
            return self._cache[key]
        s = pygame.Surface((12, 12), pygame.SRCALPHA)
        cx, cy = 6, 6
        # Outer teeth
        for angle_deg in range(0, 360, 45):
            a = math.radians(angle_deg + frame * 45)
            tx = int(cx + math.cos(a) * 5)
            ty = int(cy + math.sin(a) * 5)
            _c(s, tx, ty, C.C_BORDER_LIGHT)
        # Body
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if dx*dx + dy*dy <= 14:
                    _c(s, cx+dx, cy+dy, C.C_BORDER)
        # Inner ring
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx*dx + dy*dy <= 4:
                    _c(s, cx+dx, cy+dy, C.C_BG_LIGHT)
        # Spokes
        for i in range(-3, 4):
            _c(s, cx+i, cy, C.C_BORDER_LIGHT)
            _c(s, cx, cy+i, C.C_BORDER_LIGHT)
        return self._put(key, s)

    def get_octopus(self, frame=0, win=False) -> pygame.Surface:
        """Purple pixel-art jellyfish with bell dome, trailing tentacles, bioluminescent glow."""
        f = frame % 8
        key = f"octopus_{f}_{win}"
        if key in self._cache:
            return self._cache[key]

        s = pygame.Surface((20, 26), pygame.SRCALPHA)

        # Colors
        bell_dark   = (100, 45, 160)
        bell_mid    = (135, 70, 195)
        bell_lite   = (170, 105, 225)
        bell_shine  = (210, 160, 255)
        bell_top    = (230, 190, 255)
        glow_c      = (180, 130, 255)
        glow_bright = (220, 185, 255)
        tent_dark   = (90, 40, 150)
        tent_mid    = (120, 60, 180)
        tent_lite   = (155, 95, 210)
        eye_white   = (255, 255, 255)
        pupil       = (25, 15, 50)
        eye_shine   = (255, 255, 255)
        mouth_c     = (80, 35, 130)
        blush_c     = (200, 120, 180)

        # ── Bell / Dome (wide, translucent dome shape) ──
        # Shadow underneath
        for dx in range(-1, 12):
            for dy in range(-1, 2):
                px, py = 4 + dx, 9 + dy
                if 0 <= px < 20 and 0 <= py < 26:
                    if (dx - 5) ** 2 / 30 + dy * dy < 1.0:
                        s.set_at((px, py), bell_dark)

        # Main dome — wide half-circle, wider than tall
        for dx in range(-7, 8):
            for dy in range(-6, 2):
                # Wider dome: ellipse stretched horizontally
                ex = dx / 7.0
                ey = dy / 4.5
                if ex * ex + ey * ey <= 1.0 and dy <= 0:
                    px, py = 10 + dx, 6 + dy
                    if 0 <= px < 20 and 0 <= py < 26:
                        shade = 1.0 - (ex * ex + ey * ey)
                        if ey < -0.6:
                            c = bell_top if shade > 0.6 else bell_shine
                        elif ey < -0.2:
                            c = bell_shine if shade > 0.5 else bell_lite
                        elif ey < 0.2:
                            c = bell_lite if shade > 0.3 else bell_mid
                        else:
                            c = bell_mid if shade > 0.2 else bell_dark
                        s.set_at((px, py), c)
                # Bottom edge of dome (flat-ish, like a jellyfish rim)
                elif dy == 0 and abs(dx) <= 6:
                    px, py = 10 + dx, 6
                    if 0 <= px < 20:
                        s.set_at((px, py), bell_dark)

        # Dome highlight / shine streak (pulsing)
        pulse = math.sin(f * 0.9)
        shine_y = 2 + int(pulse * 0.5)
        for dx in range(-4, 3):
            px = 8 + dx
            py = shine_y
            if 0 <= px < 20 and 0 <= py < 26:
                c = glow_bright if pulse > 0 else bell_shine
                s.set_at((px, py), c)
        # Extra bright spot
        _c(s, 9, shine_y - 1, glow_bright)
        _c(s, 10, shine_y - 1, bell_top)

        # Bioluminescent glow ring (pulsing alpha)
        glow_intensity = 0.4 + 0.3 * math.sin(f * 1.1)
        for dx in range(-5, 6):
            px = 10 + dx
            py = 3
            if 0 <= px < 20 and 0 <= py < 26:
                existing = s.get_at((px, py))
                blended = tuple(
                    min(255, int(existing[i] * (1 - glow_intensity) + glow_c[i] * glow_intensity))
                    for i in range(3)
                )
                s.set_at((px, py), blended)

        # ── Eyes (cute, big, on the dome) ──
        # Left eye
        for dx in range(-2, 3):
            for dy in range(-1, 2):
                px, py = 7 + dx, 7 + dy
                if 0 <= px < 20 and 0 <= py < 26:
                    if abs(dx) + abs(dy) <= 2:
                        s.set_at((px, py), eye_white)
        pupil_off = 1 if f >= 4 else 0
        _c(s, 8 + pupil_off, 7, pupil)
        _c(s, 7, 6, eye_shine)

        # Right eye
        for dx in range(-2, 3):
            for dy in range(-1, 2):
                px, py = 13 + dx, 7 + dy
                if 0 <= px < 20 and 0 <= py < 26:
                    if abs(dx) + abs(dy) <= 2:
                        s.set_at((px, py), eye_white)
        pupil_off2 = -1 if f >= 4 else 0
        _c(s, 14 + pupil_off2, 7, pupil)
        _c(s, 13, 6, eye_shine)

        # Mouth
        if win:
            _c(s, 9, 10, mouth_c)
            _c(s, 10, 10, mouth_c)
            _c(s, 11, 10, mouth_c)
            _c(s, 8, 9, mouth_c)
            _c(s, 12, 9, mouth_c)
        else:
            _c(s, 9, 10, mouth_c)
            _c(s, 10, 10, mouth_c)
            _c(s, 11, 10, mouth_c)

        # Blush
        _c(s, 5, 8, blush_c)
        _c(s, 14, 8, blush_c)

        # ── Tentacles (8, long, flowing with wave) ──
        tent_start_y = 9
        tent_xs = [2, 4, 6, 8, 11, 13, 15, 17]
        for ti, tx in enumerate(tent_xs):
            length = 10 + (ti % 3)
            for sy in range(length):
                t_ratio = sy / max(length, 1)
                wave = math.sin(f * 0.7 + ti * 1.0 + t_ratio * 3.0) * (1.5 + t_ratio)
                px = tx + int(wave)
                py = tent_start_y + sy
                if 0 <= px < 20 and 0 <= py < 26:
                    # Taper color: lighter at base, darker at tip
                    if t_ratio < 0.3:
                        c = tent_lite
                    elif t_ratio < 0.6:
                        c = tent_mid
                    else:
                        c = tent_dark
                    s.set_at((px, py), c)
                    # Width: 2px at base, 1px at tip
                    if t_ratio < 0.4 and px + 1 < 20:
                        s.set_at((px + 1, py), tent_mid)

            # Suction cup dots at tips
            tip_x = tx + int(math.sin(f * 0.7 + ti * 1.0 + 1.0) * 1.5)
            tip_y = tent_start_y + length
            if 0 <= tip_x < 20 and 0 <= tip_y < 26:
                s.set_at((tip_x, tip_y), bell_lite)

        return self._put(key, s)
