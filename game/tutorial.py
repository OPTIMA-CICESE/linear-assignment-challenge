"""
Sistema de tutorial cinematográfico.
Personajes con bocadillos diferenciados, fondo desenfocado, secuencia paso a paso.
Renderizado en tutorial_render.py.
"""
from __future__ import annotations
import pygame
import math
from typing import List, Optional, Callable

from game.tutorial_render import draw_demo_repair, draw_exercise


CHAR_STYLES = {
    "profesor": {
        "shirt": "purple", "hair": "black", "facing": True,
        "name": "Profesor",
        "bubble_color": (25, 25, 60, 220),
        "bubble_border": (140, 100, 230),
        "bubble_accent": (180, 140, 255),
        "name_color": (180, 140, 255),
        "text_color": (220, 215, 240),
        "char_side": "left",
    },
    "tecnico": {
        "shirt": "blue", "hair": "brown", "facing": True,
        "name": "Técnico",
        "bubble_color": (15, 35, 50, 220),
        "bubble_border": (60, 180, 220),
        "bubble_accent": (80, 220, 255),
        "name_color": (80, 220, 255),
        "text_color": (200, 230, 245),
        "char_side": "left",
    },
    "robot": {
        "shirt": "orange", "hair": "black", "facing": False,
        "name": "■ PC PLAYER",
        "bubble_color": (45, 25, 15, 220),
        "bubble_border": (230, 150, 50),
        "bubble_accent": (255, 180, 70),
        "name_color": (255, 180, 70),
        "text_color": (240, 225, 200),
        "char_side": "right",
    },
}


class TutorialStep:
    def __init__(self, character: str, text: str, emotion: str = "normal",
                 demo: Optional[str] = None):
        self.character = character
        self.text = text
        self.emotion = emotion
        # demo: clave opcional de ejemplo animado (p. ej. "reparar").
        self.demo = demo


