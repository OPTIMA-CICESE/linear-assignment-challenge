import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import config as C
from game.states import State
from game.engine import Game

pygame.init()


def drive_assign(game):
    """Assign the remaining components via keyboard flow (no AI finish)."""
    n = game.problem.num_components
    assigned = 0
    for _ in range(n * 2):
        if game.selected_component < 0:
            break
        if game.state == State.PLAYING:
            game._handle_key(pygame.K_RETURN)
        if game.state == State.SELECT_COMPUTER:
            # asignar a una PC libre distinta por pieza (LAP uno-a-uno)
            pc = assigned % game.problem.num_computers
            game._handle_key(pygame.K_1 + pc)
            assigned += 1
        if game.state == State.PLAYING:
            continue
        else:
            break
    return game.state in (State.PLAYING, State.SELECT_COMPUTER, State.DRAGGING)


def test_level(level_idx, steps=40):
    g = Game()
    # tutorial -> skip
    g._handle_key(pygame.K_ESCAPE)
    assert g.state == State.MENU, f"state after skip={g.state}"

    # menu -> level select
    g.menu_cursor = 1
    g._handle_key(pygame.K_RETURN)
    assert g.state == State.LEVEL_SELECT, f"menu_action state={g.state}"

    # start level
    g.level_cursor = level_idx
    g.current_level = level_idx
    g._start_game(level_idx)
    assert g.state == State.PLAYING, f"start_game state={g.state}"

    # render every state a few times + update (catches text crashes)
    for _ in range(steps):
        g._update(0.05)
        g._render()

    # assign all components
    drive_assign(g)
    for _ in range(steps):
        g._update(0.05)
        g._render()

    # wait for AI to finish -> result
    guard = 0
    while g.state != State.RESULT and guard < 4000:
        g._update(0.05)
        g._render()
        guard += 1
    assert g.state == State.RESULT, f"never reached result, state={g.state}"
    for _ in range(5):
        g._render()
    print(f"  level {level_idx} '{C.LEVELS[level_idx]['name']}' -> {g.result_text} OK")
    # keep audio alive until end to avoid 'mixer not initialized' at exit noise


def test_modos_de_dificultad():
    """La dificultad arranca en Normal y la tecla G va a Ultra facil y vuelve."""
    g = Game()
    g._handle_key(pygame.K_ESCAPE)  # saltar tutorial
    assert g.difficulty == C.DIFFICULTY_NORMAL, "el modo por defecto debe ser Normal"
    assert g.difficulty_names[g.difficulty] == "Normal"

    # Mas dificultad = mas busqueda del GA y menos tiempo
    gens = [C.ga_generations(C.LEVELS[4], d) for d in range(len(C.DIFFICULTIES))]
    pops = [C.ga_population(C.LEVELS[4], d) for d in range(len(C.DIFFICULTIES))]
    times = [C.difficulty_time_mult(d) for d in range(len(C.DIFFICULTIES))]
    assert gens == sorted(gens) and gens[0] < gens[-1], f"generaciones: {gens}"
    assert pops == sorted(pops) and pops[0] < pops[-1], f"poblaciones: {pops}"
    assert times == sorted(times, reverse=True), f"tiempos: {times}"
    # Ultra facil: el GA sigue buscando, pero muy pocas generaciones
    assert 0 < gens[0] <= 6, f"ultra facil con demasiadas generaciones: {gens[0]}"

    # G alterna Normal <-> Ultra facil
    g._toggle_easy_mode()
    assert g.difficulty == C.DIFFICULTY_ULTRA
    assert g.mode_toast and "Ultra fácil" in g.mode_toast[0]
    g._toggle_easy_mode()
    assert g.difficulty == C.DIFFICULTY_NORMAL
    assert g.mode_toast and "Normal" in g.mode_toast[0]
    pygame.quit()


