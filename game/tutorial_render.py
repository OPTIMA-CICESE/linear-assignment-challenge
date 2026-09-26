"""
Tutorial renderers: el ejemplo animado de reparación y el mini-ejercicio.
Animaciones a pantalla completa y texto grande (sin fondos de panel).
"""
from __future__ import annotations
import math
import pygame

GUIDE_BG = (10, 12, 26, 190)


def _super(font, text, color, n=2):
    """Texto renderizado y ampliado x2 (nearest, nítido para pixel-art)."""
    base = font.render(text, True, color)
    if n == 1:
        return base
    return pygame.transform.scale(base, (base.get_width() * n, base.get_height() * n))


def _wrap(text, font, max_w, max_lines=2):
    """Ajuste de texto por palabras; nunca se sale de max_w."""
    lines, cur = [], ""
    for w in text.split(" "):
        test = (cur + " " + w).strip()
        if not cur or font.size(test)[0] <= max_w:
            cur = test
        else:
            if len(lines) >= max_lines - 1:
                cur = (cur + " " + w).strip()
            else:
                lines.append(cur)
                cur = w
    if cur and len(lines) < max_lines:
        lines.append(cur)
    elif cur and len(lines) >= max_lines:
        lines[-1] = (lines[-1] + " " + cur).strip()
    return lines