class TutorialSystem:
    # Duración del ejemplo animado "reparar": los niños NO deben saltárselo.
    DEMO_REPAIR_END = 21.0
    TUT_BG = (16, 18, 36)
    TUT_GOLD = (255, 212, 92)
    TUT_DIM = (150, 156, 196)

    def __init__(self, font_md, font_sm, font_xs, font_xxs):
        self.active = False
        self.steps: List[TutorialStep] = []
        self.current = 0
        self.char_text = ""
        self.char_target = ""
        self.typewriter_idx = 0
        self.typewriter_timer = 0.0
        self.global_time = 0.0
        self.step_time = 0.0
        self.alpha_bg = 0.0
        self.skip_alpha = 0.0
        self.hint_alpha = 0.0
        self._on_complete: Optional[Callable] = None

        self.font_md = font_md
        self.font_sm = font_sm
        self.font_xs = font_xs
        self.font_xxs = font_xxs

        # ── Interactive exercise state ──
        self.exercise_active = False
        self.exercise_pcs = []          # [{x,y,health,bar_x,bar_y,bar_w}]
        self.exercise_pieces = []       # [{x,y,name,contrib,assigned_to}]
        self.exercise_assignment = [-1, -1]
        self.exercise_done = False
        self.exercise_dragging = -1
        self.exercise_drag_off = (0, 0)
        self.exercise_msg = ""
        self.exercise_msg_color = (200, 200, 200)
        self.exercise_click_fx = []     # [{x,y,timer}]
        self.exercise_arrow_fx = []     # [{x1,y1,x2,y2,timer}]

    def start(self, steps: List[TutorialStep], on_complete: Optional[Callable] = None):
        self.active = True
        self.steps = steps
        self.current = 0
        self.char_text = ""
        self.char_target = steps[0].text if steps else ""
        self.typewriter_idx = 0
        self.step_time = 0.0
        self.typewriter_timer = 0.0
        self.alpha_bg = 0.0
        self.global_time = 0.0
        self._on_complete = on_complete

    def skip(self):
        if not self.can_skip():
            return
        self.active = False
        self.exercise_active = False
        if self._on_complete:
            self._on_complete()

    def can_skip(self) -> bool:
        """No dejar saltar mientras corre la animación del ejemplo o el ejercicio."""
        if not self.active:
            return True
        if self.exercise_active and not self.exercise_done:
            return False
        if (self.current < len(self.steps)
                and self.steps[self.current].demo == "reparar"
                and self.step_time < TutorialSystem.DEMO_REPAIR_END):
            return False
        return True

    def _setup_exercise(self):
        """Set up a mini-exercise: 2 PCs, 2 pieces with different contributions."""
        W = 480
        mid = W // 2
        self.exercise_active = True
        self.exercise_done = False
        self.exercise_dragging = -1
        self._exercise_hover_pc = -1
        self._exercise_target_pc = 0
        self.exercise_select_time = 0.0
        self.exercise_assignment = [-1, -1]
        self.exercise_msg = "← → elige pieza  ·  ↑ ↓ cambia PC  ·  ENTER coloca"
        self.exercise_msg_color = (200, 200, 200)
        self.exercise_click_fx = []
        self.exercise_arrow_fx = []
        self._exercise_contrib = [[70, 40], [35, 55]]

        pc_sz = 46
        pc_gap = 130
        pc_x0 = mid - pc_gap // 2 - pc_sz // 2
        self.exercise_pcs = [
            {"x": pc_x0, "y": 60, "health": 30, "target": 100,
             "bar_x": pc_x0, "bar_y": 60 + pc_sz + 3, "bar_w": pc_sz},
            {"x": pc_x0 + pc_gap, "y": 60, "health": 55, "target": 100,
             "bar_x": pc_x0 + pc_gap, "bar_y": 60 + pc_sz + 3, "bar_w": pc_sz},
        ]

        piece_sz = 32
        piece_gap = 112
        piece_x0 = mid - piece_gap // 2 - piece_sz // 2
        piece_y = 148
        self.exercise_pieces = [
            {"x": piece_x0, "y": piece_y, "name": "CPU", "contrib": 70,
             "orig_x": piece_x0, "orig_y": piece_y, "assigned_to": -1},
            {"x": piece_x0 + piece_gap, "y": piece_y, "name": "GPU", "contrib": 35,
             "orig_x": piece_x0 + piece_gap, "orig_y": piece_y, "assigned_to": -1},
        ]

    def _exercise_pc_repaired(self, ci) -> bool:
        """True si la PC ci ya está reparada con la pieza asignada."""
        pi = self.exercise_assignment[ci]
        if pi < 0:
            return False
        return (self.exercise_pcs[ci]["health"]
                + self._exercise_contrib[pi][ci]) >= 100

    def _exercise_default_target(self, pi) -> int:
        """PC correcta para la pieza pi (la que repara); si no, la primera libre."""
        empty = [ci for ci, a in enumerate(self.exercise_assignment) if a < 0]
        for ci in empty:
            if self.exercise_pcs[ci]["health"] + self._exercise_contrib[pi][ci] >= 100:
                return ci
        return empty[0] if empty else -1

    def exercise_update(self, dt):
        """Update exercise animations and effects."""
        for fx in self.exercise_click_fx:
            fx["timer"] -= dt
        self.exercise_click_fx = [f for f in self.exercise_click_fx if f["timer"] > 0]
        for fx in self.exercise_arrow_fx:
            fx["timer"] -= dt
        self.exercise_arrow_fx = [f for f in self.exercise_arrow_fx if f["timer"] > 0]

    def exercise_mouse_down(self, mx, my):
        """Handle mouse down during exercise. Returns True if consumed."""
        if not self.exercise_active or self.exercise_done:
            return False

        for pi, p in enumerate(self.exercise_pieces):
            if p["assigned_to"] >= 0:
                continue
            r = pygame.Rect(p["x"], p["y"], 22, 22)
            if r.collidepoint(mx, my):
                self.exercise_dragging = pi
                self.exercise_select_time = self.global_time
                t = self._exercise_default_target(pi)
                if t >= 0:
                    self._exercise_target_pc = t
                self.exercise_drag_off = (mx - p["x"], my - p["y"])
                # Click animation
                self.exercise_click_fx.append({"x": mx, "y": my, "timer": 0.4})
                return True
        return False

    def exercise_mouse_up(self, mx, my):
        """Handle mouse up during exercise. Returns True if piece placed."""
        if not self.exercise_active or self.exercise_dragging < 0:
            return False

        pi = self.exercise_dragging
        self.exercise_dragging = -1
        p = self.exercise_pieces[pi]

        # Check if dropped on a PC
        for ci, pc in enumerate(self.exercise_pcs):
            r = pygame.Rect(pc["x"] - 4, pc["y"] - 4, 40, 40)
            if r.collidepoint(mx, my):
                if self.exercise_assignment[ci] >= 0:
                    self.exercise_msg = "¡Solo 1 pieza por PC!"
                    self.exercise_msg_color = (220, 75, 75)
                    p["x"], p["y"] = p["orig_x"], p["orig_y"]
                    return True

                # Solo se acepta si la pieza deja la PC reparada
                contrib = self._exercise_contrib[pi][ci]
                total = pc["health"] + contrib
                if total < 100:
                    self.exercise_msg = (
                        f"{p['name']} +{contrib}% → PC-{ci+1} = {total}%."
                        f" No alcanza, prueba en la otra"
                    )
                    self.exercise_msg_color = (240, 220, 65)
                    p["x"], p["y"] = p["orig_x"], p["orig_y"]
                    return True

                # Assign piece to PC
                self.exercise_assignment[ci] = pi
                p["assigned_to"] = ci
                p["x"] = pc["x"] + 5
                p["y"] = pc["y"] + 5

                # Arrow animation
                self.exercise_arrow_fx.append({
                    "x1": p["orig_x"] + 11, "y1": p["orig_y"] + 11,
                    "x2": pc["x"] + 16, "y2": pc["y"] + 16,
                    "timer": 0.5
                })

                self.exercise_msg = f"¡{p['name']} +{contrib}% = {total}% reparada! ✓"
                self.exercise_msg_color = (70, 210, 110)

                # Check if exercise complete (ambas PCs reparadas)
                if all(self._exercise_pc_repaired(ci2)
                       for ci2 in range(len(self.exercise_pcs))):
                    self.exercise_done = True
                    self.exercise_msg = "¡Muy bien! Reparaste las 2 computadoras"
                    self.exercise_msg_color = (70, 210, 110)
                return True

        # Dropped on nothing — return to original position
        p["x"], p["y"] = p["orig_x"], p["orig_y"]
        return False

    def exercise_mouse_move(self, mx, my):
        """Update drag position and target PC under the piece (ratón)."""
        if self.exercise_dragging >= 0:
            p = self.exercise_pieces[self.exercise_dragging]
            p["x"] = mx - self.exercise_drag_off[0]
            p["y"] = my - self.exercise_drag_off[1]
            # PC-1 o PC-2 según dónde esté la pieza
            cx, cy = p["x"] + 11, p["y"] + 11
            for ci, pc in enumerate(self.exercise_pcs):
                r = pygame.Rect(pc["x"] - 4, pc["y"] - 4, 40, 40)
                if r.collidepoint(cx, cy) and self.exercise_assignment[ci] < 0:
                    self._exercise_target_pc = ci
                    break

    def exercise_key_down(self, key):
        """Handle keyboard during exercise:
        LEFT/RIGHT = select piece, UP/DOWN = select target PC, ENTER = assign."""
        if not self.exercise_active or self.exercise_done:
            return

        unassigned_pieces = [i for i, p in enumerate(self.exercise_pieces) if p["assigned_to"] < 0]
        empty_pcs = [ci for ci, a in enumerate(self.exercise_assignment) if a < 0]

        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            current = self.exercise_dragging if self.exercise_dragging >= 0 else -1
            if not unassigned_pieces:
                return
            if current in unassigned_pieces:
                idx = unassigned_pieces.index(current)
                next_idx = (idx + (1 if key == pygame.K_RIGHT else -1)) % len(unassigned_pieces)
                self.exercise_dragging = unassigned_pieces[next_idx]
            else:
                self.exercise_dragging = unassigned_pieces[0]
            self.exercise_select_time = self.global_time
            # Al elegir una pieza, marcar la PC donde sí la repara
            pi = self.exercise_dragging
            p = self.exercise_pieces[pi]
            target = self._exercise_default_target(pi)
            if target >= 0:
                self._exercise_target_pc = target
            if target in empty_pcs:
                contrib = self._exercise_contrib[pi][target]
                total = self.exercise_pcs[target]["health"] + contrib
                if total >= 100:
                    self.exercise_msg = f"{p['name']} → PC-{target+1}: +{contrib}% = {total}% ✓"
                    self.exercise_msg_color = (70, 210, 110)
                else:
                    self.exercise_msg = f"{p['name']} → PC-{target+1}: +{contrib}% = {total}%..."
                    self.exercise_msg_color = (240, 220, 65)

        elif key in (pygame.K_UP, pygame.K_DOWN):
            if self.exercise_dragging < 0:
                if unassigned_pieces:
                    self.exercise_dragging = unassigned_pieces[0]
                    self.exercise_select_time = self.global_time
                    t = self._exercise_default_target(unassigned_pieces[0])
                    if t >= 0:
                        self._exercise_target_pc = t
                    return
            if empty_pcs:
                current = getattr(self, '_exercise_target_pc', empty_pcs[0])
                if current not in empty_pcs:
                    current = empty_pcs[0]
                idx = empty_pcs.index(current)
                next_idx = (idx + (1 if key == pygame.K_DOWN else -1)) % len(empty_pcs)
                self._exercise_target_pc = empty_pcs[next_idx]
            # Show dynamic feedback for target PC
            pi = self.exercise_dragging
            if pi >= 0:
                p = self.exercise_pieces[pi]
                target = self._exercise_target_pc
                if target in empty_pcs:
                    contrib = self._exercise_contrib[pi][target]
                    total = self.exercise_pcs[target]["health"] + contrib
                    if total >= 100:
                        self.exercise_msg = f"{p['name']} → PC-{target+1}: +{contrib}% = {total}% ✓"
                        self.exercise_msg_color = (70, 210, 110)
                    else:
                        self.exercise_msg = f"{p['name']} → PC-{target+1}: +{contrib}% = {total}%..."
                        self.exercise_msg_color = (240, 220, 65)

        elif key == pygame.K_RETURN and self.exercise_dragging >= 0:
            pi = self.exercise_dragging
            p = self.exercise_pieces[pi]
            # Find target PC: use _exercise_target_pc if valid, else first empty
            target = -1
            if hasattr(self, '_exercise_target_pc') and self._exercise_target_pc in empty_pcs:
                target = self._exercise_target_pc
            elif empty_pcs:
                target = empty_pcs[0]

            if target < 0:
                return

            pc = self.exercise_pcs[target]
            contrib = self._exercise_contrib[pi][target]
            total = pc["health"] + contrib

            # Solo se acepta si la pieza deja la PC reparada
            if total < 100:
                self.exercise_msg = (
                    f"{p['name']} +{contrib}% → PC-{target+1} = {total}%."
                    f" No alcanza, prueba en la otra"
                )
                self.exercise_msg_color = (240, 220, 65)
                return

            self.exercise_assignment[target] = pi
            p["assigned_to"] = target
            p["x"] = pc["x"] + 5
            p["y"] = pc["y"] + 5
            self.exercise_click_fx.append({"x": pc["x"] + 16, "y": pc["y"] + 16, "timer": 0.4})
            self.exercise_arrow_fx.append({
                "x1": p["orig_x"] + 11, "y1": p["orig_y"] + 11,
                "x2": pc["x"] + 16, "y2": pc["y"] + 16,
                "timer": 0.5
            })
            self.exercise_msg = f"¡{p['name']} +{contrib}% → PC-{target+1} = {total}% ✓"
            self.exercise_msg_color = (70, 210, 110)
            self.exercise_dragging = -1
            if hasattr(self, '_exercise_target_pc'):
                del self._exercise_target_pc
            if all(self._exercise_pc_repaired(ci2)
                   for ci2 in range(len(self.exercise_pcs))):
                self.exercise_done = True
                self.exercise_msg = "¡Muy bien! Reparaste las 2 computadoras"
                self.exercise_msg_color = (70, 210, 110)

    def advance(self) -> bool:
        """Avanzar al siguiente paso. Bloqueado durante el ejemplo o ejercicio."""
        if not self.active:
            return False
        if self.exercise_active and not self.exercise_done:
            return False
        if (self.current < len(self.steps)
                and self.steps[self.current].demo == "reparar"
                and self.step_time < TutorialSystem.DEMO_REPAIR_END):
            return False
        self.current += 1
        if self.current >= len(self.steps):
            self.active = False
            self.exercise_active = False
            if self._on_complete:
                self._on_complete()
            return True
        self.char_target = self.steps[self.current].text
        self.char_text = ""
        self.typewriter_idx = 0
        self.step_time = 0.0
        if self.steps[self.current].demo == "ejercicio":
            self._setup_exercise()
        return True

    def update(self, dt):
        """Timers globales, máquina de escribir y suavizado de fades."""
        if not self.active:
            return
        self.global_time += dt
        self.step_time += dt
        self.alpha_bg = min(1.0, self.alpha_bg + dt * 2.5)
        self.skip_alpha = min(0.9, self.skip_alpha + dt * 2.0)
        self.hint_alpha = min(0.9, self.hint_alpha + dt * 1.5)
        if self.exercise_active:
            self.exercise_update(dt)

        if self.typewriter_idx < len(self.char_target):
            self.typewriter_timer -= dt
            while self.typewriter_timer <= 0 and self.typewriter_idx < len(self.char_target):
                self.typewriter_idx += 1
                self.typewriter_timer += 0.03
            self.char_text = self.char_target[: self.typewriter_idx]

    def draw(self, surf, sprites, global_time, shake_ox=0, shake_oy=0):
        """Dibuja tutorial: fondo limpio, animaciones grandes y barra de instrucciones."""
        if not self.active:
            return

        W, H = surf.get_size()
        t = global_time

        # ── Fondo limpio + decoración animada ──────────────
        surf.fill(self.TUT_BG)
        for i in range(10):
            phi = t * 0.45 + i * 1.7
            x = int((i * 89 + math.sin(phi) * 34) % (W + 40)) - 20
            y = int((i * 43 + math.cos(phi * 0.8) * 26) % (H + 40)) - 20
            r = 5 + (i % 3) * 5
            orb = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(orb, (120, 132, 255, 26), (r, r), r)
            surf.blit(orb, (int(x - r), int(y - r)))
        for i in range(7):
            phi = t * 1.2 + i * 2.3
            x = int((i * 71 + math.sin(phi) * 40) % W)
            y = int((i * 55 + math.cos(phi * 0.7) * 20) % H)
            glow = pygame.Surface((5, 5), pygame.SRCALPHA)
            pygame.draw.line(glow, (255, 255, 255, 62), (2, 0), (2, 4), 2)
            pygame.draw.line(glow, (255, 255, 255, 62), (0, 2), (4, 2), 2)
            surf.blit(glow, (int(x), int(y)))

        if self.current >= len(self.steps):
            return

        step = self.steps[self.current]
        style = CHAR_STYLES.get(step.character, CHAR_STYLES["tecnico"])

        # ── Encabezado: título + progreso ──────────────────
        hd = self.font_md.render("TUTORIAL", True, self.TUT_GOLD)
        surf.blit(hd, (10, 6))
        pw = 170
        pygame.draw.rect(surf, (54, 58, 100), (10, 27, pw, 4))
        fw = max(0, int(pw * (self.current + 1) / len(self.steps)))
        if fw:
            pygame.draw.rect(surf, self.TUT_GOLD, (10, 27, fw, 4))
        hnt = self.font_xxs.render("ESC: saltar", True, self.TUT_DIM)
        hnt.set_alpha(int(self.skip_alpha * 255))
        surf.blit(hnt, (W - hnt.get_width() - 8, 10))

        # ── Animaciones (ejemplo / ejercicio), grandes ─────
        if step.demo == "reparar":
            draw_demo_repair(surf, sprites, self.step_time, self.font_sm, self.font_xs)
        elif step.demo == "ejercicio":
            if not self.exercise_active:
                self._setup_exercise()
            self.exercise_update(1 / 60)
            draw_exercise(self, surf, sprites)

        # ── Barra de instrucciones grande (inferior) ───────
        bar_h = self._draw_instruction_bar(surf, step, style)

        # ── Personaje grande (solo pasos de charla) ────────
        if not step.demo:
            self._draw_character(surf, sprites, step, style, t, bar_h)

    def _draw_instruction_bar(self, surf, step, style) -> int:
        """Barra inferior con la instrucción, en texto grande."""
        W, H = surf.get_size()
        f = self.font_sm
        shown = self.char_text if self.char_text else (step.text or "")
        name_lbl = f.render(style["name"] + ":", True, style["name_color"])
        tx = 14 + name_lbl.get_width() + 12
        wrap_w = W - tx - 14
        lines = []
        cur = ""
        for w in shown.split(" "):
            test = (cur + " " + w).strip()
            if f.size(test)[0] <= wrap_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        lines = lines[:3]
        line_h = 18
        bar_h = 12 + len(lines) * line_h + 8

        bar = pygame.Surface((W, bar_h), pygame.SRCALPHA)
        bar.fill((12, 12, 28, 216))
        surf.blit(bar, (0, H - bar_h))
        pygame.draw.line(surf, style["bubble_accent"], (0, H - bar_h), (W, H - bar_h), 2)

        surf.blit(name_lbl, (10, H - bar_h + 9))
        for i, line in enumerate(lines):
            lt = f.render(line, True, style["text_color"])
            surf.blit(lt, (tx, H - bar_h + 9 + i * line_h))
        return bar_h

    def _draw_character(self, surf, sprites, step, style, t, bar_h):
        """Personaje grande flotando sobre los pasos de charla."""
        W, H = surf.get_size()
        bob = int(math.sin(t * 2) * 2)
        if step.character == "robot":
            char = sprites.get_octopus(int(t * 3) % 8, win=False)
        else:
            char = sprites.get_technician(
                style["shirt"], style["hair"], style["facing"],
                int(t * 3) % 4,
            )
        bigger = pygame.transform.scale(char, (58, 64))
        if style["char_side"] == "left":
            cx, cy = 16, H - bar_h - 72 + bob
        else:
            cx, cy = W - 74, H - bar_h - 72 + bob

        glow = pygame.Surface((70, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*style["bubble_accent"], 90), (0, 0, 70, 18))
        surf.blit(glow, (cx + 29 - 35, cy + 68))

        surf.blit(bigger, (cx, cy))
        nm = self.font_xs.render(style["name"], True, style["name_color"])
        surf.blit(nm, (cx + 29 - nm.get_width() // 2, cy - 14))

def get_default_tutorial() -> List[TutorialStep]:
    return [
        TutorialStep(
            "profesor",
            "¡Hola! Soy el Profesor. ¡Bienvenido a PC Repair Challenge!",
        ),
        TutorialStep(
            "profesor",
            "Aquí llegan computadoras dañadas y tú eres el técnico que las arregla.",
        ),
        TutorialStep(
            "tecnico",
            "¿Yo las arreglo? ¡Qué buena idea! ¿Y cómo le hago?",
        ),
        TutorialStep(
            "robot",
            "¡Hola! Soy el PC PLAYER, un algoritmo genético. ¡También reparamos computadoras!",
        ),
        TutorialStep(
            "profesor",
            "¡Mira este ejemplo! Fíjate cuánto aporta cada pieza a cada PC.",
            demo="reparar",
        ),
        TutorialStep(
            "profesor",
            "¡Ahora prueba tú! Elige una pieza y mira sus valores.",
            demo="ejercicio",
        ),
        TutorialStep(
            "robot",
            "¡Ese es el problema de asignación lineal! Elige la mejor pieza para cada PC y ve el progreso. ¡Mucha suerte!",
        ),
    ]