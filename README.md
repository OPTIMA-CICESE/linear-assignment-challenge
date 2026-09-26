# PC Repair Challenge

Juego educativo de pixel-art que enseña el **Problema de Asignación Lineal** (LAP).
El jugador repara computadoras asignando componentes, mientras compite contra
**PC PLAYER**, un algoritmo genético que busca la mejor asignación en vivo.

Proyecto del laboratorio [OPTIMA](https://www.cicese.edu.mx) para la Semana de Ciencias.

![Python](https://img.shields.io/badge/python-3.10%2B-4b8bbe)
![pygame](https://img.shields.io/badge/pygame--ce-4b8bbe)
![license](https://img.shields.io/badge/license-MIT-3cb371)

## El problema, en simple

Cada computadora pide un porcentaje de reparación y cada componente aporta un
porcentaje distinto en cada una, así que la ubicación importa.

- Cada computadora acepta **una sola** pieza.
- Pasarse del 100 % desperdicia capacidad y penaliza.
- Gana quien deje más computadoras al 100 % con menos desperdicio.

No hace falta saber ecuaciones: todo se comunica con colores, barras, iconos y
porcentajes.

## Requisitos

- Linux (probado en Ubuntu/Debian y Fedora)
- Python 3.10 o superior

Dependencias: `pygame-ce` y `numpy` (`scipy` es opcional, solo acelera el audio).
Están declaradas en `requirements.txt`.

## Cómo jugar

La forma más simple en Linux:

```bash
./run.sh
```

`run.sh` crea un entorno virtual en `.venv`, instala lo que falte y arranca el
juego. Equivale a:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Controles:

| Tecla | Acción |
|---|---|
| `F11` | pantalla completa |
| `ESC` | menú |
| `M` | activar o silenciar el sonido |
| `G` | modo ultra fácil / normal, al instante |
| `DEL` / `Retroceso` | deshacer la última asignación |
| flechas + `ENTER` | asignar sin arrastrar |

También hay un botón **↶ Deshacer** en la parte inferior derecha de la
partida, así que todo se puede hacer solo con el ratón. Se atenúa cuando no
hay nada que deshacer.

Se puede asignar una pieza arrastrándola hasta la computadora, o seleccionándola
y eligiendo la computadora con el teclado. Cada computadora admite un único
componente: si ya tiene pieza, el socket no acepta otra.

## Quién gana

- Gana quien termine con mayor puntaje.
- **Si el jugador llega a la misma solución que el algoritmo, también gana.**
- Si el jugador iguala o supera la mejor solución que el algoritmo tiene en ese
  momento, la ronda se decide ahí mismo: no hace falta esperar a que el GA
  termine. El resultado indica si llegaste antes, si superaste al algoritmo o si
  los dos encontraron la misma solución.

## Modos de dificultad

El modo por defecto es **Normal**. En *Ajustes* se pueden elegir los cuatro, y
la tecla `G` alterna al instante entre **Ultra fácil** y **Normal** (funciona en
cualquier pantalla, incluso con la ronda en marcha).

| Modo | Población | Generaciones | Tiempo |
|---|---|---|---|
| Ultra fácil | 35 % | 12 % (mínimo 3) | 220 % |
| Fácil | 70 % | 60 % | 150 % |
| Normal | 100 % | 100 % | 100 % |
| Difícil | 125 % | 130 % | 60 % |

El modo no le da al algoritmo una respuesta prefabricada: sigue buscando de
verdad, solo que con muchos menos recursos. En el nivel 5 el GA llega al 92 % del
óptimo en ultra fácil y al 93 % en normal, así que un jugador que asigna bien
puede ganar en los dos casos.

Si cambias de modo con la ronda en marcha, el GA que ya está corriendo recorta su
población y su número de generaciones, y el tiempo restante se reescala en
proporción. El botón de deshacer, el tutorial y las teclas siguen igual.

Tests: `tests/smoke_test.py` comprueba que la dificultad arranque en Normal, que
`G` va y vuelve, que los modos están ordenados por dificultad y que ganar al
llegar antes cierra la ronda con victoria.

## Ejecutable para Windows

Un `.exe` de Windows no se puede compilar en Linux, así que hay dos caminos:

```bat
:: En una PC con Windows y Python instalado: doble clic en
build_windows.bat
```

O bien, sin tocar ninguna PC, desde GitHub:

1. Sube el proyecto al repositorio.
2. Ve a la pestaña **Actions**, elige el flujo **Windows** y pulsa *Run workflow*
   (también se ejecuta solo al publicar un tag `v1.0.0`, por ejemplo).
3. Al terminar, descarga `PCRepairChallenge-windows` y descomprime el `.exe`.

El `.exe` no necesita Python ni nada instalado en la PC destino.

Los dos ejecutables quedan ordenados por sistema operativo:

```
dist/
  linux/     AppImage, .tar.gz, JUGAR.sh, LEEME.txt
  windows/   PCRepairChallenge.exe
```

## Ejecutable para Linux

```bash
./build_appimage.sh
```

Deja las cosas en `dist/linux/`:

| Archivo | Para que sirve |
|---|---|
| `pc-repair-challenge-linux-x86_64.tar.gz` | **el que se reparte**: carpeta con la AppImage, `JUGAR.sh` y `LEEME.txt` |
| `pc-repair-challenge-x86_64.AppImage` | la AppImage sola, para quien ya sabe ejecutarla |
| `JUGAR.sh` | lanzador, ya junto a la AppImage para probar sin descomprimir |
| `LEEME.txt` | instrucciones para quien recibe la carpeta |

En la computadora destino se descomprime el `.tar.gz` y se ejecuta:

```bash
chmod +x JUGAR.sh
./JUGAR.sh
```

`JUGAR.sh` intenta abrir la AppImage directamente y, si el sistema no tiene
FUSE, la extrae una sola vez en la carpeta de datos del usuario y usa esa copia
en los siguientes inicios. También funciona con doble clic después de marcarlo
como ejecutable.

Comprobación rápida de la AppImage, sin abrir la ventana del juego:

```bash
./JUGAR.sh --test
```

Funciona en Linux x86-64 de escritorio (Ubuntu, Debian, Fedora, Mint...). El
script descarga sus herramientas a `.cache/` la primera vez, así que hace falta
`curl` y conexión en esa primera ejecución. Para regenerar el icono:
`python3 tools/make_icon.py`.

## Tests

```bash
./run.sh --test        # o: python main.py --test
```

- `tests/test_core.py` — generador de problemas, puntuación y algoritmo genético.
  Solo biblioteca estándar, sin pygame.
- `tests/smoke_test.py` — juega los cinco niveles de principio a fin en modo
  automático y verifica que el render no falle.

## Estructura

```
core/        problema de asignación y puntuación (sin dependencias de UI)
algorithm/   algoritmo genético (determinista con semilla)
game/        motor, estados, renderizado y tutorial
assets/      sprites de pixel-art y logos
ui/          efectos de pantalla: partículas, transiciones
audio/       música y efectos sintetizados
tests/       pruebas del núcleo y prueba de humo
```

`core/` y `algorithm/` no importan pygame: son verificables por separado y
aceptan una semilla aleatoria para reproducir exactamente los mismos
resultados.

## Licencia

MIT. Ver [LICENSE](LICENSE).
