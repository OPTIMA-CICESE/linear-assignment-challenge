#!/usr/bin/env bash
# Genera un AppImage de PC Repair Challenge: un unico archivo que se ejecuta
# en Linux sin instalar Python, pygame ni nada mas.
#
#   ./build_appimage.sh
#   -> dist/linux/pc-repair-challenge-x86_64.AppImage
#   -> dist/linux/pc-repair-challenge-linux-x86_64.tar.gz
#
# Herramientas usadas (se descargan una vez a .cache/):
#   PyInstaller    empaqueta Python + juego
#   linuxdeploy    opcional (WITH_LINUXDEPLOY=1): anade OpenGL, ALSA...
#   appimagetool   convierte la carpeta AppDir en el AppImage final

set -euo pipefail

NAME="pc-repair-challenge"
ARCH="x86_64"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
CACHE="$DIR/.cache"
BUILD="$DIR/build"
APPDIR="$BUILD/AppDir"
DIST="$DIR/dist/linux"
PY="${PYTHON:-python3}"

cd "$DIR"
mkdir -p "$CACHE" "$DIST"

# ── 1. Entorno y dependencias ─────────────────────────────
if [ ! -d "$VENV" ]; then
    echo "Creando entorno virtual en .venv ..."
    "$PY" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python -m pip install --quiet pyinstaller

# ── 2. Icono ──────────────────────────────────────────────
python tools/make_icon.py

# ── 3. Empaquetar con PyInstaller ─────────────────────────
echo "Limpiando compilaciones previas ..."
rm -rf "$BUILD/onedir" "$BUILD/work" "$APPDIR" "$BUILD/$NAME.spec"
rm -f "$DIST/$NAME-$ARCH.AppImage"

echo "Compilando con PyInstaller ..."
# Las salidas intermedias van a build/ para no mezclarse con dist/, donde solo
# debe quedar el AppImage final.
pyinstaller --noconfirm --onedir --windowed --name "$NAME" \
    --distpath "$BUILD/onedir" --workpath "$BUILD/work" --specpath "$BUILD" \
    --add-data "$DIR/assets/logos:assets/logos" \
    --add-data "$DIR/assets/icon.png:assets" \
    --add-data "$DIR/assets/fonts:assets/fonts" \
    main.py >/dev/null

# ── 4. Montar el AppDir ───────────────────────────────────
echo "Montando AppDir ..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib"
# OJO: con --onedir la app completa queda en <distpath>/<nombre> (los archivos
# de build/ son solo intermedios).
cp -r "$BUILD/onedir/$NAME/." "$APPDIR/usr/bin/"
cp assets/icon.png "$APPDIR/$NAME.png"

cat > "$APPDIR/$NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=PC Repair Challenge
Name[es]=PC Repair Challenge
Comment=Juego educativo del Problema de Asignación Lineal
Exec=$NAME
Icon=$NAME
Categories=Game;Education;
Terminal=false
EOF

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
# Punto de entrada del AppImage.
HERE="$(dirname "$(readlink -f "$0")")"
# Las librerias extra que trae la app (OpenGL, ALSA...) viven en usr/lib.
LD_LIBRARY_PATH="$HERE/usr/lib:${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH
exec "$HERE/usr/bin/pc-repair-challenge" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# ── 5. Anadir librerias del sistema ───────────────────────
# linuxdeploy se usa solo para las librerias: si falla (no siempre funciona
# en distribuciones recientes) se continua, la app ya trae todo lo de Python.
if [ ! -x "$CACHE/linuxdeploy.AppImage" ]; then
    echo "Descargando linuxdeploy ..."
    curl -fsSL -o "$CACHE/linuxdeploy.AppImage" \
        "https://github.com/linuxdeploy/linuxdeploy/releases/download/1-alpha-20240109-1/linuxdeploy-$ARCH.AppImage" || true
    [ -f "$CACHE/linuxdeploy.AppImage" ] && chmod +x "$CACHE/linuxdeploy.AppImage" || rm -f "$CACHE/linuxdeploy.AppImage"
fi

