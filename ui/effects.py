"""
Visual effects — particles, glow, floating text, shake, confetti, transitions.
"""
from __future__ import annotations
import pygame
import random
import math
from typing import List
import config as C


# ── Cachés de color/superficie compartidas ───────────────────────
# A 60 fps con cientos de partículas, estrellas y anillos por frame,
# crear Surface(SRCALPHA) y tuplas de color cada frame es el mayor costo.
_TINT_CACHE = {}

RING_MAX = 120


def tint(color, a):
    """Color atenuado por alpha, cuantizado a 16 niveles y cacheado."""
    lv = int(a * 16)
    if lv < 0:
        lv = 0
    elif lv > 16:
        lv = 16
    key = (color, lv)
    c = _TINT_CACHE.get(key)
    if c is None:
        f = lv * 0.0625
        c = (int(color[0] * f), int(color[1] * f), int(color[2] * f))
        _TINT_CACHE[key] = c
    return c



class AlphaOverlay:
    """Superficie alfa del tamaño de la pantalla, reutilizada entre frames."""
    __slots__ = ("surf", "_filled", "_size")

    def __init__(self, size):
        self._size = tuple(size)
        self.surf = pygame.Surface(self._size, pygame.SRCALPHA)
        self.surf.fill((0, 0, 0, 0))
        self._filled = None

    def blit_fill(self, dest, rgba):
        """Rellena de (0,0,0,alpha) y pega; evita reallocar la superficie."""
        key = (int(rgba[3]),) if len(rgba) > 3 else rgba
        if self._filled != key:
            self.surf.fill(rgba)
            self._filled = key
        dest.blit(self.surf, (0, 0))

    def clear(self):
        if self._filled is not None:
            self.surf.fill((0, 0, 0, 0))
            self._filled = None


class Particle:
    __slots__ = ("x","y","vx","vy","color","life","max_life","size","gravity","friction")
    def __init__(self, x, y, vx, vy, color, life, size=2, gravity=60, friction=0.99):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.gravity = gravity
        self.friction = friction

    def update(self, dt):
        self.vx *= self.friction
        self.vy *= self.friction
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt

    def draw(self, surf):
        # Bucle ultra caliente (cientos por frame): lookup de tinte inlined.
        a = self.life / self.max_life
        if a < 0.0:
            a = 0.0
        elif a > 1.0:
            a = 1.0
        r = int(self.size * a)
        if r < 1:
            r = 1
        lv = int(a * 16)
        key = (self.color, lv)
        c = _TINT_CACHE.get(key)
        if c is None:
            f = lv * 0.0625
            col = self.color
            c = (int(col[0] * f), int(col[1] * f), int(col[2] * f))
            _TINT_CACHE[key] = c
        pygame.draw.rect(surf, c, (int(self.x), int(self.y), r, r))

    @property
    def alive(self):
        return self.life > 0



class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit(self, x, y, count, color, speed=80, life=0.8, size=2, gravity=60):
        for _ in range(count):
            angle = random.uniform(0, 2*math.pi)
            spd = random.uniform(speed*0.3, speed)
            self.particles.append(Particle(
                x, y, math.cos(angle)*spd, math.sin(angle)*spd - 30,
                color, random.uniform(life*0.5, life), size, gravity
            ))

    def emit_sparks(self, x, y, count=15):
        for _ in range(count):
            c = random.choice([C.C_YELLOW, C.C_ORANGE, C.C_WHITE, C.C_GREEN])
            self.emit(x, y, 1, c, speed=140, life=0.5, size=2, gravity=80)

    def emit_repair_burst(self, x, y):
        for _ in range(20):
            c = random.choice([C.C_GREEN, C.C_GREEN_DIM, C.C_CYAN, C.C_WHITE])
            self.emit(x, y, 1, c, speed=100, life=0.7, size=2, gravity=40)

    def emit_fail_burst(self, x, y):
        for _ in range(10):
            c = random.choice([C.C_RED, C.C_RED_DIM, C.C_ORANGE])
            self.emit(x, y, 1, c, speed=60, life=0.5, size=2, gravity=50)

    def emit_multi_bursts(self, x, y, bursts=4):
        for _ in range(bursts):
            bx = x + random.uniform(-40, 40)
            by = y + random.uniform(-20, 20)
            c = random.choice([C.C_GREEN, C.C_CYAN, C.C_YELLOW, C.C_PURPLE, C.C_GREEN_DIM])
            self.emit(bx, by, 8, c, speed=110, life=0.8, size=2, gravity=45)

    def update(self, dt):
        ps = self.particles
        i = 0
        for p in ps:
            p.update(dt)
            if p.life > 0:
                ps[i] = p
                i += 1
        del ps[i:]

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)

    def clear(self):
        self.particles.clear()


