#!/usr/bin/env bash
# Lanzador de PC Repair Challenge para Linux.
# Crea un entorno virtual la primera vez, instala las dependencias y arranca el juego.
#
#   ./run.sh            jugar
#   ./run.sh --test     correr los tests
#   ./run.sh --clean    borrar el entorno virtual y empezar de cero

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
PY="${PYTHON:-python3}"

if [ "${1:-}" = "--clean" ]; then
    echo "Borrando $VENV"
    rm -rf "$VENV"
    exit 0
fi

if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Error: no se encontro $PY. Instala Python 3.10 o superior." >&2
    echo "  Debian/Ubuntu : sudo apt install python3 python3-venv" >&2
    echo "  Fedora        : sudo dnf install python3" >&2
    exit 1
fi

if [ ! -d "$VENV" ]; then
    echo "Creando entorno virtual en .venv ..."
    "$PY" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

if [ ! -f "$VENV/.deps-ok" ]; then
    echo "Instalando dependencias ..."
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r "$DIR/requirements.txt"
    touch "$VENV/.deps-ok"
fi

cd "$DIR"

case "${1:-}" in
    --test)
        python tests/test_core.py
        python tests/smoke_test.py
        ;;
    *)
        exec python main.py
        ;;
esac
