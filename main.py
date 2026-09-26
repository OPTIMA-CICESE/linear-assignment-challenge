#!/usr/bin/env python3
"""PC Repair Challenge — punto de entrada del juego.

    python3 main.py            jugar
    python3 main.py --test     autocomprobacion sin ventana
    ./main.py                  igual, si python3 esta en el PATH
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config as C


def _run_tests() -> int:
    """Ejecuta las suites del repositorio, o una comprobacion minima si el
    programa se ejecuto desde un binario empaquetado (sin carpeta tests/)."""
    tests_dir = os.path.join(ROOT, "tests")
    if os.path.isdir(tests_dir):
        for name in ("test_core.py", "smoke_test.py"):
            path = os.path.join(tests_dir, name)
            if not os.path.isfile(path):
                continue
            print(f"--- {name}", flush=True)
            result = subprocess.run([sys.executable, path])
            if result.returncode:
                return result.returncode
        return 0

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from game.engine import Game

    game = Game()
    for _ in range(30):
        game._update(1 / 60)
        game._render()
    game.running = False

    # Modo de dificultad: arranca en Normal y G va a ultra facil y vuelve.
    if game.difficulty != C.DIFFICULTY_NORMAL:
        print(f"MODO INICIAL MALO: {game.difficulty}", flush=True)
        return 1
    game._toggle_easy_mode()
    if game.difficulty != C.DIFFICULTY_ULTRA:
        print("LA TECLA G NO CAMBIA A ULTRA FACIL", flush=True)
        return 1
    game._toggle_easy_mode()
    if game.difficulty != C.DIFFICULTY_NORMAL:
        print("LA TECLA G NO VUELVE A NORMAL", flush=True)
        return 1
    gens = [C.ga_generations(lvl, d) for d, lvl in enumerate(C.LEVELS)]
    if any(gens[i] > gens[i + 1] for i in range(len(gens) - 1)):
        print("LOS MODOS NO ESTAN ORDENADOS POR DIFICULTAD", flush=True)
        return 1
    print(f"modos OK (por defecto {C.difficulty_name(C.DIFFICULTY_NORMAL)}, "
          f"ultra facil {C.ga_generations(C.LEVELS[0], C.DIFFICULTY_ULTRA)} "
          f"generaciones en el nivel 1)", flush=True)

    # En un binario empaquetado no hay tests/, pero los simbolos de la fuente
    # si se pueden comprobar: en Windows es justo lo que fallaba.
    faltan = C.missing_glyphs()
    if faltan:
        print("FALTAN SIMBOLOS EN LA FUENTE: "
              + " ".join(f"U+{ord(c):04X} {c}" for c in faltan), flush=True)
        return 1
    print(f"fuente OK ({C.FONT_PATH}), {len(C.GLYPHS)} simbolos dibujados", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PC Repair Challenge")
    parser.add_argument("--test", action="store_true",
                        help="ejecuta los tests y sale")
    args = parser.parse_args()

    if args.test:
        return _run_tests()

    from game.engine import Game

    Game().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
