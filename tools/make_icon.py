#!/usr/bin/env python3
"""Genera assets/icon.png: icono de la app en pixel-art (16x16, escalado x16).

    python3 tools/make_icon.py

No necesita pygame ni Pillow: el icono son rectangulos de color y el PNG se
escribe a mano.
"""
import os
import struct
import zlib

TRANSPARENTE = (0, 0, 0, 0)
BORDE = (68, 68, 75, 255)        # carcasa del monitor
CUERPO = (36, 36, 48, 255)
PANTALLA = (212, 74, 75, 255)    # pantalla dañada
GRIETA = (168, 58, 58, 255)
SOCKET = (250, 200, 80, 255)     # pieza colocada
BRILLO = (240, 240, 255, 255)

LADO = 16
ESCALA = 16


def lienzo():
    return [[TRANSPARENTE] * LADO for _ in range(LADO)]


def rect(px, x, y, w, h, color):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < LADO and 0 <= yy < LADO:
                px[yy][xx] = color


def marco(px, x, y, w, h, color, grosor=1):
    rect(px, x, y, w, grosor, color)
    rect(px, x, y + h - grosor, w, grosor, color)
    rect(px, x, y, grosor, h, color)
    rect(px, x + w - grosor, y, grosor, h, color)


def dibujar(px):
    # Monitor
    rect(px, 2, 1, 12, 12, CUERPO)
    marco(px, 2, 1, 12, 12, BORDE)
    # Pantalla rota
    rect(px, 4, 3, 8, 8, PANTALLA)
    for x, y in ((5, 4), (6, 5), (7, 6), (8, 7), (9, 8), (7, 5), (8, 6)):
        px[y][x] = GRIETA
    px[4][5] = BRILLO
    # Socket con la pieza puesta
    rect(px, 6, 11, 3, 1, SOCKET)
    # Pedestal
    rect(px, 5, 13, 6, 1, BORDE)
    rect(px, 6, 14, 4, 1, BORDE)
    rect(px, 4, 15, 8, 1, BORDE)


def escalar(px, lado, factor):
    """Rejilla pixel-art -> imagen grande con vecino mas cercano (nada de blur)."""
    grande = lado * factor
    out = [[px[y // factor][x // factor] for x in range(grande)]
           for y in range(grande)]
    return grande, out


def escribir_png(ruta, px, lado):
    """Escribe un PNG RGBA sin dependencias externas."""
    filas = bytearray()
    for y in range(lado):
        filas.append(0)                      # filtro "None"
        for x in range(lado):
            filas += bytes(px[y][x])

    def bloque(tipo, datos):
        crc = zlib.crc32(tipo + datos) & 0xFFFFFFFF
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", crc))

    esperado = lado * (1 + lado * 4)
    if len(filas) != esperado:
        raise AssertionError(
            f"pixeles {len(filas)}, se esperaban {esperado} para {lado}x{lado}")

    ihdr = struct.pack(">IIBBBBB", lado, lado, 8, 6, 0, 0, 0)
    with open(ruta, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(bloque(b"IHDR", ihdr))
        fh.write(bloque(b"IDAT", zlib.compress(bytes(filas), 9)))
        fh.write(bloque(b"IEND", b""))


def main():
    px = lienzo()
    dibujar(px)
    lado, px = escalar(px, LADO, ESCALA)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    destino = os.path.join(raiz, "assets", "icon.png")
    escribir_png(destino, px, lado)
    opacos = sum(1 for fila in px for c in fila if c[3])
    print(f"Escrito {destino} ({lado}x{lado}, {opacos} pixeles con color)")


if __name__ == "__main__":
    main()
