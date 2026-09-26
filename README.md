# PC Repair Challenge

Juego educativo de pixel-art que enseña el **Problema de Asignación Lineal** (LAP).
El jugador repara computadoras asignando componentes, mientras compite contra
**PC PLAYER**, un algoritmo genético que busca la mejor asignación en vivo.

Proyecto del laboratorio [OPTIMA](https://www.cicese.edu.mx) para la Semana de Ciencias.

![Python](https://img.shields.io/badge/python-3.10%2B-4b8bbe)
![pygame](https://img.shields.io/badge/pygame--ce-4b8bbe)
![license](https://img.shields.io/badge/license-MIT-3cb371)

## El problema

Cada computadora requiere un porcentaje de reparación y cada componente aporta
un porcentaje distinto en cada una, por lo que la asignación de las piezas es
determinante.

- Cada computadora acepta **una sola** pieza.
- Superar el 100 % desperdicia capacidad y penaliza el puntaje.
- Gana quien deje más computadoras al 100 % con menos desperdicio.

No es necesario conocer ecuaciones: toda la información se transmite mediante
colores, barras, iconos y porcentajes.

## Requisitos

- Linux (probado en Ubuntu/Debian y Fedora)
- Python 3.10 o superior

Dependencias: `pygame-ce` y `numpy` (`scipy` es opcional, solo acelera el audio).
Están declaradas en `requirements.txt`.

## Instrucciones de juego

En Linux:

```bash
./run.sh
```

`run.sh` crea un entorno virtual en `.venv`, instala las dependencias que
falten y ejecuta el juego. Equivale a:

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
| `G` | alternar entre los modos ultra fácil y normal |
| `DEL` / `Retroceso` | deshacer la última asignación |
| flechas + `ENTER` | asignar sin arrastrar |

El botón **↶ Deshacer** se encuentra en la esquina inferior derecha de la
partida, de modo que todas las acciones pueden realizarse con el ratón. El
botón se atenúa cuando no hay ninguna asignación que deshacer.

Se puede asignar una pieza arrastrándola hasta la computadora, o seleccionándola
y eligiendo la computadora con el teclado. Cada computadora admite un único
componente: si ya tiene pieza, el socket no acepta otra.

## Quién gana

- Gana quien termine con mayor puntaje.
- **Si el jugador alcanza la misma solución que el algoritmo, también gana.**
- Si el jugador iguala o supera la mejor solución disponible del algoritmo en ese
  momento, la ronda se decide inmediatamente, sin esperar a que el GA termine.
  El resultado indica si el jugador llegó antes, superó al algoritmo o si ambos
  encontraron la misma solución.

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

El modo no proporciona al algoritmo una solución prefabricada: la búsqueda
continúa con recursos mucho menores. En el nivel 5 el GA alcanza el 92 % del
óptimo en el modo ultra fácil y el 93 % en el modo normal, de modo que un
jugador que asigna correctamente puede ganar en ambos casos.

Si el modo cambia mientras la ronda está en curso, el GA reduce su población y
su número de generaciones, y el tiempo restante se reescala en proporción. El
botón de deshacer, el tutorial y el resto de los controles no se modifican.

`tests/smoke_test.py` comprueba que la dificultad se inicialice en Normal, que
la tecla `G` alterne entre ambos modos, que los modos estén ordenados por
dificultad y que alcanzar la mejor solución antes que el GA cierre la ronda con
victoria.

## Ejecutable para Windows

El ejecutable de Windows requiere un equipo con Windows y Python instalado:

```bat
build_windows.bat
```

Alternativamente, la compilación puede ejecutarse desde GitHub Actions:

1. Publicar el proyecto en el repositorio.
2. Abrir la pestaña **Actions**, seleccionar el flujo **Windows** y ejecutar
   *Run workflow* (también se ejecuta automáticamente al publicar una etiqueta
   como `v1.0.0`).
3. Al finalizar, descargar `PCRepairChallenge-windows` y descomprimir el `.exe`.

El `.exe` no requiere Python ni ninguna instalación adicional en el equipo
destino.

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

Genera los archivos en `dist/linux/`:

| Archivo | Descripción |
|---|---|
| `pc-repair-challenge-linux-x86_64.tar.gz` | **paquete de distribución**: contiene la AppImage, `JUGAR.sh` y `LEEME.txt` |
| `pc-repair-challenge-x86_64.AppImage` | AppImage aislada, para usuarios que saben ejecutarla |
| `JUGAR.sh` | lanzador, situado junto a la AppImage para probarla sin descomprimir |
| `LEEME.txt` | instrucciones de instalación para la persona que recibe la carpeta |

En el equipo destino se descomprime el `.tar.gz` y se ejecuta:

```bash
chmod +x JUGAR.sh
./JUGAR.sh
```

`JUGAR.sh` intenta abrir la AppImage directamente y, si el sistema no dispone de
FUSE, la extrae una sola vez en el directorio de datos del usuario y utiliza esa
copia en las ejecuciones siguientes. También puede ejecutarse con doble clic
tras marcarlo como ejecutable.

Comprobación de la AppImage sin abrir la ventana del juego:

```bash
./JUGAR.sh --test
```

Compatible con Linux x86-64 de escritorio (Ubuntu, Debian, Fedora, Mint). El
script descarga sus herramientas a `.cache/` en la primera ejecución, por lo que
requiere `curl` y conexión a internet en esa ejecución. Para regenerar el icono:
`python3 tools/make_icon.py`.

## Pruebas

```bash
./run.sh --test        # equivalente a: python main.py --test
```

- `tests/test_core.py` — generador de problemas, puntuación y algoritmo genético.
  Solo biblioteca estándar, sin pygame.
- `tests/smoke_test.py` — ejecuta los cinco niveles de principio a fin de forma
  automática, verifica el renderizado, comprueba la cobertura de la fuente
  embebida y valida los modos de dificultad.

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
