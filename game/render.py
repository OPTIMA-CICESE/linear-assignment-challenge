"""
Rendering layer — draws every screen onto the logical surface.
Kept separate from game logic so game/engine.py stays small.
"""
from __future__ import annotations
import os, math, random
import pygame
import config as C
from game.states import State
from ui.effects import GlowRect


class GameRenderer:

    def __init__(self, game):
        self.g = game
        self.logos = self._load_logos()
        # Cachés de superficies y texto: crear Surface(SRCALPHA) y renderizar
        # fuentes cada frame es lo más caro del render a 480x270.
        self._chip_cache = {}
        self._scaled_cache = {}
        self._text_cache = {}
        self._disc_cache = {}
        self._socket_cache = {}
        self._strip_cache = {}
        self._frame_cache = {}
        self._screen_buf = None
        self._logo_cache = {}



    def _load_logos(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logos = []
        for name in ("OPTIMA2-N.png", "logo-cicese.png", "iee.png"):
            # assets/logos/ es la ubicación canónica; la raíz se mantiene como
            # fallback para copias antiguas del proyecto.
            for folder in ("assets/logos", ""):
                path = os.path.join(base, folder, name)
                if os.path.isfile(path):
                    break
            else:
                continue
            try:
                logos.append(pygame.image.load(path).convert_alpha())
            except Exception:
                pass
        return logos

    def _alpha_rect(self, w, h, rgba):
        """Surface SRCALPHA rellena, cacheada por (w, h, color).
        El alpha se cuantiza a pasos de 8 para que los pulsos animados no
        generen una entrada nueva por frame."""
        r, g, b, a = int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])
        a = (a // 8) * 8
        key = (w, h, r, g, b, a)
        s = self._chip_cache.get(key)
        if s is None:
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((r, g, b, a))
            if len(self._chip_cache) > 600:
                self._chip_cache.clear()
            self._chip_cache[key] = s
        return s


    def _scale_cached(self, surf, w, h):
        key = (id(surf), w, h)
        s = self._scaled_cache.get(key)
        if s is None:
            s = pygame.transform.scale(surf, (w, h))
            self._scaled_cache[key] = s
        return s

    def _text(self, font, text, color):
        """Texto renderizado cacheado: evita re-rasterizar la misma cadena cada frame.
        NO mutar el resultado (set_alpha) — la superficie es compartida."""
        key = (id(font), text, tuple(color))
        t = self._text_cache.get(key)
        if t is None:
            t = font.render(text, True, color)
            if len(self._text_cache) > 3000:
                self._text_cache.clear()
            self._text_cache[key] = t
        return t


    def _dashed_rect(self, surf, x, y, w, h, color, phase_offset=0):
        """Borde punteado (pixel art) para marcar 'slot vacío'."""
        step = 2
        for i in range(0, w, step):
            if (i + phase_offset) % 4 < 2:
                surf.set_at((x + i, y), color)
                surf.set_at((x + i, y + h - 1), color)
        for i in range(0, h, step):
            if (i + phase_offset) % 4 < 2:
                surf.set_at((x, y + i), color)
                surf.set_at((x + w - 1, y + i), color)

    def _glow_disc(self, r, color, alpha):
        """Círculo difuso cacheado (los orbes de fondo lo creaban cada frame)."""
        r = max(2, (int(r) // 3) * 3)
        alpha = max(0, min(255, (int(alpha) // 8) * 8))
        key = (r, color, alpha)
        s = self._disc_cache.get(key)
        if s is None:
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            steps = 3
            for i in range(steps, 0, -1):
                rr = int(r * i / steps)
                aa = int(alpha / steps)
                pygame.draw.circle(s, (*color, aa), (r, r), rr)
            if len(self._disc_cache) > 400:
                self._disc_cache.clear()
            self._disc_cache[key] = s
        return s

    def _socket_img(self, edge, show_plus):
        """Socket vacío 10x10 pre-dibujado (borde punteado + '+')."""
        key = (edge, show_plus)
        img = self._socket_cache.get(key)
        if img is None:
            img = pygame.Surface((10, 10), pygame.SRCALPHA)
            img.fill((0, 0, 0, 110))
            self._dashed_rect(img, 0, 0, 10, 10, edge, 0)
            if show_plus:
                plus = self.g.font_xxs.render("+", True, edge)
                img.blit(plus, ((10 - plus.get_width()) // 2,
                                (10 - plus.get_height()) // 2))
            self._socket_cache[key] = img
        return img

    def _fill_screen(self, surf, rgba):
        """Tiñe toda la pantalla con un color alfa usando un buffer reutilizado.
        Cachear esto por nivel de alpha ocuparía decenas de MB (480x270x4)."""
        buf = self._screen_buf
        if buf is None or buf.get_size() != surf.get_size():
            buf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            self._screen_buf = buf
        a = int(rgba[3])
        if a < 0:
            a = 0
        elif a > 255:
            a = 255
        buf.fill((int(rgba[0]), int(rgba[1]), int(rgba[2]), a))
        surf.blit(buf, (0, 0))

    def _glow_frame(self, alpha):
        """Marco 36x36 cacheado por nivel de alpha (ghost de arrastre)."""

        img = self._frame_cache.get(alpha)
        if img is None:
            img = pygame.Surface((36, 36), pygame.SRCALPHA)
            pygame.draw.rect(img, (*C.C_GLOW_CYAN, alpha), img.get_rect(), 2)
            self._frame_cache[alpha] = img
        return img

    def _divider_strip(self, step):
        """Franja vertical de 3px con la onda del centro, cacheada por paso."""
        strip = self._strip_cache.get(step)
        if strip is None:
            strip = pygame.Surface((3, 185))
            for y in range(185):
                wave = int(math.sin(y * 0.08 + step) * 1)
                c = C.C_BORDER_LIGHT if y % 4 == 0 else C.C_BORDER
                strip.set_at((1 + wave, y), c)
            if len(self._strip_cache) > 40:
                self._strip_cache.clear()
            self._strip_cache[step] = strip
        return strip

    

    def _draw_logos_bottom(self, surf, ox, oy):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        t = self.g.global_time
        if not self.logos:
            return
    
        n = len(self.logos)
        gap = W // (n + 1)
        logo_h = 12
    
        for i, img in enumerate(self.logos):
            # El reescalado (smoothscale sobre PNG grandes) se hace UNA vez y
            # se cachea: hacerlo cada frame costaba ~6 ms en el menú.
            scaled = self._logo_cache.get(i)
            if scaled is None:
                iw, ih = img.get_size()
                new_w = max(1, int(iw * (logo_h / ih)))
                scaled = pygame.transform.smoothscale(img.convert_alpha(), (new_w, logo_h))
                self._logo_cache[i] = scaled
            new_w = scaled.get_width()
    
            # Gentle bob animation
            bx = gap * (i + 1) - new_w // 2
            by = H - logo_h - 4 + int(math.sin(t * 1.5 + i * 2.0) * 2)
    
            # Pulsing alpha
            alpha = int(180 + 60 * math.sin(t * 1.2 + i * 1.5))
            alpha = max(100, min(255, alpha))
            scaled.set_alpha(alpha)
            surf.blit(scaled, (bx + ox, by + oy))

    def render(self, surf, window):
        surf.fill(C.C_BG)
        self.g._comp_rects.clear()
        self.g._cpu_rects.clear()
        self.g._menu_rects.clear()
        self.g._level_rects.clear()
        self.g._result_rects.clear()

        ox, oy = self.g.shake.offset_x, self.g.shake.offset_y

        self.g.stars.draw(surf, self.g.global_time)

        if self.g.state == State.TUTORIAL:
            self._draw_game(surf, ox, oy)
            self.g.tutorial.draw(surf, self.g.sprites, self.g.global_time, ox, oy)
        elif self.g.state == State.MENU:
            self._draw_menu(surf, ox, oy)
        elif self.g.state == State.LEVEL_SELECT:
            self._draw_level_select(surf, ox, oy)
        elif self.g.state == State.SETTINGS:
            self._draw_settings(surf, ox, oy)
        elif self.g.state == State.CREDITS:
            self._draw_credits(surf, ox, oy)
        elif self.g.state in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING, State.AI_TURN):
            self._draw_game(surf, ox, oy)
        elif self.g.state == State.RESULT:
            self._draw_game(surf, ox, oy)
            self._draw_result_overlay(surf)

        if self.g.state in (State.MENU, State.SETTINGS, State.LEVEL_SELECT):
            self._draw_logos_bottom(surf, ox, oy)

        self.g.particles.draw(surf)
        self.g.floating.draw(surf)
        self.g.confetti.draw(surf)

        if self.g.dragging and self.g.state == State.DRAGGING:
            self.draw_drag_ghost(surf)

        if self.g.level_transition_active:
            self._draw_level_transition(surf, ox, oy)

        self._draw_mode_toast(surf, ox, oy)

        self.g.transition.draw(surf)

        window.blit(surf, (0, 0))
        pygame.display.flip()
    
    # ── Menu ───────────────────────────────────────────────
    

    def _draw_mode_toast(self, surf, ox, oy):
        """Aviso emergente al cambiar de modo con la tecla G."""
        if not self.g.mode_toast:
            return
        texto, left = self.g.mode_toast
        if left <= 0:
            return
        alpha = 255 if left > 0.6 else max(0, int(255 * (left / 0.6)))
        d_idx = min(self.g.difficulty, len(C.DIFFICULTIES) - 1)
        border = [C.C_CYAN, C.C_GREEN, C.C_GOLD, C.C_RED][d_idx]
        t = self._text(self.g.font_xs, texto, C.C_WHITE)
        bw, bh = t.get_width() + 18, t.get_height() + 10
        bx = C.LOGICAL_W // 2 - bw // 2
        by = 112
        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((18, 18, 42, int(alpha * 0.92)))
        surf.blit(box, (bx + ox, by + oy))
        pygame.draw.rect(surf, tuple(int(c * alpha / 255) for c in border),
                         pygame.Rect(bx, by, bw, bh).move(ox, oy), 1)
        surf.blit(t, (bx + 9 + ox, by + 5 + oy))

    def _draw_menu(self, surf, ox, oy):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid_x = W // 2
        t = self.g.global_time
    
        # ── Luminous background orbs ──
        cols = (C.C_CYAN, C.C_PURPLE, C.C_GREEN, C.C_GOLD, C.C_ORANGE, C.C_CYAN)
        for i in range(6):
            gx = int(W * 0.1 + math.sin(t * 0.12 + i * 1.5) * W * 0.3)
            gy = int(H * 0.1 + math.cos(t * 0.15 + i * 2.1) * H * 0.35)
            gr = int(25 + 18 * math.sin(t * 0.25 + i))
            alpha = 15 + 10 * math.sin(t * 0.4 + i)
            surf.blit(self._glow_disc(gr, cols[i], alpha), (gx - gr + ox, gy - gr + oy))
    
        # ── Floating particles ──
        for i in range(12):
            px = int((20 + i * 40 + math.sin(t * 0.3 + i) * 25) % W)
            py = int((5 + i * 23 + math.cos(t * 0.4 + i * 0.7) * 18) % H)
            pa = 25 + 22 * math.sin(t * 2 + i * 1.3)
            surf.blit(self._alpha_rect(4, 4, (*C.C_CYAN, pa)), (px + ox, py + oy))
    
        # ── Stars ──
        for i in range(10):
            sx = int((15 + i * 48) % W)
            sy = int((5 + i * 27) % (H // 3))
            sa = 25 + 20 * math.sin(t * 2.5 + i * 1.7)
            sc = (C.C_GOLD, C.C_WHITE, C.C_CYAN)[(i * 7 + int(t * 2)) % 3]
            surf.blit(self._alpha_rect(5, 5, (*sc, sa)), (sx + ox, sy + oy))
    
        # ── Title ──
        pulse = math.sin(t * 2) * 2
        t1 = self._text(self.g.font_title, "PC REPAIR", C.C_TITLE)
        t2 = self._text(self.g.font_title, "CHALLENGE", C.C_TITLE)
        ty = 12 + int(pulse)
        surf.blit(t1, (mid_x - t1.get_width() // 2 + ox, ty + oy))
        surf.blit(t2, (mid_x - t2.get_width() // 2 + ox, ty + 34 + oy))
    
        sub = self._text(
            self.g.font_xs,
            "¿Puedes reparar más PCs que un algoritmo genético?", C.C_SUBTITLE
        )
        surf.blit(sub, (mid_x - sub.get_width() // 2 + ox, ty + 74 + oy))
    
        # ── Characters ──
        tech_l = self.g.sprites.get_technician("blue", "brown", True, self.g.char_frame)
        surf.blit(tech_l, (50 + ox, ty + 90 + oy))
        gear = self.g.sprites.get_gear(self.g.gear_frame)
        surf.blit(gear, (80 + ox, ty + 100 + oy))
        comp_r = self.g.sprites.get_computer("repaired", 100, self.g.computer_frame)
        surf.blit(comp_r, (W - 80 + ox, ty + 88 + oy))
        gear2 = self.g.sprites.get_gear(self.g.gear_frame + 4)
        surf.blit(gear2, (W - 90 + ox, ty + 100 + oy))
    
        # ── Menu orbs (2 rows x 3 columns) ──
        orb_r = 18
        gap_x = 52
        gap_y = 52
        grid_start_x = mid_x - gap_x
        grid_start_y = ty + 138
    
        # Solo simbolos con glifo en la fuente empaquetada (ver assets/fonts/).
        orb_icons = ("▶", "☰", "?", "⚙", "✦", "✕")
        orb_labels = ("Iniciar", "Niveles", "Tutorial", "Ajustes", "Créditos", "Salir")
    
        for i, item in enumerate(self.g.menu_items):
            row = i // 3
            col = i % 3
            cx = grid_start_x + col * gap_x
            cy = grid_start_y + row * gap_y
            sel = (i == self.g.menu_cursor)
    
            self.g._menu_rects.append(pygame.Rect(cx - orb_r, cy - orb_r, orb_r * 2, orb_r * 2))
    
            # Glow if selected
            if sel:
                glow_r = orb_r + int(5 * math.sin(t * 5))
                surf.blit(self._glow_disc(glow_r * 2, C.C_CYAN, 35),
                          (cx - glow_r * 2 + ox, cy - glow_r * 2 + oy))
    
            # Orb body
            orb_col = C.C_CYAN if sel else C.C_BORDER_LIGHT
            pygame.draw.circle(surf, (25, 25, 50), (cx + ox, cy + oy), orb_r)
            pygame.draw.circle(surf, orb_col, (cx + ox, cy + oy), orb_r, 2)
    
            # Icon inside (centered with pixel-perfect offset for ▶)
            icon_t = self._text(self.g.font_lg, orb_icons[i], orb_col)
            iw, ih = icon_t.get_size()
            if orb_icons[i] == "▶":
                icon_x = cx - iw // 2 + 2
            else:
                icon_x = cx - iw // 2
            surf.blit(icon_t, (icon_x + ox, cy - ih // 2 + oy))
    
            # Label below
            lbl = self._text(self.g.font_xxs, orb_labels[i],
                             C.C_WHITE if sel else C.C_DIM)
            surf.blit(lbl, (cx - lbl.get_width() // 2 + ox, cy + orb_r + 3 + oy))
    
        # ── Sound indicator (top-left, translucent) ──
        mute_txt = "Sonido: activo" if self.g.audio.enabled else "Sonido: mudo"
        mute_c = C.C_GREEN if self.g.audio.enabled else C.C_RED
        m_hint = self._text(self.g.font_xxs, f"M = {mute_txt}", mute_c)
        pad = 3
        chip_w = m_hint.get_width() + pad * 2
        chip_h = m_hint.get_height() + pad
        chip = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
        pygame.draw.rect(chip, (*C.C_BG_LIGHT, 150), chip.get_rect())
        pygame.draw.rect(chip, (*C.C_BORDER, 120), chip.get_rect(), 1)
        surf.blit(chip, (5 + ox, 5 + oy))
        surf.blit(m_hint, (5 + pad + ox, 5 + pad // 2 + oy))

        # ── Bottom hints ──
        hint = self._text(
            self.g.font_xxs,
            "← → ↑ ↓ Seleccionar  |  ENTER=Entrar  |  F11=Pantalla", C.C_DIM
        )
        surf.blit(hint, (mid_x - hint.get_width() // 2 + ox, H - 26 + oy))
    
    # ── Settings ───────────────────────────────────────────
    

    def _draw_credits(self, surf, ox, oy):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid_x = W // 2
        t = self.g.global_time
    
        # ── Luminous background orbs ──
        for i in range(4):
            gx = int(W * 0.15 + math.sin(t * 0.2 + i * 1.8) * W * 0.2)
            gy = int(H * 0.2 + math.cos(t * 0.25 + i * 2.3) * H * 0.2)
            gr = int(30 + 15 * math.sin(t * 0.4 + i))
            gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            alpha = int(20 + 12 * math.sin(t + i))
            cols = [C.C_CYAN, C.C_PURPLE, C.C_GREEN, C.C_GOLD]
            pygame.draw.circle(gs, (*cols[i], alpha), (gr, gr), gr)
            surf.blit(gs, (gx - gr + ox, gy - gr + oy))
    
        # ── Stars twinkling ──
        for i in range(12):
            sx = int((40 + i * 37) % W)
            sy = int((10 + i * 23) % H)
            sa = int(40 + 35 * math.sin(t * 3 + i * 1.1))
            ss = pygame.Surface((6, 6), pygame.SRCALPHA)
            star_col = random.choice([C.C_GOLD, C.C_CYAN, C.C_WHITE])
            pygame.draw.circle(ss, (*star_col, sa), (3, 3), 2)
            surf.blit(ss, (sx + ox, sy + oy))
    
        # ── Title ──
        title = self.g.font_lg.render("Créditos", True, C.C_GOLD)
        surf.blit(title, (mid_x - title.get_width() // 2 + ox, 8 + oy))
    
        # ── PC PLAYER jellyfish bouncing ping-pong ──
        jp_x = int(W * 0.5 + math.sin(t * 1.8) * (W * 0.35))
        jp_y = int(H * 0.5 + math.sin(t * 2.6) * (H * 0.3))
        octo = self.g.sprites.get_octopus(int(t * 3) % 8, win=False)
        octo_s = pygame.transform.scale(octo, (28, 32))
        surf.blit(octo_s, (jp_x - 14 + ox, jp_y - 16 + oy))
    
        # ── Content: clean text with small circle icons ──
        line_h = 14
        y = 78
    
        # OPTIMA with small circle icon
        pygame.draw.circle(surf, C.C_CYAN, (mid_x - 55 + ox, y + 5 + oy), 5)
        opt = self.g.font_sm.render("OPTIMA", True, C.C_CYAN)
        surf.blit(opt, (mid_x - 44 + ox, y - 1 + oy))
        y += line_h + 4
    
        # Project name
        proj = self.g.font_sm.render("PC Repair Challenge", True, C.C_WHITE)
        surf.blit(proj, (mid_x - proj.get_width() // 2 + ox, y + oy))
        y += line_h
    
        # Description
        sub = self.g.font_xxs.render("Juego educativo de reparación de PCs", True, C.C_SUBTITLE)
        surf.blit(sub, (mid_x - sub.get_width() // 2 + ox, y + oy))
        y += line_h + 8
    
        # GitHub with small circle icon
        pygame.draw.circle(surf, C.C_WHITE, (mid_x - 65 + ox, y + 5 + oy), 5)
        gh = self.g.font_xxs.render("github.com/Jabonsote", True, C.C_CYAN)
        surf.blit(gh, (mid_x - 54 + ox, y + oy))
        y += line_h + 2
    
        # Email with small circle icon
        pygame.draw.circle(surf, C.C_GREEN, (mid_x - 65 + ox, y + 5 + oy), 5)
        em = self.g.font_xxs.render("javier.ramirez@cicese.mx", True, C.C_GREEN)
        surf.blit(em, (mid_x - 54 + ox, y + oy))
        y += line_h + 6
    
        # Thanks with small circle icon
        pygame.draw.circle(surf, C.C_GOLD, (mid_x - 55 + ox, y + 5 + oy), 5)
        th = self.g.font_xxs.render("¡Gracias por jugar!", True, C.C_GOLD)
        surf.blit(th, (mid_x - 44 + ox, y + oy))
        y += line_h + 10
    
        # ── Logos centered and bigger ──
        if self.logos:
            logo_h = 24
            gap = 16
            n = len(self.logos)
            # Calculate total width
            sizes = []
            for img in self.logos:
                iw, ih = img.get_size()
                sc = logo_h / ih
                sizes.append(max(1, int(iw * sc)))
            total_w = sum(sizes) + gap * (n - 1)
            lx = mid_x - total_w // 2
    
            for i, img in enumerate(self.logos):
                nw = sizes[i]
                scaled = pygame.transform.smoothscale(img, (nw, logo_h))
                alpha = int(180 + 60 * math.sin(t * 1.2 + i * 1.5))
                alpha = max(100, min(255, alpha))
                scaled.set_alpha(alpha)
                by = y + int(math.sin(t * 1.5 + i * 2.0) * 2)
                surf.blit(scaled, (lx + ox, by + oy))
                lx += nw + gap
    
        # ── Right side animated dots ──
        dot_x = W - 10
        for i in range(6):
            dy = 20 + i * 12
            da = int(30 + 25 * math.sin(t * 2 + i * 0.8))
            ds = pygame.Surface((6, 6), pygame.SRCALPHA)
            dot_cols = [C.C_GOLD, C.C_CYAN, C.C_GREEN, C.C_PURPLE, C.C_ORANGE, C.C_WHITE]
            pygame.draw.circle(ds, (*dot_cols[i], da), (3, 3), 2)
            surf.blit(ds, (dot_x + ox, dy + oy))
    
        # ── Left side animated dots ──
        for i in range(6):
            dy = 20 + i * 12
            da = int(30 + 25 * math.sin(t * 1.8 + i * 1.2))
            ds = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(ds, (*C.C_PURPLE, da), (3, 3), 2)
            surf.blit(ds, (4 + ox, dy + oy))
    
        # ── Hint ──
        hint = self.g.font_xxs.render("ENTER / ESC = Volver", True, C.C_DIM)
        surf.blit(hint, (mid_x - hint.get_width() // 2 + ox, H - 26 + oy))
    
    # ── Level Select ───────────────────────────────────────
    

    def _draw_settings(self, surf, ox, oy):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid_x = W // 2
        t = self.g.global_time
    
        # ── Background luminous orbs ──
        for i in range(3):
            gx = int(W * 0.2 + math.sin(t * 0.15 + i * 2.5) * W * 0.25)
            gy = int(H * 0.3 + math.cos(t * 0.18 + i * 1.9) * H * 0.25)
            gr = int(35 + 20 * math.sin(t * 0.3 + i))
            gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            alpha = int(18 + 10 * math.sin(t * 0.5 + i))
            cols = [C.C_PURPLE, C.C_CYAN, C.C_GREEN]
            pygame.draw.circle(gs, (*cols[i], alpha), (gr, gr), gr)
            surf.blit(gs, (gx - gr + ox, gy - gr + oy))
    
        # ── Title ──
        t_title = self.g.font_lg.render("Configuración", True, C.C_TITLE)
        surf.blit(t_title, (mid_x - t_title.get_width() // 2 + ox, 8 + oy))
    
        # ── 4 round config orbs in a horizontal row ──
        self.g._settings_rects.clear()
        orb_r = 20
        gap = 56
        start_x = mid_x - (3 * gap) // 2
        orb_y = 70
    
        icons = ["♪", "♫", "⚡", "◉"]
        labels = ["Música", "Efectos", "Dificultad", "Daltonismo"]
    
        for i in range(4):
            cx = start_x + i * gap
            sel = (i == self.g.settings_cursor)
    
            # Glow if selected
            if sel:
                glow_r = orb_r + int(5 * math.sin(t * 5))
                glow_s = pygame.Surface((glow_r * 4, glow_r * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_s, (*C.C_CYAN, 35), (glow_r * 2, glow_r * 2), glow_r * 2)
                surf.blit(glow_s, (cx - glow_r * 2 + ox, orb_y - glow_r * 2 + oy))
    
            # Dark circle body
            pygame.draw.circle(surf, (30, 30, 55), (cx + ox, orb_y + oy), orb_r)
            # Colored border
            orb_col = C.C_CYAN if sel else C.C_BORDER_LIGHT
            pygame.draw.circle(surf, orb_col, (cx + ox, orb_y + oy), orb_r, 2)
    
            # Icon inside (centered)
            icon_t = self.g.font_lg.render(icons[i], True, orb_col)
            icon_rect = icon_t.get_rect(center=(cx + ox, orb_y + oy))
            surf.blit(icon_t, icon_rect.topleft)
    
            # Label below
            lbl = self.g.font_xxs.render(labels[i], True, C.C_WHITE if sel else C.C_DIM)
            surf.blit(lbl, (cx - lbl.get_width() // 2 + ox, orb_y + orb_r + 4 + oy))
    
            # Value below label
            if i == 0:
                val = f"{int(self.g.music_volume * 100)}%"
                col = C.C_GREEN if self.g.music_volume > 0.3 else C.C_YELLOW
                if self.g.music_volume <= 0.05: col = C.C_RED_DIM
                # Volume bar
                bar_w = 36
                bar_h = 3
                bar_x = cx - bar_w // 2
                bar_y = orb_y + orb_r + 16
                pygame.draw.rect(surf, (40, 40, 60), (bar_x + ox, bar_y + oy, bar_w, bar_h))
                fill_w = int(bar_w * self.g.music_volume)
                if fill_w > 0:
                    pygame.draw.rect(surf, col, (bar_x + ox, bar_y + oy, fill_w, bar_h))
                # Knob
                knob_x = bar_x + fill_w
                pygame.draw.circle(surf, C.C_WHITE, (knob_x + ox, bar_y + bar_h // 2 + oy), 3)
            elif i == 1:
                val = f"{int(self.g.sfx_volume * 100)}%"
                col = C.C_GREEN if self.g.sfx_volume > 0.3 else C.C_YELLOW
                if self.g.sfx_volume <= 0.05: col = C.C_RED_DIM
                # Volume bar
                bar_w = 36
                bar_h = 3
                bar_x = cx - bar_w // 2
                bar_y = orb_y + orb_r + 16
                pygame.draw.rect(surf, (40, 40, 60), (bar_x + ox, bar_y + oy, bar_w, bar_h))
                fill_w = int(bar_w * self.g.sfx_volume)
                if fill_w > 0:
                    pygame.draw.rect(surf, col, (bar_x + ox, bar_y + oy, fill_w, bar_h))
                knob_x = bar_x + fill_w
                pygame.draw.circle(surf, C.C_WHITE, (knob_x + ox, bar_y + bar_h // 2 + oy), 3)
            elif i == 2:
                val = self.g.difficulty_names[self.g.difficulty]
                col = [C.C_CYAN, C.C_GREEN, C.C_YELLOW, C.C_RED][
                    min(self.g.difficulty, len(C.DIFFICULTIES) - 1)]
            else:
                val = "ON" if self.g.colorblind_mode else "OFF"
                col = C.C_GREEN if self.g.colorblind_mode else C.C_RED
    
            val_t = self.g.font_xxs.render(val, True, col)
            if i in (0, 1):
                surf.blit(val_t, (cx - val_t.get_width() // 2 + ox, orb_y + orb_r + 22 + oy))
            else:
                surf.blit(val_t, (cx - val_t.get_width() // 2 + ox, orb_y + orb_r + 14 + oy))
    
            # Store rect for click detection
            self.g._settings_rects.append(pygame.Rect(cx - orb_r, orb_y - orb_r, orb_r * 2, orb_r * 2 + 26))
    
        # ── Colorblind indicator ──
        if self.g.colorblind_mode:
            cb_ind = self.g.font_xxs.render("Daltonismo activo", True, C.C_GREEN)
            surf.blit(cb_ind, (mid_x - cb_ind.get_width() // 2 + ox, 110 + oy))
    
        # ── Hint ──
        hint = self.g.font_xxs.render("← → Ajustar  ·  ↑ ↓ Seleccionar  ·  ESC=Volver", True, C.C_DIM)
        surf.blit(hint, (mid_x - hint.get_width() // 2 + ox, H - 26 + oy))
    
    # ── Credits ─────────────────────────────────────────────
    

    def _draw_level_select(self, surf, ox, oy):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid_x = W // 2
    
        t = self.g.font_lg.render("Seleccionar nivel", True, C.C_TITLE)
        surf.blit(t, (mid_x - t.get_width() // 2 + ox, 20 + oy))
    
        uw = 140
        pygame.draw.line(surf, C.C_BORDER_LIGHT,
                         (mid_x - uw // 2, 42), (mid_x + uw // 2, 42), 1)
    
        btn_w = 280
        btn_h = 24
        btn_start_y = 55
    
        for i, name in enumerate(self.g.level_names):
            bx = mid_x - btn_w // 2
            by = btn_start_y + i * (btn_h + 6)
            r = pygame.Rect(bx, by, btn_w, btn_h)
            self.g._level_rects.append(r)
            sel = (i == self.g.level_cursor)
            lvl = C.LEVELS[i]
    
            if sel:
                glow_a = int(35 + 25 * math.sin(self.g.global_time * 5))
                gs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
                gs.fill((C.C_CYAN[0], C.C_CYAN[1], C.C_CYAN[2], glow_a))
                surf.blit(gs, (bx, by))
                pygame.draw.rect(surf, C.C_CYAN, (bx, by, btn_w, btn_h), 1)
                txt = self.g.font_sm.render(f"> {name}", True, C.C_CYAN)
                info = self.g.font_xxs.render(
                    f"{lvl['computers']} PCs  |  {lvl['components']} partes",
                    True, C.C_WHITE,
                )
                surf.blit(txt, (bx + 8, by + 1))
                surf.blit(info, (bx + btn_w - info.get_width() - 8, by + 4))
            else:
                bg_a = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
                bg_a.fill((60, 60, 100, 40))
                surf.blit(bg_a, (bx, by))
                pygame.draw.rect(surf, C.C_BORDER, (bx, by, btn_w, btn_h), 1)
                txt = self.g.font_sm.render(name, True, C.C_SUBTITLE)
                info = self.g.font_xxs.render(
                    f"{lvl['computers']}x{lvl['components']}", True, C.C_DIM
                )
                surf.blit(txt, (bx + 8, by + 3))
                surf.blit(info, (bx + btn_w - info.get_width() - 8, by + 5))
    
        hint = self.g.font_xxs.render(
            "↑/↓ o clic  |  ENTER=Seleccionar  ESC=Atrás", True, C.C_DIM
        )
        surf.blit(hint, (mid_x - hint.get_width() // 2 + ox, H - 26 + oy))
    
    # ── Game screen ────────────────────────────────────────
    

    def _draw_game(self, surf, ox, oy):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid = W // 2
    
        # ── Luminous background glow ──
        glow_t = self.g.global_time
        for i in range(3):
            gx = int(W * 0.2 + math.sin(glow_t * 0.3 + i * 2.1) * W * 0.15)
            gy = int(H * 0.3 + math.cos(glow_t * 0.4 + i * 1.7) * H * 0.15)
            gr = int(40 + 20 * math.sin(glow_t * 0.5 + i))
            alpha = 15 + 8 * math.sin(glow_t + i)
            glow_col = [C.C_CYAN, C.C_PURPLE, C.C_GREEN][i]
            surf.blit(self._glow_disc(gr, glow_col, alpha), (gx - gr + ox, gy - gr + oy))

        # ── Floating particles (bright) ──
        for i in range(5):
            px = int((W * 0.1 + (i * 97) % W + math.sin(glow_t * 0.2 + i) * 30) % W)
            py = int((H * 0.1 + (i * 67) % H + math.cos(glow_t * 0.25 + i) * 20) % H)
            a = 30 + 20 * math.sin(glow_t * 2 + i * 1.3)
            surf.blit(self._alpha_rect(4, 4, (200, 220, 255, a)), (px + ox, py + oy))

        # Onda central: antes 185 set_at por frame, ahora una franja cacheada.
        surf.blit(self._divider_strip(int(glow_t * 1.5) % 24), (mid + ox - 1, 10 + oy))

    
        self._draw_player_zone_hint(surf, ox, oy)
        self._draw_ai_panel(surf, ox, oy)
        self._draw_player_panel(surf, ox, oy)
        self._draw_scoreboard(surf, ox, oy)
        self._draw_component_tray(surf, ox, oy)
        self._draw_undo_button(surf, ox, oy)
        self._draw_bottom_bar(surf, ox, oy)
        self._draw_level_info(surf, ox, oy)
    

    def _draw_player_zone_hint(self, surf, ox, oy):
        """En el nivel 1, remarca claramente el área donde el jugador coloca sus piezas."""
        if (self.g.current_level == 0 and self.g.problem
                and self.g.state in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING)
                and len(self.g.used_components) < self.g.problem.num_components):
            W = C.LOGICAL_W
            mid = W // 2
            # Zona derecha (JUGADOR) con fondo destellante
            pulse = 0.5 + 0.5 * math.sin(self.g.global_time * 5)
            zone = pygame.Surface((mid, 110), pygame.SRCALPHA)
            a = int(30 + 25 * pulse)
            zone.fill((255, 215, 90, a))
            surf.blit(zone, (mid + ox, 2 + oy))
            pygame.draw.rect(surf, (*C.C_GOLD, int(160 + 90 * pulse)),
                             (mid + ox, 2 + oy, mid, 110), 2)
    
            # Etiqueta guía con flecha rebotando hacia la zona
            txt = self.g.font_sm.render("Coloca aquí tus piezas", True, C.C_GOLD)
            arrow = self.g.font_md.render("▼", True, C.C_GOLD)
            by = int(112 + 6 * math.sin(self.g.global_time * 4))
            # Flecha apuntando hacia abajo por encima de la zona, a la derecha
            ax = W - 90
            surf.blit(txt, (ax - txt.get_width() // 2 + ox, 108 + oy))
            surf.blit(arrow, (ax - arrow.get_width() // 2 + ox, by + oy))
    

    def _draw_ai_panel(self, surf, ox, oy):
        W = C.LOGICAL_W
        mid = W // 2
        # ── Label ────────────────────────────────────────
        lbl = self._text(self.g.font_sm, "PC PLAYER", C.C_SCORE_AI)
        surf.blit(lbl, (10 + ox, 2 + oy))
        sub = self._text(self.g.font_xxs, "Algoritmo genético", C.C_ORANGE)
        surf.blit(sub, (10 + ox, 16 + oy))
    
        # ── Character + gears ────────────────────────────
        octo = self.g.sprites.get_octopus(self.g.char_frame, win=False)
        surf.blit(octo, (8 + ox, 24 + oy))
        g1 = self.g.sprites.get_gear(self.g.gear_frame)
        g2 = self.g.sprites.get_gear(self.g.gear_frame + 3)
        surf.blit(g1, (30 + ox, 36 + oy))
        surf.blit(g2, (44 + ox, 42 + oy))
    
        # ── Gen counter (next to gears) ──────────────────
        if self.g.ai_ga and self.g.state not in (State.MENU, State.LEVEL_SELECT, State.TUTORIAL):
            total = max(1, self.g.ai_total_steps)
            gen = min(self.g.ai_ga.generation, self.g.ai_steps_done, total)
            gen_t = self._text(
                self.g.font_xxs,
                f"Gen: {gen}/{total}",
                C.C_SUBTITLE,
            )
            surf.blit(gen_t, (60 + ox, 38 + oy))
    
            # ── Fitness bar ──────────────────────────────
            if self.g.ai_ga.history:
                val = min(self.g.ai_ga.history[-1], 100)
                bar_x, bar_y, bar_w, bar_h = 10 + ox, 52 + oy, 90, 6
                pygame.draw.rect(surf, (40, 40, 55), (bar_x, bar_y, bar_w, bar_h))
                fw = int(bar_w * val / 100)
                if fw > 0:
                    pygame.draw.rect(surf, C.C_ORANGE, (bar_x, bar_y, fw, bar_h))
                    shine = tuple(min(255, c + 50) for c in C.C_ORANGE)
                    pygame.draw.rect(surf, shine, (bar_x, bar_y, fw, 2))
                pygame.draw.rect(surf, C.C_BORDER, (bar_x, bar_y, bar_w, bar_h), 1)
                pct_t = self._text(self.g.font_xxs, f"{val:.0f}%", C.C_WHITE)
                surf.blit(pct_t, (bar_x + bar_w + 4, bar_y - 1))
    
        # ── AI computers ─────────────────────────────────
        if self.g.problem:
            n = self.g.problem.num_computers
            ai_area_w = mid - 10
            ai_spacing = min(30, ai_area_w // max(n, 1))
            ai_start_x = 10 + (ai_area_w - n * ai_spacing) // 2
            for ci in range(n):
                x = ai_start_x + ci * ai_spacing + ox
                y = 64 + oy
                req = self.g.problem.requirements[ci]
                repaired = self.g.ai_repair_pct[ci] >= 100
                init_health = 100 - req
                state = "repaired" if repaired else ("damaged" if self.g.ai_repair_pct[ci] <= init_health else "repairing")
                sprite = self.g.sprites.get_computer(state, self.g.ai_repair_pct[ci], self.g.computer_frame)
                surf.blit(sprite, (x, y))
                req_c = C.C_GREEN if repaired else C.C_SUBTITLE
                req_t = self._text(self.g.font_xxs, f"{self.g.ai_repair_pct[ci]:.0f}%", req_c)
                surf.blit(req_t, (x + 13 - req_t.get_width() // 2, y + 25))
                if self.g.colorblind_mode:
                    cb_sym = "✓" if repaired else "✗"
                    cb_c = C.C_GREEN if repaired else C.C_RED
                    cb_t = self._text(self.g.font_xxs, cb_sym, cb_c)
                    surf.blit(cb_t, (x + 26 + ox, y - 2 + oy))
    
        # ── Mensajes divertidos durante el turno de la IA ──
        if self.g.state == State.AI_TURN:
            quips = [
                "¡Ya casi te gano!",
                "Mi robot afina su plan...",
                "Casi, casi te alcanzo...",
                "¡Esto se pone parejo!",
                "No te confíes, técnico...",
                "Mis engranajes piensan rápido...",
            ]
            msg = quips[int(self.g.state_timer * 1.5) % len(quips)]
            s_t = self._text(self.g.font_xxs, msg, C.C_YELLOW)
            surf.blit(s_t, (10 + ox, 96 + oy))
    

    def _pc_slot(self, x, y):
        """Rect del 'socket' de pieza sobre el pedestal de la PC."""
        return pygame.Rect(x + 6, y + 15, 10, 10)


    def _mini_component(self, comp_idx):
        """Icono de pieza reducido a 10x10 (nearest, mismo criterio que la bandeja)."""
        return self._scale_cached(self.g.sprites.get_component(comp_idx, False, 0), 10, 10)



    def _draw_pc_slot(self, surf, x, y, comp_idx, highlight=False):
        """
        Marca qué PCs ya tienen pieza y cuáles siguen vacías.
        - Con pieza: el icono real de la pieza, en chiquito, sobre el pedestal.
        - Sin pieza: socket hueco punteado con '+' pulsante.
        El estado se lee por FORMA (icono vs '+'), no solo por color.
        `x`/`y` ya traen el offset del shake.
        """
        r = self._pc_slot(x, y)
        t = self.g.global_time

        if comp_idx is not None and comp_idx >= 0:
            # ── Pieza instalada ──
            border = C.C_GLOW_CYAN if highlight else C.C_BORDER_LIGHT
            surf.blit(self._alpha_rect(r.w, r.h, (0, 0, 0, 150)), (r.x, r.y))
            pygame.draw.rect(surf, border, r, 1)
            surf.blit(self._mini_component(comp_idx), (r.x, r.y))
        else:
            # ── Falta pieza: socket vacío con '+' ──
            edge = C.C_GLOW_YELLOW if highlight else C.C_GOLD
            surf.blit(self._socket_img(edge, int(t * 3) % 2 == 0), (r.x, r.y))




    def _draw_player_panel(self, surf, ox, oy):
        W = C.LOGICAL_W
        mid = W // 2

        # ── Label ────────────────────────────────────────
        surf.blit(self._text(self.g.font_sm, "Jugador", C.C_SCORE_PLAYER),
                  (mid + 10 + ox, 2 + oy))
    
        # ── Character ────────────────────────────────────
        tech = self.g.sprites.get_technician("blue", "brown", True, self.g.char_frame)
        surf.blit(tech, (mid + 10 + ox, 28 + oy))

    
        # ── Computers ────────────────────────────────────
        if self.g.problem:
            n = self.g.problem.num_computers
            comp_area_w = mid - 20
            comp_spacing = min(38, comp_area_w // max(n, 1))
            comp_start_x = mid + 10 + (comp_area_w - n * comp_spacing) // 2

            # Mapa inverso pc -> pieza colocada. Se reconstruye cada frame para
            # que deshacer (DEL) y reiniciar el nivel no dejen estado colgando.
            placed = {}
            for comp_i, cpu_i in enumerate(self.g.player_assignment):
                if cpu_i >= 0:
                    placed[cpu_i] = comp_i

            # Pieza recién colocada: la mini cae con un pequeño rebote.
            drop_comp, drop_cpu = -1, -1
            if self.g.used_components and self.g.state_timer < 0.4:
                drop_comp = self.g.used_components[-1]
                if drop_comp < len(self.g.player_assignment):
                    drop_cpu = self.g.player_assignment[drop_comp]

            for ci in range(self.g.problem.num_computers):
                x = comp_start_x + ci * comp_spacing + ox
                y = 64 + oy
                req = self.g.problem.requirements[ci]
                init_health = 100 - req
                repaired = self.g.player_repair_pct[ci] >= 100
                over = self.g.player_repair_pct[ci] > 100
                state = "repaired" if repaired else ("damaged" if self.g.player_repair_pct[ci] <= init_health else "repairing")
                if over:
                    state = "overrepaired"
                sprite = self.g.sprites.get_computer(state, self.g.player_repair_pct[ci], self.g.computer_frame)
    
                # ── Brillo animado en las PCs del jugador ──
                # Las que aún NO están reparadas brillan con pulso, para que
                # el jugador identifique al instante cuáles son suyas y qué
                # falta por reparar (distintas de las del robot).
                if not repaired:
                    pulse = 0.5 + 0.5 * math.sin(self.g.global_time * 4 + ci * 0.6)
                    glow_a = 70 + 70 * pulse
                    surf.blit(self._alpha_rect(30, 32, (*C.C_GLOW_YELLOW, glow_a)),
                              (x - 2, y - 2))
    
                surf.blit(sprite, (x, y))
                r = pygame.Rect(x, y, 26, 28)
                self.g._cpu_rects.append(r)


                # ── Socket de pieza: qué PC ya tiene pieza y cuál no ──
                sel_here = (self.g.state == State.SELECT_COMPUTER
                            and ci == self.g.selected_computer)
                hov_here = (self.g.dragging and self.g.state == State.DRAGGING
                            and ci == self.g.drag_hover_cpu)
                slot_comp = placed.get(ci, -1)
                if ci == drop_cpu:
                    # Mini pieza cayendo desde arriba del socket
                    sr = self._pc_slot(x, y)
                    p = min(1.0, self.g.state_timer / 0.28)
                    ease = p * p * (3 - 2 * p)
                    dy = int(-7 * (1 - ease))
                    chip = self._alpha_rect(sr.w, sr.h, (0, 0, 0, 150))
                    surf.blit(chip, (sr.x, sr.y + dy))
                    pygame.draw.rect(surf, C.C_GLOW_CYAN, (sr.x, sr.y + dy, sr.w, sr.h), 1)
                    mini = self._mini_component(slot_comp)
                    if p < 1.0:
                        mini = mini.copy()
                        mini.set_alpha(int(255 * ease))
                    surf.blit(mini, (sr.x, sr.y + dy))
                else:
                    self._draw_pc_slot(surf, x, y, slot_comp,
                                       highlight=(sel_here or hov_here))
    
                # ── Indicador bajo la PC ──────────────────
                if repaired:
                    total = self.g.player_repair_pct[ci]
                    badge_txt = f"{total:.0f}%"
                    badge_c = C.C_GREEN
                else:
                    health = self.g.player_repair_pct[ci]
                    badge_txt = f"{health:.0f}%"
                    badge_c = C.C_YELLOW
                b_t = self._text(self.g.font_xxs, badge_txt, badge_c)
                b_bg = self._alpha_rect(b_t.get_width() + 3, b_t.get_height() + 1,
                                        (0, 0, 0, 150))
                surf.blit(b_bg, (x + (26 - b_t.get_width()) // 2 - 2, y + 27))
                surf.blit(b_t, (x + (26 - b_t.get_width()) // 2 - 1, y + 28))
    
                # Colorblind symbol
                if self.g.colorblind_mode:
                    cb_sym = "✓" if repaired else "✗"
                    cb_c = C.C_GREEN if repaired else C.C_RED
                    cb_t = self._text(self.g.font_xxs, cb_sym, cb_c)
                    surf.blit(cb_t, (x + 26 - 4 + ox, y - 2 + oy))
    
                if self.g.state == State.SELECT_COMPUTER and ci == self.g.selected_computer:
                    pulse = int(self.g.global_time * 6) % 2
                    bc = C.C_GLOW_CYAN if pulse else C.C_WHITE
                    pygame.draw.rect(surf, bc, (x - 2, y - 2, 28, 30), 2)
                    surf.blit(self._text(self.g.font_xxs, "v", C.C_CYAN), (x + 10, y - 8))
    
                if self.g.dragging and self.g.state == State.DRAGGING and ci == self.g.drag_hover_cpu:
                    contrib = self.g.problem.contributions[self.g.drag_comp][ci]
                    cur = self.g.player_repair_pct[ci]
                    new_total = cur + contrib
                    ok = new_total >= 100
                    pulse_val = int(self.g.global_time * 8) % 2
                    bc = C.C_GLOW_GREEN if ok else C.C_GLOW_RED
                    if pulse_val:
                        bc = C.C_GLOW_YELLOW
                    pygame.draw.rect(surf, bc, (x - 2, y - 2, 28, 30), 2)
                    status = "+" if ok else "!"
                    surf.blit(self._text(self.g.font_xxs, status, bc), (x + 10, y - 8))
    
                # ── Vista previa del poder de la pieza por PC ──
                # Cuando hay un componente activo (seleccionado o arrastrado),
                # mostramos cuánto aportaría en ESTA computadora.
                active_comp = None
                if self.g.dragging and self.g.drag_comp >= 0:
                    # Al estar agarrando/arrastrando una pieza, mostrar su utilidad
                    # desde el primer momento (antes incluso del umbral de arrastre).
                    active_comp = self.g.drag_comp
                elif self.g.selected_component >= 0 and self.g.state in (
                    State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING):
                    active_comp = self.g.selected_component
    
                if active_comp is not None and self.g.problem and ci < self.g.problem.num_computers:
                    contrib = self.g.problem.contributions[active_comp][ci]
                    cur = self.g.player_repair_pct[ci]
                    # Tope visual a 100%
                    new_total = min(cur + contrib, 100)
                    will_repair = new_total >= 100 and not repaired

                    # Chip: SIEMPRE muestra cuánto aporta la pieza (+X%)
                    if not repaired:
                        pv_c = C.C_GREEN if will_repair else C.C_YELLOW
                        chip = self._text(self.g.font_xxs, f"+{contrib:.0f}%", pv_c)
                        chip_bg = self._alpha_rect(chip.get_width() + 4,
                                                   chip.get_height() + 2,
                                                   (10, 10, 20, 170))
                        surf.blit(chip_bg, (x - 3, y - 12))
                        surf.blit(chip, (x - 1, y - 11))

                    # Mini-barra: muestra cuánto se llenaría esta PC.
                    # Va DENTRO de la pantalla (debajo de la barra del sprite)
                    # para no chocar con el socket de pieza del pedestal.
                    if not repaired:
                        bw = 18
                        by = y + 11
                        pygame.draw.rect(surf, (40, 40, 55), (x + 2, by, bw, 3))
                        fill_pct = min(new_total / 100.0, 1.0)
                        if fill_pct > 0:
                            pygame.draw.rect(surf, pv_c, (x + 2, by, int(bw * fill_pct), 3))

                    # ── El socket NO se toca al seleccionar una pieza ──
                    # El socket solo refleja lo REAL: vacío o con su pieza.
                    # La ayuda de "cuánto aporta" va en el chip +X% y en la
                    # mini-barra, así el niño no cree que ya están ocupadas.
                    pass


    

    def _draw_scoreboard(self, surf, ox, oy):
        W = C.LOGICAL_W
        mid = W // 2
        bar_y = 114
        bar_h = 30
    
        # ── Bar background ───────────────────────────────
        pygame.draw.rect(surf, C.C_PANEL_BOT, (0, bar_y, W, bar_h))
        pygame.draw.line(surf, C.C_BORDER, (0, bar_y), (W, bar_y), 1)
        pygame.draw.line(surf, C.C_BORDER, (0, bar_y + bar_h - 1), (W, bar_y + bar_h - 1), 1)
    
        ai_v = self.g.ai_score_display.value
        p_v = self.g.player_score_display.value
    
        # ── Left side: label + score on one line ────────
        ai_label = self._text(self.g.font_xxs, "PC PLAYER", C.C_SCORE_AI)
        ai_t = self._text(self.g.font_sm, f"{ai_v:.0f}", C.C_SCORE_AI)
        ai_x = mid - 140 + ox
        ai_cy = bar_y + (bar_h - max(ai_label.get_height(), ai_t.get_height())) // 2
        surf.blit(ai_label, (ai_x, ai_cy))
        surf.blit(ai_t, (ai_x + ai_label.get_width() + 6, ai_cy))
    
        # ── Center: VS badge ─────────────────────────────
        vs_badge = pygame.Surface((30, 18))
        vs_badge.fill(C.C_BORDER)
        pygame.draw.rect(vs_badge, C.C_BORDER_LIGHT, (0, 0, 30, 18), 1)
        surf.blit(vs_badge, (mid - 15, bar_y + 6))
        vs = self._text(self.g.font_xs, "VS", C.C_BLACK)
        surf.blit(vs, (mid - vs.get_width() // 2, bar_y + 8))
    
        # ── Right side: label + score on one line ───────
        p_label = self._text(self.g.font_xxs, "Jugador", C.C_SCORE_PLAYER)
        p_t = self._text(self.g.font_sm, f"{p_v:.0f}", C.C_SCORE_PLAYER)
        p_x = mid + 78 + ox
        p_cy = bar_y + (bar_h - max(p_label.get_height(), p_t.get_height())) // 2
        surf.blit(p_label, (p_x, p_cy))
        surf.blit(p_t, (p_x + p_label.get_width() + 6, p_cy))
    
        # ── Timer next to player score ──
        if self.g.level_time_limit > 0 and self.g.problem:
            left = max(0.0, self.g.time_left)
            frac = left / self.g.level_time_limit
            if frac > 0.5:
                col = C.C_GREEN
            elif frac > 0.25:
                col = C.C_YELLOW
            else:
                col = C.C_RED
    
            secs = int(math.ceil(left))
            tcol = col
            if frac <= 0.2 and int(self.g.global_time * 4) % 2 == 0:
                tcol = C.C_WHITE
            tx = p_x + p_label.get_width() + p_t.get_width() + 14
            # Clock icon
            cx_c, cy_c, r = tx + 5, bar_y + bar_h // 2, 4
            pygame.draw.circle(surf, tcol, (cx_c, cy_c), r, 1)
            ang = -math.pi / 2 + (1 - frac) * 2 * math.pi
            hx = cx_c + int((r - 1) * math.cos(ang))
            hy = cy_c + int((r - 1) * math.sin(ang))
            pygame.draw.line(surf, tcol, (cx_c, cy_c), (hx, hy), 1)
            # Seconds text
            st = self._text(self.g.font_xxs, f"{secs}s", tcol)
            surf.blit(st, (tx + 14, bar_y + (bar_h - st.get_height()) // 2))
    

    def _draw_component_tray(self, surf, ox, oy):
        if not self.g.problem:
            return
        W = C.LOGICAL_W
        tray_y = 146 + oy
    
        n = self.g.problem.num_components
        if n <= 4:
            comp_size, gap = 40, 12
        elif n <= 6:
            comp_size, gap = 36, 10
        else:
            comp_size, gap = 32, 8
    
        block_w = n * comp_size + (n - 1) * gap
        start_x = (W - block_w) // 2
    
        tray_h = comp_size + 28
        pygame.draw.rect(surf, C.C_PANEL_BOT, (0, tray_y, W, tray_h))
        pygame.draw.line(surf, C.C_BORDER, (0, tray_y), (W, tray_y), 1)
    
        for ci in range(n):
            x = round(start_x + ci * (comp_size + gap)) + ox
            y = tray_y + 24 + oy
            used = ci in self.g.used_components
            is_dragged = (ci == self.g.drag_comp and self.g.dragging and self.g.drag_started_move)
    
            r = pygame.Rect(x, y, comp_size, comp_size)
            self.g._comp_rects.append(r)
    
            if used:
                pygame.draw.rect(surf, (28, 28, 38), (x, y, comp_size, comp_size))
                pygame.draw.rect(surf, (50, 50, 60), (x, y, comp_size, comp_size), 1)
                txt = self._text(self.g.font_xxs, "X", C.C_RED)
                surf.blit(txt, (x + comp_size // 2 - 3, y + comp_size // 2 - 5))
            elif is_dragged:
                pygame.draw.rect(surf, (40, 40, 60), (x, y, comp_size, comp_size))
                pygame.draw.rect(surf, C.C_DIM, (x, y, comp_size, comp_size), 1)
                dots = self._text(self.g.font_xxs, "...", C.C_DIM)
                surf.blit(dots, (x + comp_size // 2 - 6, y + comp_size // 2 - 4))
            else:
                sel = (ci == self.g.selected_component)
                if sel and self.g.state == State.SELECT_COMPUTER:
                    glow = GlowRect(x - 1, y - 1, comp_size + 2, comp_size + 2, C.C_GLOW_YELLOW, 6.0)
                    glow.update(self.g.global_time)
                    glow.draw(surf)
                elif sel:
                    glow = GlowRect(x - 1, y - 1, comp_size + 2, comp_size + 2, C.C_GLOW_CYAN, 4.0)
                    glow.update(self.g.global_time)
                    glow.draw(surf)
                else:
                    pygame.draw.rect(surf, C.C_BG_LIGHT, (x, y, comp_size, comp_size))
                    pygame.draw.rect(surf, C.C_BORDER, (x, y, comp_size, comp_size), 1)
    
                icon = self.g.sprites.get_component(ci, sel, self.g.computer_frame)
                icon_s = self._scale_cached(icon, comp_size - 12, comp_size - 12)
                phase = ci * 0.9 + self.g.global_time * 2.2
                bob = int(math.sin(phase * 2) * 1)
                if sel:
                    bob += int(math.sin(self.g.global_time * 6) * 1)
                ix = x + 6 + int(math.sin(phase) * 1)
                iy = y + 6 + bob
                surf.blit(icon_s, (ix, iy))
    
            # Colorblind: ▲ on selected component
            if self.g.colorblind_mode and sel and not used:
                cb_arrow = self._text(self.g.font_xxs, "▲", C.C_CYAN)
                surf.blit(cb_arrow, (x + comp_size // 2 - cb_arrow.get_width() // 2, y - 8 + oy))
    
            # ── Nombre centrado debajo de la pieza ──
            name = C.C_COMP_NAMES[ci % len(C.C_COMP_NAMES)]
            label_color = C.C_SUBTITLE if not used else C.C_DIM
            font_n = self.g.font_xxs
            max_w = comp_size + 2
            short_name = name
            if font_n.size(short_name)[0] > max_w:
                short_name = name[:5] + "."
            ln_t = self._text(font_n, short_name, label_color)
            surf.blit(
                ln_t,
                (x + comp_size // 2 - ln_t.get_width() // 2,
                 y + comp_size + 1),
            )
    

    def _draw_undo_button(self, surf, ox, oy):
        """Boton de deshacer, para no depender del teclado.

        Se dibuja en la franja libre entre la bandeja de piezas y la barra
        inferior. Queda atenuado cuando no hay nada que deshacer, y su estado
        no sejnala solo con color: lleva flecha y texto.
        """
        g = self.g
        if g.state not in (State.PLAYING, State.SELECT_COMPUTER):
            g._undo_rect = None
            return

        W = C.LOGICAL_W
        bw, bh = 92, 22
        bx, by = W - bw - 8, 222
        rect = pygame.Rect(bx + ox, by + oy, bw, bh)
        g._undo_rect = rect

        active = bool(g.used_components)
        hover = active and rect.collidepoint(g.mouse_pos)

        if not active:
            fill, border, fg = C.C_BG_LIGHT, C.C_BORDER, C.C_DIM
        elif hover:
            fill, border, fg = C.C_PANEL_BOT, C.C_CYAN, C.C_WHITE
        else:
            fill, border, fg = C.C_PANEL_BOT, C.C_CYAN, C.C_CYAN

        pygame.draw.rect(surf, fill, rect)
        pygame.draw.rect(surf, border, rect, 1)

        icon = self._text(g.font_xs, "↶", fg)
        label = self._text(g.font_xxs, "Deshacer", fg)
        iy = rect.centery - icon.get_height() // 2
        surf.blit(icon, (rect.x + 8, iy))
        surf.blit(label, (rect.x + 8 + icon.get_width() + 4,
                          rect.centery - label.get_height() // 2))

    def _draw_bottom_bar(self, surf, ox, oy):
        W = C.LOGICAL_W
        bar_y = C.LOGICAL_H - 14
    
        if self.g.state == State.PLAYING:
            if self.g.selected_component >= 0:
                comp = self.g.selected_component
                name = C.C_COMP_NAMES[comp % len(C.C_COMP_NAMES)]
                hint = self.g.font_xxs.render(
                    f"Pieza: {name}  |  ENTER/Elegir PC  |  Arrastrar  |  DEL=Deshacer",
                    True, C.C_CYAN,
                )
            else:
                hint = self.g.font_xxs.render(
                    "ENTER/Clic=Seleccionar pieza  |  Arrastrar=Asignar rápido", True, C.C_DIM
                )
            surf.blit(hint, (6 + ox, bar_y + oy))
    
        elif self.g.state == State.SELECT_COMPUTER:
            cpu = self.g.selected_computer
            cur = self.g.player_repair_pct[cpu]
            comp = self.g.selected_component
            contrib = self.g.problem.contributions[comp][cpu]
            new_total = cur + contrib
            ok = new_total >= 100
            status = "¡Repara!" if ok else "Insuficiente"
            sc = C.C_GREEN if ok else C.C_RED
            hint = self.g.font_mini.render(
                f"PC#{cpu + 1}: {cur:.0f}+{contrib}={new_total:.0f}%  {status}  |  ENTER=OK  ESC=Cancelar",
                True, sc,
            )
            surf.blit(hint, (6 + ox, bar_y + oy))
    
        elif self.g.state == State.DRAGGING:
            if self.g.drag_hover_cpu >= 0:
                cpu = self.g.drag_hover_cpu
                cur = self.g.player_repair_pct[cpu]
                comp = self.g.drag_comp
                contrib = self.g.problem.contributions[comp][cpu]
                new_total = cur + contrib
                ok = new_total >= 100
                status = "Soltar para reparar" if ok else "Soltar (no alcanza)"
                sc = C.C_GREEN if ok else C.C_RED
            else:
                comp = self.g.drag_comp
                status = "Suelta en una computadora para asignar"
                sc = C.C_DIM
            hint = self.g.font_mini.render(
                f"Arrastrando: {C.C_COMP_NAMES[comp % len(C.C_COMP_NAMES)]}  |  {status}",
                True, sc,
            )
            surf.blit(hint, (6 + ox, bar_y + oy))
    
        elif self.g.state == State.AI_TURN:
            hint = self.g.font_mini.render(
                "El algoritmo genético está calculando... ¡observa los engranajes!", True, C.C_ORANGE
            )
            surf.blit(hint, (6 + ox, bar_y + oy))
    

    def _draw_level_info(self, surf, ox, oy):
        if self.g.problem and self.g.state in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING):
            W = C.LOGICAL_W
            lvl = C.LEVELS[self.g.current_level]
    
            # Level name at top-RIGHT (texto pequeño para no invadir el HUD)
            name_t = self._text(self.g.font_xxs, lvl["name"], C.C_TITLE)
            surf.blit(name_t, (W - name_t.get_width() - 6 + ox, 2 + oy))
    
            # Remaining parts (under the badge on the right)
            rem = self.g.problem.num_components - len(self.g.used_components)
            rem_t = self._text(self.g.font_xxs,
                               f"Partes: {rem}/{self.g.problem.num_components}", C.C_DIM)
            surf.blit(rem_t, (W - rem_t.get_width() - 6 + ox, 16 + oy))
    
            if self.g.player_score:
                met = self.g.player_score.requirement_met
                tot = self.g.problem.num_computers
                mc = C.C_GREEN if met == tot else C.C_YELLOW
                met_t = self._text(self.g.font_xxs, f"Reparadas: {met}/{tot}", mc)
                surf.blit(met_t, (W - met_t.get_width() - 6 + ox, 28 + oy))

            # PCs a las que todavía les falta pieza (socket vacío en el tablero)
            assigned = sum(1 for c in self.g.player_assignment if c >= 0)
            missing = self.g.problem.num_computers - assigned
            if missing > 0:
                miss_t = self._text(self.g.font_xxs, f"Sin pieza: {missing}", C.C_GOLD)
            else:
                miss_t = self._text(self.g.font_xxs, "Todas con pieza", C.C_GREEN)
            surf.blit(miss_t, (W - miss_t.get_width() - 6 + ox, 40 + oy))

    

    def _draw_level_transition(self, surf, ox, oy):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid_x = W // 2
        t = self.g.level_transition_timer
        # Fade: 2.5s total, 0.45s de entrada y 0.45s de salida con smoothstep
        if t > 2.05:
            u = 2.5 - t
        elif t < 0.45:
            u = t
        else:
            u = 0.45
        p = max(0.0, min(1.0, u / 0.45))
        ease = p * p * (3 - 2 * p)          # smoothstep: entra y sale sin tirón
        alpha = int(255 * ease)

        if alpha > 2:
            self._fill_screen(surf, (10, 10, 30, alpha * 0.85))

        num_a = min(255, alpha)
        if num_a > 2:
            num_txt = self._text(self.g.font_title,
                                 f"Nivel {self.g.current_level + 1}", C.C_TITLE)
            num_s = num_txt.copy()
            num_s.set_alpha(num_a)
            surf.blit(num_s, (mid_x - num_txt.get_width() // 2 + ox, H // 2 - 30 + oy))

            name_txt = self._text(self.g.font_lg,
                                  self.g.level_transition_name, C.C_WHITE)
            name_s = name_txt.copy()
            name_s.set_alpha(num_a)
            surf.blit(name_s, (mid_x - name_txt.get_width() // 2 + ox, H // 2 + 2 + oy))
    

    def draw_drag_ghost(self, surf):
        if self.g.drag_comp < 0:
            return
        mx, my = self.g.drag_mouse

        icon = self.g.sprites.get_component(self.g.drag_comp, True, self.g.computer_frame)
        ghost = self._scale_cached(icon, 30, 30).copy()
        ghost.set_alpha(180)
        surf.blit(ghost, (mx - 15, my - 15))

        glow_a = (int(40 + 20 * math.sin(self.g.global_time * 10)) // 8) * 8
        surf.blit(self._glow_frame(glow_a), (mx - 18, my - 18))


        if self.g.drag_comp < len(self.g._comp_rects):
            orig = self.g._comp_rects[self.g.drag_comp]
            # Línea directa (mezcla precalculada en vez de un overlay alfa
            # de pantalla completa por frame).
            pygame.draw.line(surf, C.C_CYAN_DIM,
                             (orig.centerx, orig.centery), (mx, my), 1)

    

    def _draw_result_overlay(self, surf):
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid = W // 2
    
        self._fill_screen(surf, (0, 0, 0, 220))
    
        # Anillos expansivos de la animación de resultado
        self.g.result_anim.draw_rings(surf, (mid, 60))
    
        # ── Banner (GANASTE / EMPATE / PC PLAYER GANA) ────
        bounce = self.g.result_anim.banner_offset()
        cy = 4 + bounce
        pulse = 0.8 + 0.2 * math.sin(self.g.global_time * 4)
        rc = tuple(min(255, int(c * pulse)) for c in self.g.result_color)
        rt = self.g.font_md.render(self.g.result_text, True, rc)
        surf.blit(rt, (mid - rt.get_width() // 2, cy))
        cy += 22

        # Por que gano o perdio (llego antes, misma solucion, etc.)
        if self.g.result_reason:
            rr = self.g.font_mini.render(self.g.result_reason, True, C.C_SUBTITLE)
            surf.blit(rr, (mid - rr.get_width() // 2, cy))
            cy += 12
    
        # ── Estrellas conseguidas (solo las estrellas) ─────
        self.g.result_anim.draw_stars(surf, cy, size=11)
        cy += 30
    
        p_sc = self.g.player_score.score if self.g.player_score else 0
        ai_sc = self.g.ai_solution.score if self.g.ai_solution else 0
    
        # ── Tabla de puntaje: TÚ vs PC PLAYER, bien separada ──
        row_y = cy
        col_gap = 150
        col_left = mid - col_gap
        col_right = mid + 20
    
        # Encabezado de columnas (PC PLAYER izquierda, TÚ derecha)
        h_a = self.g.font_xs.render("PC PLAYER", True, C.C_SCORE_AI)
        h_p = self.g.font_xs.render("Tú", True, C.C_SCORE_PLAYER)
        surf.blit(h_a, (col_left, row_y))
        surf.blit(h_p, (col_right, row_y))
        row_y += 15
    
        # Puntaje destacado
        a_big = self.g.font_sm.render(f"{ai_sc:.0f}", True, C.C_SCORE_AI)
        p_big = self.g.font_sm.render(f"{p_sc:.0f}", True, C.C_SCORE_PLAYER)
        surf.blit(a_big, (col_left, row_y - 3))
        surf.blit(p_big, (col_right, row_y - 3))
        row_y += 17
    
        pygame.draw.line(surf, C.C_BORDER,
                         (col_left, row_y - 5), (col_right + 130, row_y - 5), 1)
    
        # Métricas comparadas: cada columna muestra su propio "Campo: valor"
        if self.g.player_score and self.g.ai_solution:
            p_met = self.g.player_score.requirement_met
            a_met = self.g.ai_solution.requirement_met
            p_eff = self.g.player_score.efficiency * 100
            a_eff = self.g.ai_solution.efficiency * 100
            p_was = self.g.player_score.waste * 100
            a_was = self.g.ai_solution.waste * 100
    
            fields = [
                ("Reparadas", f"{p_met}/{self.g.problem.num_computers}",
                              f"{a_met}/{self.g.problem.num_computers}"),
                ("Eficiencia", f"{p_eff:.0f}%", f"{a_eff:.0f}%"),
                ("Desperdicio", f"{p_was:.0f}%", f"{a_was:.0f}%"),
            ]
    
            def col_text(label, p_val, a_val):
                nonlocal row_y
                p_line = self.g.font_mini.render(f"{label}: {p_val}", True, C.C_SCORE_PLAYER)
                a_line = self.g.font_mini.render(f"{label}: {a_val}", True, C.C_SCORE_AI)
                # PC Player a la izquierda, Jugador a la derecha
                surf.blit(a_line, (col_left - 2, row_y))
                surf.blit(p_line, (col_right - 2, row_y))
                row_y += 12
    
            for label, pv, av in fields:
                col_text(label, pv, av)
    
        # ── Botones de acción ─────────────────────────────
        opts = self.g._result_options()
        btn_w = 200
        btn_h = 22
        gap = 8
        n = len(opts)
        total_h = n * btn_h + (n - 1) * gap
        btn_start_y = H - total_h - 14
        if self.g.result_cursor >= n:
            self.g.result_cursor = 0
    
        for i, label in enumerate(opts):
            bx = mid - btn_w // 2
            by = btn_start_y + i * (btn_h + gap)
            r = pygame.Rect(bx, by, btn_w, btn_h)
            self.g._result_rects.append(r)
            sel = (i == self.g.result_cursor)
    
            if sel:
                glow_a = int(35 + 25 * math.sin(self.g.global_time * 5))
                gs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
                gs.fill((C.C_CYAN[0], C.C_CYAN[1], C.C_CYAN[2], glow_a))
                surf.blit(gs, (bx, by))
                pygame.draw.rect(surf, C.C_CYAN, (bx, by, btn_w, btn_h), 1)
                txt_c = C.C_WHITE
            else:
                pygame.draw.rect(surf, (60, 60, 100), (bx, by, btn_w, btn_h))
                pygame.draw.rect(surf, C.C_BORDER, (bx, by, btn_w, btn_h), 1)
                txt_c = C.C_SUBTITLE
    
            txt = self.g.font_xs.render(label, True, txt_c)
            surf.blit(txt, (mid - txt.get_width() // 2, by + (btn_h - txt.get_height()) // 2))
    
        # Hint compacto JUSTO encima de los botones (sin superponerse)
        hint = self.g.font_mini.render("↑/↓ y ENTER, o clic", True, C.C_DIM)
        surf.blit(hint, (mid - hint.get_width() // 2, btn_start_y - 12))
    
        # ── Animación de comparación: piezas asignadas IA vs Jugador ──
        if self.g.state_timer > 1.0:
            self._draw_result_comparison(surf)
    
    

    def _draw_result_comparison(self, surf):
        """Muestra visualmente las piezas asignadas por IA vs Jugador, lado a lado."""
        W, H = C.LOGICAL_W, C.LOGICAL_H
        mid = W // 2
        t = self.g.state_timer - 1.0
        n = self.g.problem.num_computers
    
        # Zona de comparación: parte inferior de la pantalla
        zone_y = 100
        zone_h = 58
        zone = pygame.Surface((W, zone_h), pygame.SRCALPHA)
        zone.fill((10, 10, 25, 210))
        surf.blit(zone, (0, zone_y))
    
        # Layout: 2 columnas (IA izquierda, Jugador derecha)
        col_w = W // 2 - 10
        col_x = [5, mid + 5]
        headers = ["PC PLAYER", "Tú"]
        colors = [C.C_SCORE_AI, C.C_SCORE_PLAYER]
        assignments = [self.g.ai_solution.assignment if self.g.ai_solution else [],
                       self.g.player_assignment]
    
        for side in range(2):
            cx = col_x[side]
            # Header with character icon
            ht = self.g.font_xxs.render(headers[side], True, colors[side])
            surf.blit(ht, (cx + 18, zone_y + 10))
            # Character icon next to header
            if side == 0:
                icon = self.g.sprites.get_octopus(int(self.g.global_time * 3) % 8, win=False)
                icon_s = pygame.transform.scale(icon, (14, 18))
            else:
                icon = self.g.sprites.get_technician("blue", "brown", True, int(self.g.global_time * 3) % 4)
                icon_s = pygame.transform.scale(icon, (14, 18))
            surf.blit(icon_s, (cx, zone_y + 5))
    
            # PCs con piezas asignadas
            pc_w = min(26, (col_w - 10) // max(n, 1))
            pc_gap = 4
            start_x = cx + (col_w - n * (pc_w + pc_gap)) // 2
    
            for ci in range(n):
                px = start_x + ci * (pc_w + pc_gap)
                py = zone_y + 24
    
                # PC sprite en miniatura
                if side == 0:
                    health = self.g.ai_repair_pct[ci]
                else:
                    health = self.g.player_repair_pct[ci]
                repaired = health >= 100
                state = "repaired" if repaired else "damaged"
                spr = self.g.sprites.get_computer(state, health, 0)
                spr_s = pygame.transform.scale(spr, (pc_w, pc_w))
                surf.blit(spr_s, (px, py))
    
                # Pieza asignada (animación: cae desde arriba)
                asgn = assignments[side]
                assigned_comp = -1
                for comp_i, cpu_i in enumerate(asgn):
                    if cpu_i == ci:
                        assigned_comp = comp_i
                        break
    
                if assigned_comp >= 0:
                    # Progreso de la pieza cayendo
                    piece_delay = ci * 0.3 + side * 0.15
                    piece_t = max(0, min(1.0, (t - piece_delay) / 0.5))
                    ease = piece_t * piece_t * (3 - 2 * piece_t)
    
                    icon_comp = self.g.sprites.get_component(assigned_comp, False, 0)
                    icon_comp_s = pygame.transform.scale(icon_comp, (pc_w - 6, pc_w - 6))
                    icon_y = int(py - 20 + 20 * ease)
                    icon_x = px + 3
    
                    if piece_t < 1.0:
                        icon_comp_s.set_alpha(int(255 * ease))
                    surf.blit(icon_comp_s, (icon_x, icon_y))
    
                    # Badge de contribución
                    contrib = self.g.problem.contributions[assigned_comp][ci]
                    badge_t = self.g.font_xxs.render(f"+{contrib}", True, colors[side])
                    surf.blit(badge_t, (px + pc_w // 2 - badge_t.get_width() // 2, py + pc_w + 1))
    
    
    
    
