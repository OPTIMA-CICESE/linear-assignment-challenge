"""
Game controller — loop, states, input, game logic. Rendering lives in render.py.
"""
from __future__ import annotations
import sys, os, random
from typing import List, Optional, Tuple
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C
from core.problem import AssignmentProblem, ProblemGenerator, Solution
from core.scoring import ScoringSystem
from algorithm.genetic import GeneticAlgorithm
from assets.sprites import SpriteFactory
from ui.effects import (
    ParticleSystem, FloatingText, FloatingTextSystem,
    ScreenShake, ConfettiSystem,
    StarField, ScreenTransition, ScoreDisplay,
    ResultAnimator,
)
from game.states import State
from game.render import GameRenderer
from game.tutorial import TutorialSystem, get_default_tutorial
from audio.manager import AudioManager

DRAG_THRESHOLD = 4


class Game:
    def __init__(self):
        pygame.init()
        self.logical = pygame.Surface((C.LOGICAL_W, C.LOGICAL_H))
        pygame.display.set_caption(C.TITLE)
        self.fullscreen = True
        self.window = self._create_window()
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_title = C._make_font(38)
        self.font_lg    = C._make_font(26)
        self.font_md    = C._make_font(20)
        self.font_sm    = C._make_font(15)
        self.font_xs    = C._make_font(11)
        self.font_xxs   = C._make_font(9)
        self.font_mini  = C._make_font(8)

        self.sprites = SpriteFactory()
        self.particles = ParticleSystem()
        self.floating = FloatingTextSystem()
        self.shake = ScreenShake()
        self.confetti = ConfettiSystem()
        self.stars = StarField(60)
        self.transition = ScreenTransition()
        self.result_anim = ResultAnimator()

        self.tutorial = TutorialSystem(
            self.font_md, self.font_sm, self.font_xs, self.font_xxs
        )
        self.tutorial_done = False

        self.state = State.TUTORIAL
        self.state_timer = 0.0
        self.global_time = 0.0
        self.current_level = 0

        self.problem: Optional[AssignmentProblem] = None
        self.ai_solution: Optional[Solution] = None
        self.player_assignment: List[int] = []
        self.player_score: Optional[Solution] = None
        self.used_components: List[int] = []

        self.selected_component: int = -1
        self.selected_computer: int = 0

        self.ai_ga: Optional[GeneticAlgorithm] = None
        self.ai_steps_done = 0
        self.ai_step_timer = 0.0
        self.ai_best_score = 0.0

        self.player_repair_pct: List[float] = []
        self.ai_repair_pct: List[float] = []

        self.result_text = ""
        self.result_color = C.C_WHITE
        self.menu_cursor = 0
        self.menu_items = ["Iniciar", "Seleccionar nivel", "Ver tutorial", "Configuración", "Créditos", "Salir"]
        self.menu_blink = 0.0

        self.level_names = [lv["name"] for lv in C.LEVELS]
        self.level_cursor = 0

        # Settings
        self.settings_cursor = 0
        self.settings_items = ["Volumen música", "Vol. efectos", "Modo dificultad", "Modo daltonismo"]
        self.music_volume = 0.2
        self.sfx_volume = 0.2
        self.difficulty = C.DIFFICULTY_NORMAL  # 0=Ultra fácil, 1=Fácil, 2=Normal, 3=Difícil
        self.difficulty_names = [d[0] for d in C.DIFFICULTIES]
        self.mode_toast = None      # (texto, segundos restantes) al cambiar de modo
        self.result_reason = ""
        self.early_win = False
        self.colorblind_mode = False
        self._settings_rects: List[pygame.Rect] = []
        self.level_transition_timer = 0.0
        self.level_transition_name = ""
        self.level_transition_active = False
        self._settings_dragging = False

        self.player_score_display = ScoreDisplay()
        self.ai_score_display = ScoreDisplay()

        self._comp_rects: List[pygame.Rect] = []
        self._cpu_rects: List[pygame.Rect] = []
        self._menu_rects: List[pygame.Rect] = []
        self._level_rects: List[pygame.Rect] = []
        self._result_rects: List[pygame.Rect] = []
        self._undo_rect: Optional[pygame.Rect] = None
        self.result_cursor = 0

        self.gfx = GameRenderer(self)

        self.dragging = False
        self.drag_comp: int = -1
        self.drag_mouse: Tuple[int, int] = (0, 0)
        self.mouse_pos: Tuple[int, int] = (0, 0)
        self.drag_start: Tuple[int, int] = (0, 0)
        self.drag_started_move = False
        self.drag_hover_cpu: int = -1

        self.level_time_limit = 0.0
        self.time_left = 0.0
        self.time_up = False

        self.gear_frame = 0
        self.gear_timer = 0.0
        self.char_frame = 0
        self.char_timer = 0.0
        self.computer_frame = 0

        self.audio = AudioManager()
        self._setup_music()

        self._start_tutorial()

    def _setup_music(self):
        # Intro plays at start
        if self.state == State.TUTORIAL:
            self.audio.play_music("intro")
        else:
            self.audio.play_music("menu")

    def _handle_music_state(self):
        if self.state == State.TUTORIAL:
            self.audio.play_music("intro")
        elif self.state in (State.PLAYING, State.SELECT_COMPUTER,
                            State.DRAGGING, State.AI_TURN, State.RESULT):
            self.audio.play_level(self.current_level)
        elif self.state in (State.MENU, State.LEVEL_SELECT):
            self.audio.play_music("menu")

    def _start_tutorial(self):
        steps = get_default_tutorial()
        self.tutorial.start(steps, on_complete=self._on_tutorial_done)
        self.state = State.TUTORIAL

    def _on_tutorial_done(self):
        self.tutorial_done = True
        self.state = State.MENU
        self.transition.fade_in()

    # ── Ventana / pantalla completa ────────────────────────

    def _windowed_size(self):
        """Tamaño de la VENTANA en múltiplos ENTEROS de la resolución lógica.
        El escalado entero mantiene el pixel-art nítido (nada de blur) y es
        mucho más barato que un escalado fraccionario."""
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            dw, dh = 0, 0
        scale = C.SCALE
        if dw and dh:
            # Nunca mayor que el escritorio: si no, la ventana se sale de la
            # pantalla y solo se ve una esquina del juego.
            scale = min(scale, max(1, dw // C.LOGICAL_W), max(1, dh // C.LOGICAL_H))
        return (C.LOGICAL_W * scale, C.LOGICAL_H * scale)

    def _sdl_window(self):
        try:
            import pygame._sdl2 as sdl2
            return sdl2.Window.from_display_module()
        except Exception:
            return None

    def _create_window(self):
        """Crea la ventana.

        La SUPERFICIE del juego siempre es 480x270 (resolución lógica) y la
        ventana se escala por SDL. Si la superficie se creara ya escalada, el
        blit 1:1 de 480x270 solo llenaría una esquina de la ventana.
        """
        self.window = None
        self._apply_window_mode()
        return self.window

    def _apply_window_mode(self):
        """Aplica pantalla completa o ventana SIN recrear la superficie de
        juego (recrearla con set_mode provocaba parpadeo y reencuadres)."""
        win = self._sdl_window()
        if win is not None:
            try:
                if self.fullscreen:
                    win.set_fullscreen()
                else:
                    win.set_windowed()
                    win.size = self._windowed_size()
            except pygame.error:
                pass

        # La superficie SIEMPRE va a resolución lógica (480x270); el escalado
        # lo hace SDL. Se prueban varias combinaciones porque no todos los
        # drivers/drivers de video aceptan SCALED + FULLSCREEN.
        size = (C.LOGICAL_W, C.LOGICAL_H)
        intentos = []
        if self.fullscreen:
            intentos.append((pygame.SCALED | pygame.FULLSCREEN, True))
        intentos.append((pygame.SCALED, False))
        intentos.append((0, False))

        for flags, es_fullscreen in intentos:
            try:
                self.window = pygame.display.set_mode(size, flags)
            except pygame.error as e:
                ultimo_error = e
                continue
            if self.fullscreen and not es_fullscreen:
                # El driver no permite pantalla completa: seguimos en ventana.
                self.fullscreen = False
                if win is not None:
                    try:
                        win.set_windowed()
                        win.size = self._windowed_size()
                    except pygame.error:
                        pass
            pygame.display.set_caption(C.TITLE)
            return

        print(f"[ventana] no se pudo crear la ventana: {ultimo_error}")
        raise ultimo_error

    # ── Fullscreen / Maximize ──────────────────────────────

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._apply_window_mode()


    # ── Render ─────────────────────────────────────────────

    def _render(self):
        self.gfx.render(self.logical, self.window)

    # ── Main loop ──────────────────────────────────────────

    def run(self):
        self.transition.fade_in()
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            dt = min(dt, 0.05)
            self.global_time += dt
            self._events()
            self._update(dt)
            self._render()
        pygame.quit()

    # ── Events ─────────────────────────────────────────────

    def _events(self):
        mx_raw, my_raw = pygame.mouse.get_pos()
        scale_x = self.window.get_width() / C.LOGICAL_W
        scale_y = self.window.get_height() / C.LOGICAL_H
        mx = int(mx_raw / scale_x)
        my = int(my_raw / scale_y)
        self.mouse_pos = (mx, my)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif ev.key == pygame.K_m:
                    self.audio.toggle_mute()
                elif ev.key == pygame.K_g:
                    self._toggle_easy_mode()
                else:
                    self._handle_key(ev.key)

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.audio.play_sound("click")
                self._handle_mouse_down(mx, my)

            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                self._handle_mouse_up(mx, my)

            elif ev.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(mx, my)

    # ── Mouse handlers ─────────────────────────────────────

    def _handle_mouse_down(self, mx, my):
        # Boton de deshacer: se prueba antes que las piezas para que nunca
        # quede detras de ellas, y funciona sin tocar el teclado.
        if self._undo_rect is not None and self._undo_rect.collidepoint(mx, my):
            if self.used_components:
                self._undo_last()
                self.audio.play_sound("place")
            return

        if self.state == State.TUTORIAL:
            if self.tutorial.exercise_active and not self.tutorial.exercise_done:
                self.tutorial.exercise_mouse_down(mx, my)
            else:
                self.tutorial.advance()
            return

        if self.state == State.MENU:
            for i, r in enumerate(self._menu_rects):
                if r.collidepoint(mx, my):
                    self._menu_action(i)
                    return

        elif self.state == State.LEVEL_SELECT:
            for i, r in enumerate(self._level_rects):
                if r.collidepoint(mx, my):
                    self.current_level = i
                    self._start_game(i)
                    return

        elif self.state == State.SETTINGS:
            for i, r in enumerate(self._settings_rects):
                if r.collidepoint(mx, my):
                    self.settings_cursor = i
                    if i == 0 or i == 1:
                        self._settings_dragging = True
                    elif i == 2:
                        self._apply_difficulty(
                            (self.difficulty + 1) % len(C.DIFFICULTIES), announce=True)
                        self.audio.play_sound("click")
                    elif i == 3:
                        self.colorblind_mode = not self.colorblind_mode
                        self.audio.play_sound("click")
                    return
            self._settings_dragging = False

        elif self.state == State.PLAYING:
            for i, r in enumerate(self._comp_rects):
                if r.collidepoint(mx, my) and i not in self.used_components:
                    # Al hacer clic (o agarrar para arrastrar) también se
                    # selecciona la pieza, para mostrar su utilidad al instante.
                    self.selected_component = i
                    self.selected_computer = 0
                    self.dragging = True
                    self.drag_comp = i
                    self.drag_mouse = (mx, my)
                    self.drag_start = (mx, my)
                    self.drag_started_move = False
                    self.drag_hover_cpu = -1
                    return

        elif self.state == State.SELECT_COMPUTER:
            for i, r in enumerate(self._cpu_rects):
                if r.collidepoint(mx, my):
                    self._confirm_assignment(i)
                    return

        elif self.state == State.RESULT:
            for i, r in enumerate(self._result_rects):
                if r.collidepoint(mx, my):
                    self._result_choose(i)
                    return

    def _handle_mouse_up(self, mx, my):
        if self.state == State.TUTORIAL:
            if self.tutorial.exercise_active:
                self.tutorial.exercise_mouse_up(mx, my)
            return

        self._settings_dragging = False

        if self.dragging and self.state == State.DRAGGING:
            if self.drag_hover_cpu >= 0:
                self._confirm_assignment(self.drag_hover_cpu)
            else:
                self._cancel_drag()
        elif self.dragging and self.state == State.PLAYING:
            # Clic simple (o soltar sin arrastrar): solo detenemos el "arrastre"
            # pendiente, pero la pieza queda seleccionada para ver su utilidad.
            self.dragging = False
            self.drag_comp = -1
            self.drag_hover_cpu = -1
            self.drag_started_move = False

    def _handle_mouse_motion(self, mx, my):
        self.drag_mouse = (mx, my)

        if self.state == State.TUTORIAL:
            if self.tutorial.exercise_active:
                self.tutorial.exercise_mouse_move(mx, my)
            return

        if self.dragging and self.state == State.PLAYING:
            dx = mx - self.drag_start[0]
            dy = my - self.drag_start[1]
            if dx * dx + dy * dy > DRAG_THRESHOLD * DRAG_THRESHOLD:
                self.drag_started_move = True
                self.state = State.DRAGGING
                self.state_timer = 0.0

        if self.dragging and self.state == State.DRAGGING:
            self.drag_hover_cpu = -1
            for i, r in enumerate(self._cpu_rects):
                if r.collidepoint(mx, my):
                    self.drag_hover_cpu = i
                    break

        # Settings drag for volume orbs
        if self.state == State.SETTINGS and self._settings_dragging:
            W = C.LOGICAL_W
            mid_x = W // 2
            orb_r = 20
            gap = 56
            start_x = mid_x - (3 * gap) // 2
            orb_y = 70
            cx = start_x + self.settings_cursor * gap
            # Map horizontal mouse position to volume 0-1
            rel_x = mx - (cx - orb_r * 2)
            vol = max(0.0, min(1.0, rel_x / (orb_r * 4)))
            if self.settings_cursor == 0:
                self.music_volume = round(vol, 1)
                self.audio.set_music_volume(self.music_volume)
            elif self.settings_cursor == 1:
                self.sfx_volume = round(vol, 1)
                self.audio.set_sfx_volume(self.sfx_volume)

    def _fade_nav(self, duration=None):
        """Fundido corto al cambiar de pantalla: evita el corte seco entre menús."""
        self.state_timer = 0.0
        self.transition.fade_in(duration or ScreenTransition.NAV_FADE)

    def _menu_action(self, idx):
        if idx == 0:
            self.current_level = 0
            self._start_game(0)
        elif idx == 1:
            self.state = State.LEVEL_SELECT
            self._fade_nav()
        elif idx == 2:
            self._start_tutorial()
        elif idx == 3:
            self.state = State.SETTINGS
            self._fade_nav()
        elif idx == 4:
            self.state = State.CREDITS
            self._fade_nav()
        elif idx == 5:
            self.running = False

    def _result_options(self) -> List[str]:
        opts = ["Reintentar nivel"]
        has_next = self.current_level < len(C.LEVELS) - 1
        if has_next:
            opts.append(f"Siguiente nivel")
        opts.append("Menú")
        return opts

    def _result_choose(self, idx):
        opts = self._result_options()
        if idx >= len(opts):
            idx = 0
        self.result_anim.reset()
        label = opts[idx]
        if label == "Reintentar nivel":
            self._start_game(self.current_level)
        elif label == "Siguiente nivel":
            self.current_level = min(self.current_level + 1, len(C.LEVELS) - 1)
            self._start_game(self.current_level)
        else:  # Menú
            self.state = State.MENU
            self._fade_nav()

    def _cancel_drag(self):
        self.dragging = False
        self.drag_comp = -1
        self.drag_hover_cpu = -1
        self.state = State.PLAYING
        self.state_timer = 0.0

    # ── Keyboard ───────────────────────────────────────────

    def _handle_key(self, key):
        if self.state == State.TUTORIAL:
            if key == pygame.K_ESCAPE:
                self.tutorial.skip()
            elif self.tutorial.exercise_active and not self.tutorial.exercise_done:
                self.tutorial.exercise_key_down(key)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.tutorial.advance()

        elif self.state == State.MENU:
            if key == pygame.K_UP:
                self.menu_cursor = (self.menu_cursor - 3) % len(self.menu_items)
            elif key == pygame.K_DOWN:
                self.menu_cursor = (self.menu_cursor + 3) % len(self.menu_items)
            elif key == pygame.K_LEFT:
                self.menu_cursor = (self.menu_cursor - 1) % len(self.menu_items)
            elif key == pygame.K_RIGHT:
                self.menu_cursor = (self.menu_cursor + 1) % len(self.menu_items)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._menu_action(self.menu_cursor)

        elif self.state == State.LEVEL_SELECT:
            if key == pygame.K_UP:
                self.level_cursor = (self.level_cursor - 1) % len(self.level_names)
            elif key == pygame.K_DOWN:
                self.level_cursor = (self.level_cursor + 1) % len(self.level_names)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.current_level = self.level_cursor
                self._start_game(self.current_level)
            elif key == pygame.K_ESCAPE:
                self.state = State.MENU
                self._fade_nav()

        elif self.state == State.SETTINGS:
            if key == pygame.K_UP:
                self.settings_cursor = (self.settings_cursor - 1) % len(self.settings_items)
            elif key == pygame.K_DOWN:
                self.settings_cursor = (self.settings_cursor + 1) % len(self.settings_items)
            elif key in (pygame.K_LEFT, pygame.K_a):
                self._settings_adjust(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self._settings_adjust(1)
            elif key == pygame.K_ESCAPE:
                self.state = State.MENU
                self._fade_nav()

        elif self.state == State.CREDITS:
            if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.state = State.MENU
                self._fade_nav()

        elif self.state == State.PLAYING:
            if key == pygame.K_ESCAPE:
                self.state = State.MENU
                self._fade_nav()
            elif key in (pygame.K_LEFT, pygame.K_a):
                self._cycle_component(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self._cycle_component(1)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.selected_component >= 0:
                    self.state = State.SELECT_COMPUTER
                    self.selected_computer = 0
                    self.state_timer = 0.0
            elif key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                self._undo_last()

        elif self.state == State.SELECT_COMPUTER:
            if key == pygame.K_ESCAPE:
                self.state = State.PLAYING
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.selected_computer = (self.selected_computer - 1) % self.problem.num_computers
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.selected_computer = (self.selected_computer + 1) % self.problem.num_computers
            elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                         pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9):
                num = key - pygame.K_1
                if num < self.problem.num_computers:
                    self.selected_computer = num
                    self._confirm_assignment(num)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_assignment(self.selected_computer)

        elif self.state == State.RESULT:
            opts = self._result_options()
            if key == pygame.K_UP:
                self.result_cursor = (self.result_cursor - 1) % len(opts)
            elif key == pygame.K_DOWN:
                self.result_cursor = (self.result_cursor + 1) % len(opts)
            elif key == pygame.K_ESCAPE:
                self._result_choose(len(opts) - 1)  # Menú
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._result_choose(self.result_cursor)

    # ── Game logic ─────────────────────────────────────────

    def _start_game(self, level_idx):
        self.current_level = level_idx
        lvl = C.LEVELS[level_idx]
        seed = random.randint(0, 999999)
        gen = ProblemGenerator(seed)
        self.problem = gen.generate(
            lvl["computers"], lvl["components"],
            lvl["req_range"], lvl["cap_range"], lvl["name"],
        )
        self.ai_ga = GeneticAlgorithm(
            self.problem, C.ga_population(lvl, self.difficulty),
            C.ga_generations(lvl, self.difficulty), lvl["ai_mut"], seed=seed,
        )
        self.ai_ga.initialize()
        self.ai_solution = None
        self.ai_total_steps = C.ga_generations(lvl, self.difficulty)
        self.ai_step_delay = C.ga_step_delay(self.difficulty)
        self.player_assignment = [-1] * self.problem.num_components
        self.player_score = None
        self.used_components = []
        self.selected_component = 0 if self.problem.num_components > 0 else -1
        self.selected_computer = 0
        self.ai_steps_done = 0
        self.ai_step_timer = 0.0
        self.early_win = False
        self.ai_best_score = 0.0
        self.player_repair_pct = [100 - r for r in self.problem.requirements]
        self.ai_repair_pct = [100 - r for r in self.problem.requirements]
        self.player_score_display = ScoreDisplay()
        self.ai_score_display = ScoreDisplay()
        self.particles.clear()
        self.floating.clear()
        self.confetti.clear()
        self.shake.offset_x = self.shake.offset_y = 0
        self.dragging = False
        self.drag_comp = -1
        self.drag_hover_cpu = -1
        self.level_time_limit = float(lvl.get("time", 0)) * C.difficulty_time_mult(self.difficulty)
        self.time_left = self.level_time_limit
        self.time_up = False
        self.state = State.PLAYING
        self.state_timer = 0.0
        self.result_anim.reset()
        self.transition.fade_in()
        # Level transition animation
        self.level_transition_timer = 2.5
        self.level_transition_name = lvl["name"]
        self.level_transition_active = True

    def _cycle_component(self, direction):
        n = self.problem.num_components
        if n == 0:
            return
        avail = [i for i in range(n) if i not in self.used_components]
        if not avail:
            self.selected_component = -1
            return
        if self.selected_component in avail:
            idx = (avail.index(self.selected_component) + direction) % len(avail)
            self.selected_component = avail[idx]
        else:
            self.selected_component = avail[0]

    def _confirm_assignment(self, cpu_idx):
        comp = self.selected_component if not self.dragging else self.drag_comp
        if comp < 0 or comp in self.used_components:
            return
        if cpu_idx < 0 or cpu_idx >= self.problem.num_computers:
            return
        # Asignación uno-a-uno (LAP): cada computadora recibe SOLO una pieza.
        # No se permite colocar una pieza sobre una PC que ya tiene otra.
        if cpu_idx in self.player_assignment:
            self.floating.add(FloatingText(
                self._cpu_rects[cpu_idx].centerx,
                self._cpu_rects[cpu_idx].centery - 18,
                "¡Solo 1 pieza por PC!", C.C_RED, font=self.font_sm))
            self.audio.play_sound("error")
            return

        self.player_assignment[comp] = cpu_idx
        self.used_components.append(comp)

        contrib = self.problem.contributions[comp][cpu_idx]
        req = self.problem.requirements[cpu_idx]
        # Tope visual: la reparación nunca pasa de 100%.
        self.player_repair_pct[cpu_idx] = min(self.player_repair_pct[cpu_idx] + contrib, 100)

        cx = self._cpu_rects[cpu_idx].centerx if cpu_idx < len(self._cpu_rects) else C.LOGICAL_W // 2
        cy = self._cpu_rects[cpu_idx].centery if cpu_idx < len(self._cpu_rects) else 100

        if self.player_repair_pct[cpu_idx] >= 100:
            self.particles.emit_repair_burst(cx, cy)
            self.floating.add(FloatingText(cx, cy - 18, "✓", C.C_GREEN, font=self.font_sm))
            self.shake.trigger(2.5, 0.15)
            self.audio.play_sound("success")
        else:
            self.particles.emit_sparks(cx, cy, 8)
            self.floating.add(FloatingText(cx, cy - 18, "F", C.C_RED, font=self.font_sm))
            self.audio.play_sound("place")

        self.player_score = ScoringSystem.evaluate(self.problem, self.player_assignment)
        self.player_score_display.set_target(self.player_score.score if self.player_score else 0)

        self.dragging = False
        self.drag_comp = -1
        self.drag_hover_cpu = -1

        avail = [i for i in range(self.problem.num_components) if i not in self.used_components]
        if avail:
            self.selected_component = avail[0]
            self.state = State.PLAYING
        else:
            self.selected_component = -1
            self._finish_player_turn()

        self.state_timer = 0.0

    def _undo_last(self):
        if not self.used_components:
            return
        last_comp = self.used_components.pop()
        self.player_assignment[last_comp] = -1
        cover = [0.0] * self.problem.num_computers
        for ci in range(self.problem.num_components):
            cpu_i = self.player_assignment[ci]
            if cpu_i >= 0:
                cover[cpu_i] = min(cover[cpu_i] + self.problem.contributions[ci][cpu_i], 100)
        for i in range(self.problem.num_computers):
            self.player_repair_pct[i] = min(100 - self.problem.requirements[i] + cover[i], 100)
        self.selected_component = last_comp
        self.player_score = ScoringSystem.evaluate(self.problem, self.player_assignment) if any(c >= 0 for c in self.player_assignment) else None
        self.player_score_display.set_target(self.player_score.score if self.player_score else 0)

    def _finish_player_turn(self):
        if self._player_already_best():
            # El jugador llego a la mejor solucion conocida antes de que el
            # GA terminara: la carrera se decide aqui, sin esperar.
            self.early_win = True
            self.ai_solution = self.ai_ga.get_best()
            self._show_result()
        elif self.ai_steps_done >= self.ai_total_steps:
            self.ai_solution = self.ai_ga.get_best()
            self._show_result()
        else:
            self.state = State.AI_TURN
            self.state_timer = 0.0

    def _player_already_best(self):
        """True si el jugador igualo o supero la mejor solucion del GA."""
        if self.ai_ga is None or self.player_score is None:
            return False
        best = self.ai_ga.get_best().score
        if best <= 0:
            return False
        return self.player_score.score >= best - 1e-9

    def _toggle_easy_mode(self):
        """Tecla G: alterna entre modo ultra facil y modo normal."""
        objetivo = C.DIFFICULTY_NORMAL if self.difficulty == C.DIFFICULTY_ULTRA else C.DIFFICULTY_ULTRA
        self._apply_difficulty(objetivo, announce=True)

    def _apply_difficulty(self, idx, announce=False):
        anterior = self.difficulty
        self.difficulty = max(0, min(len(C.DIFFICULTIES) - 1, int(idx)))
        nombre = self.difficulty_names[self.difficulty]
        if self.problem is not None:
            lvl = C.LEVELS[self.current_level]
            # El GA nunca se queda sin presupuesto por debajo del que ya uso,
            # y al subir de modo puede seguir pensando.
            self.ai_total_steps = C.ga_generations(lvl, self.difficulty)
            self.ai_step_delay = C.ga_step_delay(self.difficulty)
            self.ai_steps_done = min(self.ai_steps_done, self.ai_total_steps)
            if self.ai_ga is not None:
                self.ai_ga.set_population_size(C.ga_population(lvl, self.difficulty))
            # El tiempo se reescala para que el cambio se note de inmediato.
            viejo = C.difficulty_time_mult(anterior)
            nuevo = C.difficulty_time_mult(self.difficulty)
            if viejo > 0 and not self.time_up:
                nuevo_limite = float(lvl.get("time", 0)) * nuevo
                self.time_left = min(nuevo_limite, self.time_left * (nuevo / viejo))
                self.level_time_limit = nuevo_limite
        if announce:
            self.audio.play_sound("click")
            extras = {
                C.DIFFICULTY_ULTRA: "el algoritmo casi no piensa",
                C.DIFFICULTY_NORMAL: "el algoritmo trabaja normal",
            }
            self.mode_toast = (
                f"Modo: {nombre} - {extras.get(self.difficulty, 'el algoritmo busca mas')}",
                2.4,
            )
            self.floating.add(FloatingText(
                C.LOGICAL_W // 2, 118, f"Modo: {nombre}", C.C_GOLD,
                font=self.font_sm, duration=1.6))
        return nombre

    def _update_ai(self, dt):
        if self.ai_ga is None:
            return
        total = self.ai_total_steps
        if self.ai_steps_done >= total:
            return
        self.ai_step_timer += dt
        stepped = False
        while self.ai_step_timer >= self.ai_step_delay and self.ai_steps_done < total:
            self.ai_step_timer -= self.ai_step_delay
            self.ai_ga.step()
            self.ai_steps_done += 1
            stepped = True
        if stepped:
            best = self.ai_ga.get_best()
            self.ai_best_score = best.score
            self.ai_score_display.set_target(self.ai_best_score)
            ai_cover = [0.0] * self.problem.num_computers
            for ci, cpu_i in enumerate(best.assignment):
                if cpu_i >= 0:
                    # Tope visual a 100%
                    ai_cover[cpu_i] = min(ai_cover[cpu_i] + self.problem.contributions[ci][cpu_i], 100)
            for i in range(self.problem.num_computers):
                total_health = min(100 - self.problem.requirements[i] + ai_cover[i], 100)
                if total_health >= 100 and self.ai_repair_pct[i] < 100:
                    self.particles.emit_repair_burst(10 + i * 26 + 16, 64 + 16)
                    self.floating.add(FloatingText(
                        10 + i * 26 + 16, 40, "¡Reparado!", C.C_ORANGE, font=self.font_xxs))
                self.ai_repair_pct[i] = total_health
            self.gear_frame += 1
        if self.ai_steps_done >= total and self.state == State.AI_TURN:
            self.ai_solution = self.ai_ga.get_best()
            self._show_result()

    def _show_result(self):
        if self.player_score is None:
            self.player_score = ScoringSystem.evaluate(self.problem, self.player_assignment)
        if self.ai_solution is None:
            self.ai_solution = self.ai_ga.get_best()

        outcome = ScoringSystem.compare(self.player_score, self.ai_solution, C.TIE_THRESHOLD)
        diff = self.player_score.score - self.ai_solution.score
        if outcome == "WIN":
            if self.early_win and diff >= 0:
                self.result_reason = "Llegaste antes que el algoritmo"
            elif diff > 0:
                self.result_reason = "Superaste al algoritmo"
            else:
                self.result_reason = "Misma solucion que el algoritmo"
        elif outcome == "LOSS":
            self.result_reason = "El algoritmo hallo una mejor solucion"
        else:
            self.result_reason = "Empate"
        cx, cy = C.LOGICAL_W // 2, 60
        self.result_anim.start(outcome, cx, cy)
        if outcome == "WIN":
            self.result_text = "¡Victoria!"
            self.result_color = C.C_GREEN
            self.confetti.burst(C.LOGICAL_W // 2, 70, 90)
            self.confetti.burst(C.LOGICAL_W // 4, 90, 50)
            self.confetti.burst(3 * C.LOGICAL_W // 4, 90, 50)
            self.particles.emit_multi_bursts(C.LOGICAL_W // 2, 60, 5)
            self.shake.trigger(4.0, 0.5)
            self.audio.play_sound("success")
        elif outcome == "LOSS":
            self.result_text = "¡PC PLAYER gana!"
            self.result_color = C.C_RED
            self.particles.emit_fail_burst(C.LOGICAL_W // 2, 90)
            self.shake.trigger(2.5, 0.3)
        else:
            self.result_text = "¡Empate!"
            self.result_color = C.C_YELLOW
            self.confetti.burst(C.LOGICAL_W // 2, 70, 60)
            self.particles.emit(C.LOGICAL_W // 2, 60, 20, C.C_YELLOW, speed=90, life=0.9, size=2, gravity=40)
        self.state = State.RESULT
        self.state_timer = 0.0
        self.result_compare_timer = 0.0

    def _result_fonts(self):
        return {"sm": self.font_sm, "xxs": self.font_xxs, "md": self.font_md}

    # ── Update ─────────────────────────────────────────────

    def _update(self, dt):
        self.state_timer += dt
        if self.mode_toast:
            _txt, left = self.mode_toast
            self.mode_toast = (_txt, left - dt) if left - dt > 0 else None
        self.stars.update(dt)
        self.particles.update(dt)
        self.floating.update(dt)
        self.shake.update(dt)
        self.confetti.update(dt)
        self.transition.update(dt)
        self.player_score_display.update(dt)
        self.ai_score_display.update(dt)
        if self.level_transition_active:
            self.level_transition_timer -= dt
            if self.level_transition_timer <= 0:
                self.level_transition_active = False

        self._handle_music_state()
        self.result_anim.update(dt, self.particles, self.confetti,
                                self.floating, (C.LOGICAL_W // 2, 60),
                                self._result_fonts())
        self.gear_timer += dt
        if self.gear_timer > 0.12:
            self.gear_timer -= 0.12
            self.gear_frame += 1

        self.char_timer += dt
        if self.char_timer > 0.2:
            self.char_timer -= 0.2
            self.char_frame += 1

        self.computer_frame += 1

        # ── Efectos ambientales ──────────────────────────
        if self.state in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING,
                          State.AI_TURN, State.TUTORIAL):
            if random.random() < dt * 2.0:
                self.particles.emit(
                    random.uniform(20, C.LOGICAL_W - 20),
                    random.uniform(70, 130),
                    1,
                    random.choice([C.C_CYAN, C.C_PURPLE, C.C_YELLOW, C.C_GREEN]),
                    speed=12, life=0.6, size=1, gravity=0,
                )

        # ── Destellos en las PCs del jugador aún por reparar ──
        if self.problem and self.state in (State.PLAYING, State.SELECT_COMPUTER,
                                           State.DRAGGING, State.AI_TURN):
            n = self.problem.num_computers
            area_w = min(34, (C.LOGICAL_W // 2 - 20) // max(n, 1))
            start_x = C.LOGICAL_W // 2 + 10 + ((C.LOGICAL_W // 2 - 20) - n * area_w) // 2
            for ci in range(n):
                if self.player_repair_pct[ci] >= 100:
                    continue
                px = start_x + ci * area_w + random.uniform(4, 22)
                py = 64 + random.uniform(0, 10)
                if random.random() < dt * 2.5:
                    self.particles.emit(
                        px, py, 1, C.C_GLOW_YELLOW,
                        speed=random.uniform(20, 40), life=0.7, size=2, gravity=-20,
                    )

        # ── Resaltar zona del jugador (solo nivel 1, mientras coloca piezas) ──
        if (self.current_level == 0 and self.problem
                and self.state in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING)
                and len(self.used_components) < self.problem.num_components):
            if random.random() < dt * 10.0:
                self.particles.emit(
                    random.uniform(C.LOGICAL_W // 2 + 4, C.LOGICAL_W - 6),
                    random.uniform(4, 108),
                    1, random.choice([C.C_GOLD, C.C_YELLOW, C.C_WHITE]),
                    speed=random.uniform(6, 16), life=0.9, size=2, gravity=0,
                )

        if self.state == State.TUTORIAL:
            self.tutorial.update(dt)
        elif self.state in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING, State.AI_TURN):
            self._update_ai(dt)
            self._update_timer(dt)

    def _update_timer(self, dt):
        if self.level_time_limit <= 0 or self.time_up:
            return
        if self.level_transition_active:
            return
        if self.state not in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING, State.AI_TURN):
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0.0
            self._on_time_up()

    def _on_time_up(self):
        self.time_up = True
        self.dragging = False
        self.drag_comp = -1
        self.drag_hover_cpu = -1
        self.floating.add(FloatingText(
            C.LOGICAL_W // 2, 100, "¡Tiempo agotado!", C.C_RED,
            font=self.font_md, duration=1.6))
        self.audio.play_sound("error")
        self.shake.trigger(3.0, 0.3)
        self.player_score = ScoringSystem.evaluate(self.problem, self.player_assignment)
        self.player_score_display.set_target(self.player_score.score if self.player_score else 0)
        self._finish_player_turn()

    # ── Render ─────────────────────────────────────────────

    def _settings_adjust(self, direction):
        item = self.settings_cursor
        if item == 0:  # Music volume
            self.music_volume = max(0.0, min(1.0, self.music_volume + direction * 0.1))
            self.audio.set_music_volume(self.music_volume)
            self.audio.play_sound("click")
        elif item == 1:  # SFX volume
            self.sfx_volume = max(0.0, min(1.0, self.sfx_volume + direction * 0.1))
            self.audio.set_sfx_volume(self.sfx_volume)
            self.audio.play_sound("click")
        elif item == 2:  # Difficulty
            nuevo = max(0, min(len(C.DIFFICULTIES) - 1, self.difficulty + direction))
            if nuevo != self.difficulty:
                self._apply_difficulty(nuevo, announce=True)
            self.audio.play_sound("click")
        elif item == 3:  # Colorblind
            self.colorblind_mode = not self.colorblind_mode
            self.audio.play_sound("click")
