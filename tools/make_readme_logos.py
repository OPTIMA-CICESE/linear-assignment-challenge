#!/usr/bin/env python3
"""Genera versiones web de los logos para el README.

    python3 tools/make_readme_logos.py

Los logos originales estan pensados para pantallas oscuras (el de CICESE es
blanco), asi que para GitHub se recortan los margenes, se reescribe el
contenido claro en negro y se guardan en assets/logos/readme/ (transparentes,
listos para verse sobre el fondo blanco de la pagina).
"""
import os
from PIL import Image

ORIGENES = [
    ("OPTIMA2-N.png", "OPTIMA.png"),
    ("logo-cicese.png", "CICESE.png"),
    ("iee.png", "IEEE.png"),
]
ALTURA = 64
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(REPO, "assets", "logos", "readme")


def contenido_alfa(im):
    px = im.load()
    w, h = im.size
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if px[x, y][3] > 128:
                x0 = min(x0, x)
                y0 = min(y0, y)
                x1 = max(x1, x)
                y1 = max(y1, y)
    x0 = max(0, x0 - 1)
    y0 = max(0, y0 - 1)
    x1 = min(w - 1, x1 + 1)
    y1 = min(h - 1, y1 + 1)
    if x1 < x0 or y1 < y0:
        raise ValueError("imagen sin contenido opaco")
    return x0, y0, x1 + 1, y1 + 1


def color_medio(im):
    px = im.load()
    w, h = im.size
    rs = gs = bs = n = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b, a = px[x, y]
            if a > 128:
                rs += r
                gs += g
                bs += b
                n += 1
    return (rs / n, gs / n, bs / n, n)


def main():
    os.makedirs(DESTINO, exist_ok=True)
    for origen, salida in ORIGENES:
        ruta = os.path.join(REPO, "assets", "logos", origen)
        im = Image.open(ruta).convert("RGBA")
        caja = contenido_alfa(im)
        recortado = im.crop(caja)
        r, g, b, n = color_medio(recortado)
        if (r + g + b) / 3 > 200:          # contenido claro: reescribir en negro
            _, _, _, alfa = recortado.split()
            negro = alfa.point(lambda _: 0)
            recortado = Image.merge("RGBA", (negro, negro, negro, alfa))
            fuente = "blanco"
        else:
            fuente = "negro/color"
        escala = ALTURA / recortado.height
        nuevo = (max(4, int(recortado.width * escala)), ALTURA)
        recortado = recortado.resize(nuevo, Image.LANCZOS)
        destino = os.path.join(DESTINO, salida)
        recortado.save(destino)
        print(f"{salida}: {nuevo} (contenido {fuente}, {n} px opacos)")


if __name__ == "__main__":
    main()