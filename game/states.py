"""Game states."""
from enum import Enum, auto


class State(Enum):
    TUTORIAL = auto()
    MENU = auto()
    SETTINGS = auto()
    CREDITS = auto()
    LEVEL_SELECT = auto()
    PLAYING = auto()
    SELECT_COMPUTER = auto()
    DRAGGING = auto()
    AI_TURN = auto()
    RESULT = auto()