class FloatingText:
    def __init__(self, x, y, text, color, duration=1.0, font=None, size=14):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.duration = duration
        self.age = 0.0
        self.font = font or pygame.font.Font(None, size)
        self.alive = True
        self.scale = 0.0
        self._cache = {}

    def update(self, dt):
        self.age += dt
        self.y -= 20 * dt
        self.scale = min(1.0, self.age * 5) if self.age < 0.2 else max(0, 1.0 - (self.age - self.duration + 0.3) / 0.3)
        if self.age >= self.duration:
            self.alive = False

    def draw(self, surf):
        if self.scale <= 0:
            return
        # Cuantizamos alpha y escala: evita rasterizar y reescalar la misma
        # cadena decenas de veces por frame durante la aparición/desvanecido.
        alv = max(1, min(16, int(self.scale * 16)))
        a = alv / 16.0
        c = tint(self.color, a)
        key = (alv, c)
        img = self._cache.get(key)
        if img is None:
            txt = self.font.render(self.text, True, c)
            w, h = txt.get_size()
            # Escala cuantizada en 8 pasos: mantiene la proporción del texto
            # y evita reescalar la misma cadena en cada frame.
            k = 8 + int(round(a * 2))          # 8..10  ->  0.80..1.00
            img = pygame.transform.scale(txt, (max(1, w * k // 10), max(1, h * k // 10)))
            if len(self._cache) > 24:
                self._cache.clear()
            self._cache[key] = img
        surf.blit(img, (int(self.x - img.get_width() // 2), int(self.y - img.get_height() // 2)))




class FloatingTextSystem:
    def __init__(self):
        self.texts: List[FloatingText] = []

    def add(self, ft: FloatingText):
        self.texts.append(ft)

    def update(self, dt):
        ts = self.texts
        i = 0
        for t in ts:
            t.update(dt)
            if t.alive:
                ts[i] = t
                i += 1
        del ts[i:]

    def draw(self, surf):
        for t in self.texts:
            t.draw(surf)

    def clear(self):
        self.texts.clear()


class ScreenShake:
    def __init__(self):
        self.intensity = 0.0
        self.duration = 0.0
        self.age = 0.0
        self.offset_x = 0
        self.offset_y = 0

    def trigger(self, intensity=3.0, duration=0.3):
        self.intensity = intensity
        self.duration = duration
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        if self.age < self.duration:
            r = 1.0 - self.age / self.duration
            self.offset_x = int(random.uniform(-1, 1) * self.intensity * r)
            self.offset_y = int(random.uniform(-1, 1) * self.intensity * r)
        else:
            self.offset_x = self.offset_y = 0


class ConfettiSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def burst(self, x, y, count=50):
        colors = [C.C_GREEN, C.C_YELLOW, C.C_ORANGE, C.C_PURPLE, C.C_PINK, C.C_CYAN, C.C_BLUE, C.C_WHITE]
        for _ in range(count):
            angle = random.uniform(0, 2*math.pi)
            spd = random.uniform(60, 180)
            c = random.choice(colors)
            p = Particle(x, y, math.cos(angle)*spd, math.sin(angle)*spd - 100,
                         c, random.uniform(1.5, 3.5), random.randint(2, 4), gravity=40, friction=0.98)
            self.particles.append(p)

    def update(self, dt):
        ps = self.particles
        i = 0
        for p in ps:
            p.update(dt)
            if p.life > 0:
                ps[i] = p
                i += 1
        del ps[i:]

    def draw(self, surf):
        for p in self.particles:
            a = p.life / p.max_life
            if a < 0.3:
                a = 0.3
            sz = int(p.size * a)
            if sz < 1:
                sz = 1
            col = p.color
            key = (col, int(a * 16))
            c = _TINT_CACHE.get(key)
            if c is None:
                f = key[1] * 0.0625
                c = (int(col[0] * f), int(col[1] * f), int(col[2] * f))
                _TINT_CACHE[key] = c
            pygame.draw.rect(surf, c, (int(p.x), int(p.y), sz, sz))

    def clear(self):
        self.particles.clear()


class ResultAnimator:
    """Animación de resultado: salvajes chorros, ondas expansivas, banner, estrellas."""

    def __init__(self):
        self.outcome = None       # "WIN" | "LOSS" | "DRAW"
        self.age = 0.0
        self.ring_time = 0.0
        self.active = False
        self._shot = False
        self._colors = []
        self.stars_awarded = 0
        self._stars_reveal = [0.0, 0.0, 0.0]   # progreso de aparición x estrella
        # Un solo buffer reutilizado para los anillos: antes se creaba una
        # Surface SRCALPHA nueva por anillo y por frame.
        self._ring_buf = pygame.Surface((RING_MAX * 2 + 2, RING_MAX * 2 + 2), pygame.SRCALPHA)
        self._ring_buf.fill((0, 0, 0, 0))

    def start(self, outcome, cx, cy):
        self.outcome = outcome
        self.age = 0.0
        self.ring_time = 0.0
        self.active = True
        self._shot = False
        self.stars_awarded = {"WIN": 3, "DRAW": 2, "LOSS": 1}.get(outcome, 1)
        self._stars_reveal = [0.0, 0.0, 0.0]
        if outcome == "WIN":
            self._colors = [C.C_GOLD, C.C_YELLOW, C.C_GREEN, C.C_CYAN, C.C_PINK]
        elif outcome == "LOSS":
            self._colors = [C.C_RED, C.C_RED_DIM, C.C_ORANGE]
        else:
            self._colors = [C.C_YELLOW, C.C_GOLD, C.C_WHITE, C.C_CYAN]

    def reset(self):
        self.active = False
        self.outcome = None
        self.age = 0.0
        self.ring_time = 0.0
        self._stars_reveal = [1.0, 1.0, 1.0]

    def update(self, dt, particles, confetti, floating, center, fonts):
        if not self.active:
            return
        self.age += dt
        self.ring_time += dt
        x, y = center

        # ── Revelar estrellas conseguidas progresivamente ──
        for i in range(self.stars_awarded):
            start_t = 0.4 + i * 0.25
            if self.age >= start_t:
                self._stars_reveal[i] = min(1.0, self._stars_reveal[i] + dt * 3.0)
        # Chorros continuos desde el centro
        if self.age < 1.6:
            for _ in range(4):
                particles.emit(
                    x, y, 1, random.choice(self._colors),
                    speed=random.uniform(80, 160), life=0.9, size=2, gravity=50,
                )
        # Onda expansiva periódica
        if self.ring_time > 0.09:
            self.ring_time = 0.0
            confetti.burst(x + random.uniform(-15, 15),
                           y + random.uniform(-15, 15), 6)
        # Feedback words
        if not self._shot and self.age > 0.15:
            self._shot = True
            if self.outcome == "WIN":
                words = ["¡Increíble!", "Óptimo", "Perfecto"]
                for i, w in enumerate(words):
                    floating.add(FloatingText(
                        x + random.uniform(-60, 60), y - 40 - i * 10,
                        w, random.choice(self._colors), duration=1.4, font=fonts["sm"]))
            elif self.outcome == "LOSS":
                for i, w in enumerate(["Inténtalo de nuevo", "¡Ánimo!"]):
                    floating.add(FloatingText(
                        x + random.uniform(-50, 50), y - 30 - i * 10,
                        w, C.C_DIM, duration=1.4, font=fonts["sm"]))
            else:
                floating.add(FloatingText(x, y - 40, "¡Justo!", C.C_YELLOW,
                                          duration=1.4, font=fonts["sm"]))

    def draw_rings(self, surf, center):
        """Dibuja anillos expansivos que se desvanecen (buffer reutilizado)."""
        if not self.active:
            return
        x, y = center
        for i in range(3):
            r = int((self.age * 30) + i * 18)
            if r > 120 or r < 1:
                continue
            a = max(0, int(120 * (1 - r / 120)))
            c = self._colors[i % len(self._colors)]
            self._ring_buf.fill((0, 0, 0, 0))
            pygame.draw.circle(self._ring_buf, (*c, a), (r + 1, r + 1), r, 2)
            surf.blit(self._ring_buf, (int(x - r - 1), int(y - r - 1)))


    def banner_offset(self):
        """Desplazamiento vertical del banner (rebote de entrada)."""
        if not self.active:
            return 0
        if self.age < 0.25:
            return int((0.25 - self.age) * 260)   # entra desde arriba
        if self.age < 0.55:
            bounce = math.sin((self.age - 0.25) / 0.3 * math.pi)
            return int(-bounce * 18)
        return 0

    def draw_stars(self, surf, y, size=18):
        """Dibuja 3 estrellas: las conseguidas doradas con rebote, el resto apagadas."""
        W = surf.get_width()
        mid = W // 2
        total = 3
        spacing = size + 10
        start_x = mid - (total - 1) * spacing // 2
        for i in range(total):
            sx = start_x + i * spacing
            earned = i < self.stars_awarded
            reveal = self._stars_reveal[i] if earned else 0.0
            if earned:
                # Rebote de escala al aparecer (bounce)
                t = reveal
                if t < 1.0:
                    scale = t * (2 - t)          # ease-out
                else:
                    # pulso suave una vez aparecida
                    scale = 1.0 + 0.05 * math.sin(self.age * 6 + i)
                r = max(1, int((size // 2) * scale))
                self._draw_star(surf, sx, y, r, C.C_GOLD, glow=True)
            else:
                self._draw_star(surf, sx, y, size // 2, (70, 60, 60), glow=False)

    def _draw_star(self, surf, cx, cy, r, color, glow=False):
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = r if k % 2 == 0 else r * 0.45
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        if glow:
            # resplandor
            base = min(255, int(color[0] * 0.4) + 40)
            gc = (base, base, 40) if glow else color
            g = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.polygon(g, (255, 230, 120, 90), [
                (r + 4 + (p[0] - cx) * 1.3, r + 4 + (p[1] - cy) * 1.3) for p in pts
            ])
            surf.blit(g, (cx - r - 4, cy - r - 4))
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, C.C_WHITE, pts, 1)


class GlowRect:
    """Pulsing glow rectangle for selections."""
    def __init__(self, x, y, w, h, color=C.C_GLOW_CYAN, speed=5.0):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.color = color
        self.speed = speed
        self.time = 0.0

    def update(self, dt):
        self.time += dt * self.speed

    def draw(self, surf):
        pulse = 0.5 + 0.5 * math.sin(self.time)
        for i in range(3, 0, -1):
            a = int(40 * pulse * (1 - i/4))
            c = tuple(min(255, ch + a) for ch in self.color)
            r = pygame.Rect(self.x - i, self.y - i, self.w + i*2, self.h + i*2)
            pygame.draw.rect(surf, c, r, 1)
        # Inner glow
        a = int(60 * pulse)
        c = tuple(min(255, ch + a) for ch in self.color)
        pygame.draw.rect(surf, c, (self.x, self.y, self.w, self.h), 1)


class StarField:
    """Animated background star field."""
    def __init__(self, count=40):
        self.stars = []
        for _ in range(count):
            self.stars.append({
                'x': random.uniform(0, C.LOGICAL_W),
                'y': random.uniform(0, C.LOGICAL_H),
                'speed': random.uniform(5, 20),
                'size': random.choice([1, 1, 1, 2]),
                'color': random.choice(C.STAR_COLORS),
                'phase': random.uniform(0, 2*math.pi),
            })

    def update(self, dt):
        for s in self.stars:
            s['x'] -= s['speed'] * dt
            s['phase'] += dt * 2
            if s['x'] < -2:
                s['x'] = C.LOGICAL_W + 2
                s['y'] = random.uniform(0, C.LOGICAL_H)

    def draw(self, surf, time=0.0):
        for s in self.stars:
            twinkle = 0.6 + 0.4 * math.sin(s['phase'] + time)
            col = s['color']
            key = (col, int(twinkle * 16))
            c = _TINT_CACHE.get(key)
            if c is None:
                f = key[1] * 0.0625
                c = (int(col[0] * f), int(col[1] * f), int(col[2] * f))
                _TINT_CACHE[key] = c
            sz = s['size']
            pygame.draw.rect(surf, c, (int(s['x']), int(s['y']), sz, sz))



class ScreenTransition:
    """
    Fade con duración fija y ease-out.
    Antes usaba un acercamiento exponencial al objetivo: la pantalla se
    quedaba oscureciéndose ~2.4 s y el final se arrastraba. Con duración
    fija + ease-out el fundido entra rápido, se siente continuo y termina
    en el tiempo esperado.
    """
    FADE_IN = 0.26
    FADE_OUT = 0.14
    NAV_FADE = 0.18


    def __init__(self):
        self.alpha = 0.0
        self.active = False
        self._from = 0.0
        self._to = 0.0
        self._t = 0.0
        self._dur = 1.0
        self._overlay = None

    def fade_in(self, duration=None):
        self._start(255.0, 0.0, duration or self.FADE_IN)

    def fade_out(self, duration=None):
        self._start(0.0, 255.0, duration or self.FADE_OUT)

    def _start(self, a0, a1, duration):
        self._from, self._to = a0, a1
        self._dur = max(0.01, duration)
        self._t = 0.0
        self.alpha = a0
        self.active = True

    def update(self, dt):
        if not self.active:
            return
        self._t += dt
        p = self._t / self._dur
        if p >= 1.0:
            self.alpha = self._to
            self.active = False
            return
        ease = 1.0 - (1.0 - p) ** 3        # ease-out cúbico
        self.alpha = self._from + (self._to - self._from) * ease

    def draw(self, surf):
        a = int(self.alpha)
        if a <= 1:
            return
        if self._overlay is None or self._overlay.get_size() != surf.get_size():
            self._overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, a))
        surf.blit(self._overlay, (0, 0))



class ScoreDisplay:
    """Animated score counter that counts up smoothly."""
    def __init__(self):
        self.displayed = 0.0
        self.target = 0.0
        self.speed = 4.0

    def set_target(self, val):
        self.target = val

    def update(self, dt):
        diff = self.target - self.displayed
        self.displayed += diff * min(1.0, self.speed * dt)
        if abs(diff) < 0.5:
            self.displayed = self.target

    @property
    def value(self):
        return self.displayed
