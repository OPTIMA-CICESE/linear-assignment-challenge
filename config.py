"""
Game configuration — resolution, palette, timings and levels.
"""
import os
import sys
import pygame

# ── Resolution ────────────────────────────────────────────
LOGICAL_W = 480
LOGICAL_H = 270
SCALE = 3
WINDOW_W = LOGICAL_W * SCALE
WINDOW_H = LOGICAL_H * SCALE
FPS = 60
TITLE = "PC REPAIR CHALLENGE"


# ── Font ──────────────────────────────────────────────────
# La fuente viaja dentro de assets/ para que el texto se vea igual en Linux y
# en Windows. Sin esto, Windows cae en Arial y los simbolos (check, cruz,
# flechas, triangulos) salian como cuadritos vacios.
def _base_dir() -> str:
    """Carpeta del proyecto, o la carpeta temporal del ejecutable empaquetado."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


_FONT_PATHS = [
    os.path.join(_base_dir(), "assets", "fonts", "DejaVuSans.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/croscore/Arimo-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]
FONT_PATH = None
for _p in _FONT_PATHS:
    if os.path.exists(_p):
        FONT_PATH = _p
        break


def _make_font(size):
    if FONT_PATH:
        return pygame.font.Font(FONT_PATH, size)
    return pygame.font.Font(None, size)


# Simbolos que el juego dibuja en pantalla. Todos tienen que existir en la fuente
# o en Windows el menu sale con huecos.
GLYPHS = (
    "✓✗✕→←↑↓▼▲▶◉☰⚙✦♪♫⚡■"   # check, cruz, flechas, triangulos, engranaje
)


def missing_glyphs(text: str = GLYPHS, size: int = 16):
    """Caracteres de `text` que la fuente del juego no puede dibujar.

    Se usa en las pruebas y en el `--test` de los ejecutables ya empaquetados,
    para detectar en la misma PC si un simbolo se quedaria invisible.
    """
    if not FONT_PATH:
        return []
    if not pygame.font.get_init():
        pygame.font.init()
    font = _make_font(size)
    faltan = []
    for ch in sorted(set(text)):
        if ord(ch) < 128:
            continue
        if font.metrics(ch)[0] is None:
            faltan.append(ch)
    return faltan


# ── Timing ────────────────────────────────────────────────
TIE_THRESHOLD = 0
AI_STEP_DELAY = 0.4

# ── Difficulty modes ─────────────────────────────────────
# Cada modo escala el presupuesto de busqueda del GA (poblacion x generaciones)
# y el tiempo disponible. El indice 2 (Normal) es el de arranque.
#   nombre, mult_poblacion, mult_generaciones, min_generaciones, mult_tiempo
DIFFICULTIES = [
    ("Ultra fácil", 0.35, 0.12, 3, 2.2),
    ("Fácil",       0.70, 0.60, 8, 1.5),
    ("Normal",      1.00, 1.00, 0, 1.0),
    ("Difícil",     1.25, 1.30, 0, 0.6),
]
DIFFICULTY_NORMAL = 2
DIFFICULTY_ULTRA = 0


def _clamp_diff(idx):
    return max(0, min(len(DIFFICULTIES) - 1, int(idx)))


def difficulty_name(idx):
    return DIFFICULTIES[_clamp_diff(idx)][0]


def difficulty_time_mult(idx):
    return DIFFICULTIES[_clamp_diff(idx)][4]


def ga_population(level_cfg, idx):
    """Poblacion inicial del GA segun el modo de dificultad."""
    mult = DIFFICULTIES[_clamp_diff(idx)][1]
    return max(6, int(round(level_cfg["ai_pop"] * mult)))


def ga_generations(level_cfg, idx):
    """Generaciones maximas del GA segun el modo de dificultad.

    En modo ultra facil el algoritmo sigue buscando de verdad, pero con muy
    pocas generaciones: es un GA debil, no una solucion prefabricada.
    """
    _, _pm, gmult, floor, _tm = DIFFICULTIES[_clamp_diff(idx)]
    return max(floor, int(round(level_cfg["ai_gen"] * gmult)))


def ga_step_delay(idx):
    """Segundos entre generaciones. Un GA mas debil tambien piensa mas lento."""
    gmult = DIFFICULTIES[_clamp_diff(idx)][2]
    return AI_STEP_DELAY * (2.0 - gmult)

# ── Bright child-friendly palette ────────────────────────
C_BG           = (30,  30,  60)
C_BG_LIGHT     = (50,  50,  85)
C_PANEL_BOT    = (40,  40,  72)
C_BORDER        = (90,  90, 140)
C_BORDER_LIGHT  = (130, 130, 200)

C_WHITE    = (255, 255, 255)
C_BLACK    = (0,   0,   0)
C_TITLE    = (110, 210, 255)
C_SUBTITLE = (190, 190, 220)
C_DIM      = (100, 100, 140)

# ── Character colors ──────────────────────────────────────
C_SKIN       = (255, 210, 165)
C_SKIN_SH    = (225, 175, 130)
C_EYES       = (25,  25,  45)
C_MOUTH      = (200, 120, 100)

C_HAIR_BROWN = (120,  65,  35)
C_HAIR_BLACK = (35,   35,  40)
C_HAIR_BLOND = (235, 195,  85)
C_HAIR_RED   = (180,  60,  30)

C_SHIRT_BLUE   = (70,  140, 220)
C_SHIRT_GREEN  = (65,  190, 105)
C_SHIRT_ORANGE = (235, 150,  55)
C_SHIRT_PURPLE = (160,  90, 210)

C_PANTS  = (55,  55,  95)
C_SHOES  = (75,  55,  45)

# ── Computer colors ───────────────────────────────────────
C_MONITOR      = (65,  65,  90)
C_MONITOR_BEZ  = (45,  45,  65)
C_SCREEN_DMG   = (90,  35,  35)
C_SCREEN_WARN  = (120, 80,  30)
C_SCREEN_REPAIR= (65,  65,  90)
C_SCREEN_OK    = (35, 100,  55)
C_SCREEN_BRIGHT= (55, 210, 110)
C_STAND        = (55,  55,  72)
C_BASE         = (50,  50,  68)
C_SMOKE        = (80,  80, 100)

# ── Component colors ──────────────────────────────────────
C_CPU = (190, 190, 210)
C_GPU = (110, 170,  85)
C_RAM = (85,  190, 170)
C_SSD = (190, 170,  65)
C_PSU = (170, 110,  65)
C_AIO = (170, 210, 240)
C_MB  = (65,  130,  65)
C_NET = (90,  200, 255)
C_SENS = (240, 120, 170)

C_COMP_COLORS = [C_CPU, C_GPU, C_RAM, C_SSD, C_PSU, C_AIO, C_MB, C_NET, C_SENS]
C_COMP_NAMES  = ["CPU", "GPU", "RAM", "SSD", "Fuente de poder", "Refrigeración", "Placa madre", "WiFi", "Sensores"]

# ── Feedback colors ───────────────────────────────────────
C_GREEN       = (70,  210, 110)
C_GREEN_DIM   = (40, 120,  65)
C_YELLOW      = (240, 220,  65)
C_GOLD        = (250, 200,  80)
C_ORANGE      = (240, 160,  50)
C_RED         = (220,  75,  75)
C_RED_DIM     = (140,  45,  45)
C_BLUE        = (80,  150, 240)
C_CYAN        = (65,  210, 230)
C_CYAN_DIM    = (45,  110, 122)
C_PURPLE      = (170, 100, 225)
C_PINK        = (240, 120, 170)

C_SCORE_PLAYER = C_CYAN
C_SCORE_AI     = C_ORANGE

# ── Glow colors ───────────────────────────────────────────
C_GLOW_CYAN   = (100, 240, 255)
C_GLOW_GREEN  = (100, 255, 140)
C_GLOW_RED    = (255, 100, 100)
C_GLOW_YELLOW = (255, 240, 100)

# ── Star field ────────────────────────────────────────────
STAR_COLORS = [(100, 100, 160), (130, 130, 200), (80, 80, 140), (160, 160, 220)]

# ── Level configs ────────────────────────────────────────
LEVELS = [
    {
        "name": "Primera Reparación",
        "computers": 3, "components": 3,
        "req_range": (40, 70), "cap_range": (30, 85),
        "time": 60, "hints": 3,
        "ai_pop": 20, "ai_gen": 15, "ai_mut": 0.2,
    },
    {
        "name": "El Taller de Enlace",
        "computers": 4, "components": 4,
        "req_range": (45, 80), "cap_range": (35, 90),
        "time": 45, "hints": 2,
        "ai_pop": 30, "ai_gen": 20, "ai_mut": 0.18,
    },
    {
        "name": "Cables Cruzados",
        "computers": 5, "components": 5,
        "req_range": (50, 85), "cap_range": (40, 95),
        "time": 40, "hints": 1,
        "ai_pop": 40, "ai_gen": 30, "ai_mut": 0.15,
    },
    {
        "name": "Carrera contra el Robot",
        "computers": 6, "components": 6,
        "req_range": (55, 90), "cap_range": (45, 95),
        "time": 35, "hints": 0,
        "ai_pop": 50, "ai_gen": 40, "ai_mut": 0.12,
    },
    {
        "name": "Maestro de Asignación",
        "computers": 7, "components": 7,
        "req_range": (60, 95), "cap_range": (50, 98),
        "time": 30, "hints": 0,
        "ai_pop": 60, "ai_gen": 50, "ai_mut": 0.1,
    },
]
