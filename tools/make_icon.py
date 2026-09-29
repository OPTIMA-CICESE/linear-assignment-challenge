#!/usr/bin/env python3
"""Genera assets/icon.png y assets/icon.ico: icono de la app en pixel-art.

    python3 tools/make_icon.py

El PNG (16x16, escalado x16) es el icono de ventana y de la AppImage; el ICO
multi-tamano se incrusta en el ejecutable de Windows. No necesita pygame ni
Pillow: el icono son rectangulos de color y los archivos se escriben a mano.
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


def png_bytes(px, lado):
    """Codifica px (rejilla con tuplas RGBA) como PNG en memoria."""
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
    out = bytearray()
    out += b"\x89PNG\r\n\x1a\n"
    out += bloque(b"IHDR", ihdr)
    out += bloque(b"IDAT", zlib.compress(bytes(filas), 9))
    out += bloque(b"IEND", b"")
    return bytes(out)


def escribir_png(ruta, px, lado):
    """Escribe un PNG RGBA sin dependencias externas."""
    with open(ruta, "wb") as fh:
        fh.write(png_bytes(px, lado))


def escribir_ico(ruta, px_base, factor_base, tamanos=(16, 24, 32, 48, 64, 128, 256)):
    """ICO multi-tamano (entries PNG, soportado por Windows Vista en adelante).

    Reutiliza el diseno de 16x16: cada tamano se escala con vecino mas cercano
    recortando la rejilla, sin depender de Pillow ni de pygame.
    """
    bloques = {}
    for t in tamanos:
        if t <= 16:
            lado = 16
            desplaz = (16 - t) // 2
            rejilla = [fila[desplaz:desplaz + t] for fila in px_base]
            rejilla = rejilla[desplaz:desplaz + t]
        else:
            lado = t
            rejilla = [[px_base[y * 16 // t][x * 16 // t]
                        for x in range(t)] for y in range(t)]
        bloques[t] = png_bytes(rejilla, lado)

    entradas = bytearray()
    datos = bytearray()
    desplazamiento_total = 6 + 16 * len(tamanos)
    for t, blob in bloques.items():
        entradas += struct.pack(
            "<BBBBHHII", t if t < 256 else 0, t if t < 256 else 0,
            0, 0, 1, 32, len(blob), desplazamiento_total)
        datos += blob
        desplazamiento_total += len(blob)

    with open(ruta, "wb") as fh:
        fh.write(struct.pack("<HHH", 0, 1, len(tamanos)))
        fh.write(entradas)
        fh.write(datos)
    return sum(len(b) for b in bloques.values())


def main():
    px = lienzo()
    dibujar(px)
    lado, px = escalar(px, LADO, ESCALA)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    destino = os.path.join(raiz, "assets", "icon.png")
    escribir_png(destino, px, lado)
    opacos = sum(1 for fila in px for c in fila if c[3])
    print(f"Escrito {destino} ({lado}x{lado}, {opacos} pixeles con color)")
    ico = os.path.join(raiz, "assets", "icon.ico")
    bytes_ico = escribir_ico(ico, px, ESCALA)
    print(f"Escrito {ico} (multi-tamano, {bytes_ico} bytes de imagenes)")


if __name__ == "__main__":
    main()
