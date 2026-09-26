#!/usr/bin/env bash
# Lanzador del juego para Linux. No requiere Python ni FUSE.
#
#   ./JUGAR.sh
#
# Que hace:
#   1. Intenta ejecutar la AppImage directamente.
#   2. Si el sistema no tiene FUSE, la extrae en la carpeta de datos del
#      usuario y ejecuta el binario de dentro. La extraccion se guarda, asi
#      que las siguientes veces abre al instante.

set -u

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPIMAGE="$AQUI/pc-repair-challenge-x86_64.AppImage"
CARPETA="${XDG_DATA_HOME:-$HOME/.local/share}/pc-repair-challenge"

if [ ! -f "$APPIMAGE" ]; then
    echo "No se encuentra pc-repair-challenge-x86_64.AppImage junto a este script." >&2
    exit 1
fi

chmod +x "$APPIMAGE" 2>/dev/null || true

# Intento 1: ejecucion directa, que es la mas rapida. Necesita FUSE.
if [ -e /dev/fuse ] && "$APPIMAGE" "$@" 2>/dev/null; then
    exit 0
fi

# Intento 2: sin FUSE, se extrae una vez y se ejecuta el binario de dentro.
# La copia se guarda, asi que las siguientes veces abre al instante.
if [ ! -x "$CARPETA/squashfs-root/AppRun" ]; then
    echo "Sin FUSE: se extrae el juego en $CARPETA (solo la primera vez) ..."
    mkdir -p "$CARPETA"
    rm -rf "$CARPETA/squashfs-root"
    (cd "$CARPETA" && "$APPIMAGE" --appimage-extract) || {
        echo "No se pudo extraer la AppImage." >&2
        exit 1
    }
fi

exec "$CARPETA/squashfs-root/AppRun" "$@"