# Opcional: WITH_LINUXDEPLOY=1 ./build_appimage.sh
# Linuxdeploy es fragil en distribuciones recientes, asi que va apagado: la
# app ya trae Python, pygame y numpy, y usa del sistema solo las librerias de
# graficos y audio, que existen en cualquier escritorio Linux.
if [ "${WITH_LINUXDEPLOY:-0}" = "1" ]; then
    if [ ! -x "$CACHE/linuxdeploy.AppImage" ]; then
        echo "Descargando linuxdeploy ..."
        curl -fsSL -o "$CACHE/linuxdeploy.AppImage" \
            "https://github.com/linuxdeploy/linuxdeploy/releases/download/1-alpha-20240109-1/linuxdeploy-$ARCH.AppImage" || true
        [ -f "$CACHE/linuxdeploy.AppImage" ] && chmod +x "$CACHE/linuxdeploy.AppImage" || rm -f "$CACHE/linuxdeploy.AppImage"
    fi
    if [ -x "$CACHE/linuxdeploy.AppImage" ]; then
        echo "Empaquetando librerias del sistema (linuxdeploy) ..."
        "$CACHE/linuxdeploy.AppImage" --appimage-extract-and-run \
            -d "$APPDIR" "$APPDIR/usr/bin/$NAME" || \
            echo "Aviso: linuxdeploy fallo; se continua sin librerias extra."
    fi
fi

# ── 6. Construir el AppImage ──────────────────────────────
if [ ! -x "$CACHE/appimagetool.AppImage" ]; then
    echo "Descargando appimagetool ..."
    curl -fsSL -o "$CACHE/appimagetool.AppImage" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
    chmod +x "$CACHE/appimagetool.AppImage"
fi

echo "Construyendo AppImage ..."
ARCH="$ARCH" "$CACHE/appimagetool.AppImage" --appimage-extract-and-run \
    "$APPDIR" "$DIST/$NAME-$ARCH.AppImage" >/dev/null
chmod +x "$DIST/$NAME-$ARCH.AppImage"

# ── 7. Paquete listo para repartir ─────────────────────────
# Un tar.gz con la AppImage y el lanzador: en una PC sin FUSE se abre con
# JUGAR.sh, sin depender de la terminal.
PAQUETE="$DIST/$NAME-linux-x86_64.tar.gz"
rm -rf "$BUILD/paquete"
mkdir -p "$BUILD/paquete"
cp "$DIST/$NAME-$ARCH.AppImage" "$BUILD/paquete/"
cp "$DIR/JUGAR.sh" "$BUILD/paquete/"

cat > "$BUILD/paquete/LEEME.txt" <<'LEEME'
PC Repair Challenge - version para Linux
=======================================

Como jugar
----------
1. Copia esta carpeta completa a la computadora.
2. Abre una terminal dentro de la carpeta y ejecuta:

       chmod +x JUGAR.sh
       ./JUGAR.sh

3. Listo. No hay que instalar Python ni ningun otro programa.

Con doble clic
--------------
1. Clic derecho sobre JUGAR.sh > "Permitir ejecutar" (o "Ejecutar como programa").
2. Despues, doble clic sobre JUGAR.sh.

Requerimientos
--------------
Linux de 64 bits (Ubuntu, Debian, Fedora, Mint, elementary...).

Atajos
------
F11  pantalla completa
ESC  menu
M    activar o silenciar el sonido
DEL  deshacer la ultima asignacion
LEEME

tar -czf "$PAQUETE" -C "$BUILD/paquete" .

# La carpeta de distribucion queda lista para usar sin desempaquetar nada:
# la AppImage, el lanzador y las instrucciones, todo junto.
cp "$BUILD/paquete/LEEME.txt" "$DIST/"
rm -rf "$BUILD/paquete"

echo
echo "Listo: dist/linux/$NAME-$ARCH.AppImage"
echo "Listo: dist/linux/$NAME-linux-x86_64.tar.gz"
ls -lh "$DIST/$NAME-$ARCH.AppImage" "$PAQUETE" | awk '{print "  Tamano:", $5, $NF}'
echo
echo "Probar   : dist/linux/JUGAR.sh --test"
echo "Repartir : dist/linux/$NAME-linux-x86_64.tar.gz"