def test_llegar_primero_gana():
    """Si el jugador iguala la mejor solucion actual del GA, gana ya."""
    g = Game()
    g._handle_key(pygame.K_ESCAPE)
    g._start_game(4)
    g.ai_ga.step()
    best = g.ai_ga.get_best()
    # Puntaje igual al mejor del GA: la carrera ya esta ganada
    g.player_assignment = list(best.assignment)
    g.player_score = best
    g.ai_steps_done = 0
    assert g.ai_steps_done < g.ai_total_steps, "el GA deberia seguir pensando"
    assert g._player_already_best() is True
    # Puntaje claramente menor: todavia no gana
    peor = best.__class__(assignment=list(best.assignment), score=0.0,
                          requirement_met=0, efficiency=0.0, waste=0.0)
    g.player_score = peor
    assert g._player_already_best() is False
    pygame.quit()


def test_ganar_llegando_primero():
    """Jugando la asignacion optima se gana ANTES de que el GA termine."""
    import itertools
    from core.scoring import ScoringSystem
    g = Game()
    g._handle_key(pygame.K_ESCAPE)   # tutorial -> menu
    g._toggle_easy_mode()             # modo ultra facil
    g._start_game(0)
    p = g.problem
    mejor, mejor_score = None, -1.0
    for perm in itertools.permutations(range(p.num_computers)):
        s = ScoringSystem.evaluate(p, list(perm)).score
        if s > mejor_score:
            mejor, mejor_score = list(perm), s
    g.ai_total_steps = 999  # el GA no termina: solo se gana llegando antes
    g.ai_steps_done = 0
    for comp, pc in enumerate(mejor):
        g._handle_key(pygame.K_RETURN)      # elegir pieza
        g._handle_key(pygame.K_1 + pc)     # elegir computadora
    assert g.state == State.RESULT, f"state={g.state}"
    assert g.result_text == "¡Victoria!", g.result_text
    assert g.early_win is True, "debe contar como llegar antes"
    assert g.result_reason == "Llegaste antes que el algoritmo", g.result_reason
    pygame.quit()


def test_font_cubre_los_simbolos():
    """Ningun simbolo del juego puede quedar como cuadradito.

    En Windows la fuente del sistema (Arial) no trae check, cruz ni triangulos,
    y el juego se quedaba con simbolos invisibles en el menu. La fuente de
    assets/fonts/ viene empaquetada justamente para evitarlo.
    """
    fuente = C.FONT_PATH
    assert fuente and os.path.exists(fuente), "no se encontro la fuente del juego"

    # 1) Los simbolos que el juego dibuja explicitamente.
    simbolos = "\u2713\u2717\u2715\u2192\u2190\u2191\u2193\u25bc\u25b2\u25b6\u25c9"
    simbolos += "\u2630\u2699\u2726\u266a\u266b\u26a1\u25a0"

    # 2) Todo lo que aparece en el codigo, para que un emoji nuevo no se cuele.
    for carpeta, subcarpetas, archivos in os.walk(ROOT):
        subcarpetas[:] = [c for c in subcarpetas if c not in (".venv", "build", "dist", ".cache")]
        for archivo in archivos:
            if not archivo.endswith(".py"):
                continue
            with open(os.path.join(carpeta, archivo), encoding="utf-8") as fh:
                simbolos += fh.read()

    faltan = C.missing_glyphs(simbolos)
    assert not faltan, (
        "la fuente no tiene estos glifos: "
        + " ".join(f"U+{ord(c):04X} {c}" for c in faltan)
    )
    print("  fuente y simbolos OK")


if __name__ == "__main__":
    ok = True
    try:
        for li in range(len(C.LEVELS)):
            try:
                test_level(li)
            except Exception as e:
                ok = False
                import traceback
                print(f"  level {li} FAILED: {e}")
                traceback.print_exc()
        try:
            test_modos_de_dificultad()
        except Exception as e:
            ok = False
            import traceback
            print(f"  modos FAILED: {e}")
            traceback.print_exc()
        try:
            test_llegar_primero_gana()
        except Exception as e:
            ok = False
            import traceback
            print(f"  llegar primero FAILED: {e}")
            traceback.print_exc()
        try:
            test_ganar_llegando_primero()
        except Exception as e:
            ok = False
            import traceback
            print(f"  ganar primero FAILED: {e}")
            traceback.print_exc()
        try:
            test_font_cubre_los_simbolos()
        except Exception as e:
            ok = False
            import traceback
            print(f"  font check FAILED: {e}")
            traceback.print_exc()
    finally:
        pygame.quit()
    print("ALL OK" if ok else "SOME FAILED")