def _guide(surf, text, color, font_sm):
    """Cinta de narración superior con texto grande (envuelto en 2 líneas)."""
    W = surf.get_size()[0]
    max_w = W - 16
    lh = 16
    lines = _wrap(text, font_sm, max_w, max_lines=2)
    h = 6 + len(lines) * lh + 4
    strip = pygame.Surface((W, h), pygame.SRCALPHA)
    strip.fill(GUIDE_BG)
    surf.blit(strip, (0, 40))
    for i, ln in enumerate(lines):
        t = font_sm.render(ln, True, color)
        surf.blit(t, (W // 2 - t.get_width() // 2, 42 + i * lh))


def draw_value_chips(surf, vals, bx, by, color, font, alpha=255, rise=0):
    """Chips de valor (PC1 x%, PC2 y%) bajo una pieza. Grandes."""
    a = max(0, min(255, int(alpha)))
    if a <= 0:
        return
    for ci, val in enumerate(vals):
        lab = font.render(f"PC{ci+1} {val}%", True, color)
        cw, ch = lab.get_width() + 8, 14
        chip = pygame.Surface((cw, ch), pygame.SRCALPHA)
        chip.fill((8, 8, 20, 200))
        pygame.draw.rect(chip, color, (0, 0, cw, ch), 2)
        chip.blit(lab, (4, 1))
        chip.set_alpha(a)
        centre = bx + 17 + (ci - 0.5) * (cw + 8)
        surf.blit(chip, (int(centre - cw / 2), int(by - rise)))


def draw_demo_repair(surf, sprites, step_time, font_sm, font_xs):
    """Ejemplo animado: valores por pieza, regla 1 pieza por PC. Ritmo lento."""
    W, H = surf.get_size()
    mid = W // 2
    t = step_time

    # Fases: 0-3 intro valores, 3-6 CPU vuela, 6-7.5 ✓, 7.5-10 GPU rechazada,
    # 10-12.5 error, 12.5-15.5 GPU a PC-2, 15.5-18 ✓ ambas reparadas.
    cpu_fly = 3.0 < t <= 6.0
    gpu_fail_fly = 7.5 < t <= 10.0
    gpu_fly = 12.5 < t <= 15.5
    cpu_done = t > 6.0
    gpu_done = t > 15.5
    show_error = 10.0 < t <= 12.5

    contrib = {0: (70, 40), 1: (35, 55)}
    names = {0: "CPU", 1: "GPU"}
    colors = {0: (80, 220, 255), 1: (240, 160, 50)}

    pc_start = [30, 55]
    health = list(pc_start)
    if cpu_done:
        health[0] = min(pc_start[0] + contrib[0][0], 100)
    if gpu_done:
        health[1] = min(pc_start[1] + contrib[1][1], 100)

    pc_sz = 48
    pc_gap = 150
    pc_x0 = mid - pc_gap // 2 - pc_sz // 2
    pc_xs = [pc_x0, pc_x0 + pc_gap]
    pc_y = 66

    piece_sz = 34
    piece_gap = 170
    piece_x0 = mid - piece_gap // 2 - piece_sz // 2
    piece_xs = [piece_x0, piece_x0 + piece_gap]
    piece_y = 148

    # Patrón de fondo de la zona de animación (sutil)
    for i in range(0, W, 24):
        pygame.draw.line(surf, (26, 29, 52), (i, 62), (i, 198), 1)

    for i in range(2):
        cx = pc_xs[i]
        sprite = sprites.get_computer(
            "repaired" if health[i] >= 100 else "damaged",
            health[i], int(t * 3) % 4)
        sprite_s = pygame.transform.scale(sprite, (pc_sz, pc_sz))
        surf.blit(sprite_s, (cx, pc_y))

        bar_y = pc_y + pc_sz + 3
        bar_w = pc_sz
        pygame.draw.rect(surf, (40, 40, 55), (cx, bar_y, bar_w, 6))
        fw = int(bar_w * min(health[i] / 100, 1.0))
        fc = (70, 210, 110) if health[i] >= 100 else (240, 220, 65)
        if fw > 0:
            pygame.draw.rect(surf, fc, (cx, bar_y, fw, 6))
        pygame.draw.rect(surf, (80, 80, 100), (cx, bar_y, bar_w, 6), 1)

        bc = (70, 210, 110) if health[i] >= 100 else (200, 200, 200)
        bt = font_xs.render(f"{health[i]}%", True, bc)
        surf.blit(bt, (cx + bar_w // 2 - bt.get_width() // 2, bar_y + 8))

        nt = font_xs.render(f"PC-{i+1}", True, (120, 120, 150))
        surf.blit(nt, (cx + bar_w // 2 - nt.get_width() // 2, pc_y - 12))

        if health[i] >= 100:
            v = _super(font_sm, "✓", (70, 210, 110))
            surf.blit(v, (cx + pc_sz + 4, pc_y + 6))

    for i in range(2):
        px = piece_xs[i]
        done = (i == 0 and cpu_done) or (i == 1 and gpu_done)
        fly = (cpu_fly and i == 0) or (gpu_fail_fly and i == 1) or (gpu_fly and i == 1)
        if done or fly:
            continue

        hl = ((i == 0 and t < 6.0) or (i == 1 and 10.5 < t < 16.0))
        bc = colors[i]
        bc_draw = bc
        if hl:
            pulse = 0.5 + 0.5 * math.sin(t * 8)
            bc_draw = tuple(int(c * pulse) for c in bc)
        pygame.draw.rect(surf, bc_draw, (px, piece_y, piece_sz, piece_sz), 2)
        icon = sprites.get_component(i, hl, int(t * 3) % 4)
        icon_s = pygame.transform.scale(icon, (piece_sz - 4, piece_sz - 4))
        surf.blit(icon_s, (px + 2, piece_y + 2))

        nm = font_xs.render(names[i], True, bc)
        surf.blit(nm, (px + piece_sz // 2 - nm.get_width() // 2, piece_y + piece_sz + 2))

        if hl or t < 3.0:
            start = 10.5 if (i == 1 and t >= 3.0) else 0.0
            appear = min(1.0, max(0.0, (t - start) / 0.35))
            draw_value_chips(
                surf, contrib[i], px, piece_y + piece_sz + 16, bc,
                font_xs, alpha=int(255 * appear), rise=int(6 * (1 - appear)))

        if hl:
            ay = int(piece_y - 10 + 3 * math.sin(t * 5))
            arr = font_xs.render("▼", True, bc_draw)
            surf.blit(arr, (px + piece_sz // 2 - 3, ay))

    FLY_SZ = 30
    if cpu_fly:
        sx, sy = piece_xs[0] + piece_sz // 2, piece_y + piece_sz // 2
        ex, ey = pc_xs[0] + pc_sz // 2, pc_y + pc_sz // 2
        prog = min(1.0, (t - 3.0) / 3.0)
        ease = prog * prog * (3 - 2 * prog)
        fx = int(sx + (ex - sx) * ease)
        fy = int(sy + (ey - sy) - 18 * math.sin(ease * math.pi))
        icon = sprites.get_component(0, True, int(t * 3) % 4)
        icon_s = pygame.transform.scale(icon, (FLY_SZ, FLY_SZ))
        surf.blit(icon_s, (fx - FLY_SZ // 2, fy - FLY_SZ // 2))
        lab = font_xs.render("+70%", True, colors[0])
        surf.blit(lab, (fx - lab.get_width() // 2, fy + 14))

    if gpu_fail_fly:
        prog = min(1.0, (t - 7.5) / 2.5)
        if prog < 0.5:
            p = prog * 2
            ease = p * p * (3 - 2 * p)
            sx, sy = piece_xs[1] + piece_sz // 2, piece_y + piece_sz // 2
            ex, ey = pc_xs[0] + pc_sz // 2, pc_y + pc_sz // 2
            fx = int(sx + (ex - sx) * ease)
            fy = int(sy + (ey - sy) - 14 * math.sin(ease * math.pi))
        else:
            p = (prog - 0.5) * 2
            ease = p * p * (3 - 2 * p)
            sx, sy = pc_xs[0] + pc_sz // 2, pc_y + pc_sz // 2
            ex, ey = piece_xs[1] + piece_sz // 2, piece_y + piece_sz // 2
            fx = int(sx + (ex - sx) * ease)
            fy = int(sy + (ey - sy) + 14 * math.sin(ease * math.pi))
        icon = sprites.get_component(1, True, int(t * 3) % 4)
        icon_s = pygame.transform.scale(icon, (FLY_SZ, FLY_SZ))
        surf.blit(icon_s, (fx - FLY_SZ // 2, fy - FLY_SZ // 2))
        lab = font_xs.render("+35%", True, colors[1])
        surf.blit(lab, (fx - lab.get_width() // 2, fy + 14))

    if gpu_fly:
        sx, sy = piece_xs[1] + piece_sz // 2, piece_y + piece_sz // 2
        ex, ey = pc_xs[1] + pc_sz // 2, pc_y + pc_sz // 2
        prog = min(1.0, (t - 12.5) / 3.0)
        ease = prog * prog * (3 - 2 * prog)
        fx = int(sx + (ex - sx) * ease)
        fy = int(sy + (ey - sy) - 18 * math.sin(ease * math.pi))
        icon = sprites.get_component(1, True, int(t * 3) % 4)
        icon_s = pygame.transform.scale(icon, (FLY_SZ, FLY_SZ))
        surf.blit(icon_s, (fx - FLY_SZ // 2, fy - FLY_SZ // 2))
        lab = font_xs.render("+55%", True, colors[1])
        surf.blit(lab, (fx - lab.get_width() // 2, fy + 14))

    # Narración dinámica del ejemplo
    if t < 3.0:
        txt, col = "Mira el valor de cada pieza hacia cada PC", (240, 225, 200)
    elif t < 6.0:
        txt, col = "CPU lleva +70% a PC-1...", colors[0]
    elif t < 7.5:
        txt, col = "30% + 70% = 100% ✓ ¡PC-1 reparada!", (70, 210, 110)
    elif t < 10.0:
        txt, col = "GPU intenta llevar +35% a PC-1...", colors[1]
    elif t < 12.5:
        txt, col = "¡NO! Cada PC solo acepta 1 pieza", (255, 120, 120)
    elif t < 15.5:
        txt, col = "GPU lleva +55% a PC-2...", colors[1]
    elif t < 18.0:
        txt, col = "¡PC-2 reparada! Pero llegó a 110: se desperdiciaron 10", (70, 210, 110)
    else:
        txt, col = ("Busca el equilibrio al asignar: así "
                    "se resuelve el problema de asignación lineal", (255, 212, 92))
    _guide(surf, txt, col, font_sm)

    octo = sprites.get_octopus(int(t * 3) % 8, win=False)
    octo_s = pygame.transform.scale(octo, (24, 28))
    surf.blit(octo_s, (W - 46, H - 108))


def draw_exercise(t, surf, sprites):
    """Mini-ejercicio: arrastra las 2 piezas sobre las 2 PCs."""
    if not t.exercise_active:
        return
    W, H = surf.get_size()
    mid = W // 2

    for i in range(0, W, 24):
        pygame.draw.line(surf, (26, 29, 52), (i, 56), (i, 192), 1)

    for ci, pc in enumerate(t.exercise_pcs):
        target_pc = getattr(t, '_exercise_target_pc', -1)
        is_target = (target_pc == ci and t.exercise_assignment[ci] < 0
                     and t.exercise_dragging >= 0)
        pc_sz = 46

        sprite = sprites.get_computer("damaged", pc["health"], int(t.global_time * 3) % 4)
        spr_s = pygame.transform.scale(sprite, (pc_sz, pc_sz))
        surf.blit(spr_s, (pc["x"], pc["y"]))

        if is_target:
            sel = t.exercise_dragging
            tc = (80, 220, 255) if sel == 0 else (240, 160, 50)
            glow = pygame.Surface((pc_sz + 8, pc_sz + 8), pygame.SRCALPHA)
            glow.fill((*tc, 55))
            surf.blit(glow, (pc["x"] - 4, pc["y"] - 4))
            pygame.draw.rect(surf, tc, (pc["x"] - 4, pc["y"] - 4, pc_sz + 8, pc_sz + 8), 3)
            arr_y = int(pc["y"] - 10 + 2 * math.sin(t.global_time * 6))
            arr_t = t.font_xs.render("▼", True, tc)
            surf.blit(arr_t, (pc["x"] + pc_sz // 2 - 4, arr_y))
        elif t.exercise_dragging >= 0 and t.exercise_assignment[ci] < 0:
            pygame.draw.rect(surf, (95, 115, 140),
                             (pc["x"] - 3, pc["y"] - 3, pc_sz + 6, pc_sz + 6), 1)

        hc = (240, 220, 65)
        ht = t.font_xs.render(f"{pc['health']}%", True, hc)
        surf.blit(ht, (pc["x"] + pc_sz // 2 - ht.get_width() // 2, pc["y"] + pc_sz + 10))

        nl = t.font_xs.render(f"PC-{ci+1}", True, (150, 150, 180))
        surf.blit(nl, (pc["x"] + pc_sz // 2 - nl.get_width() // 2, pc["y"] + pc_sz + 22))

        if t.exercise_assignment[ci] >= 0:
            pi = t.exercise_assignment[ci]
            p = t.exercise_pieces[pi]
            contrib = t._exercise_contrib[pi][ci]
            total = pc["health"] + contrib
            if total >= 100:
                v = _super(t.font_sm, "✓", (70, 210, 110))
            else:
                v = _super(t.font_sm, "F", (220, 75, 75))
            surf.blit(v, (pc["x"] + pc_sz + 4, pc["y"] + 4))

    for pi, p in enumerate(t.exercise_pieces):
        if pi == t.exercise_dragging or p["assigned_to"] >= 0:
            continue
        piece_sz = 32
        bc = (80, 220, 255) if pi == 0 else (240, 160, 50)
        pulse = 0.5 + 0.5 * math.sin(t.global_time * 6 + pi * 2)
        bc_p = tuple(int(c * pulse) for c in bc)
        pygame.draw.rect(surf, bc_p, (p["x"], p["y"], piece_sz, piece_sz), 2)
        icon = sprites.get_component(pi, True, int(t.global_time * 3) % 4)
        icon_s = pygame.transform.scale(icon, (piece_sz - 4, piece_sz - 4))
        surf.blit(icon_s, (p["x"] + 2, p["y"] + 2))

        if not t.exercise_done:
            ay = int(p["y"] - 10 + 3 * math.sin(t.global_time * 5 + pi))
            arr = t.font_xs.render("▼", True, bc)
            surf.blit(arr, (p["x"] + piece_sz // 2 - 3, ay))

    if t.exercise_dragging >= 0:
        p = t.exercise_pieces[t.exercise_dragging]
        pi = t.exercise_dragging
        piece_sz = 32
        bc = (80, 220, 255) if pi == 0 else (240, 160, 50)
        glow = pygame.Surface((piece_sz + 6, piece_sz + 6), pygame.SRCALPHA)
        glow.fill((*bc, 60))
        surf.blit(glow, (p["x"] - 3, p["y"] - 3))
        pygame.draw.rect(surf, bc, (p["x"], p["y"], piece_sz, piece_sz), 3)
        icon = sprites.get_component(pi, True, int(t.global_time * 3) % 4)
        icon_s = pygame.transform.scale(icon, (piece_sz - 4, piece_sz - 4))
        surf.blit(icon_s, (p["x"] + 2, p["y"] + 2))

        appear = min(1.0, max(0.0, (t.global_time - t.exercise_select_time) / 0.2))
        draw_value_chips(
            surf, t._exercise_contrib[pi], p["x"], p["y"] + piece_sz + 14,
            bc, t.font_xs, alpha=int(255 * appear), rise=int(6 * (1 - appear)))

    for fx in t.exercise_click_fx:
        alpha = int(255 * (fx["timer"] / 0.4))
        r = int(10 + (1 - fx["timer"] / 0.4) * 14)
        cs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(cs, (255, 255, 255, alpha), (r, r), r, 2)
        surf.blit(cs, (fx["x"] - r, fx["y"] - r))

    for fx in t.exercise_arrow_fx:
        alpha = int(200 * (fx["timer"] / 0.5))
        ls = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.line(ls, (255, 215, 90, alpha),
                         (fx["x1"], fx["y1"]), (fx["x2"], fx["y2"]), 3)
        surf.blit(ls, (0, 0))

    # Guía / feedback de la práctica
    if t.exercise_done:
        guide_txt = "¡Muy bien! ¡Ahora sí sabes reparar computadoras!"
        strip_color = (70, 210, 110)
    elif t.exercise_dragging >= 0:
        pi = t.exercise_dragging
        p = t.exercise_pieces[pi]
        target = getattr(t, '_exercise_target_pc', 0)
        empty_pcs = [ci for ci, a in enumerate(t.exercise_assignment) if a < 0]
        if target not in empty_pcs and empty_pcs:
            target = empty_pcs[0]
        if target in empty_pcs:
            contrib = t._exercise_contrib[pi][target]
            total = t.exercise_pcs[target]["health"] + contrib
            if total >= 100:
                guide_txt = f"{p['name']} a PC-{target+1}: +{contrib}% = {total}% ✓"
            else:
                guide_txt = f"{p['name']} a PC-{target+1}: +{contrib}% = {total}%... no alcanza"
            strip_color = (70, 210, 110) if total >= 100 else (240, 220, 65)
        else:
            guide_txt = "Selecciona una pieza con ← →"
            strip_color = (240, 225, 200)
    else:
        guide_txt = t.exercise_msg if t.exercise_msg else "Usa ← → y ↑ ↓ para elegir, ENTER coloca"
        strip_color = t.exercise_msg_color
    _guide(surf, guide_txt, strip_color, t.font_sm)

    octo = sprites.get_octopus(int(t.global_time * 3) % 8, win=False)
    octo_s = pygame.transform.scale(octo, (24, 28))
    surf.blit(octo_s, (W - 46, H - 108))