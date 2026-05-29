"""Capa de input: traduce eventos de pygame (teclado + joystick) a acciones.

Autodetecta joysticks y deja el teclado siempre activo, así funciona con
encoders de arcade en modo teclado o en modo joystick sin configurar nada.
"""
from __future__ import annotations

import pygame

# --- Acciones de la rocola ---
UP = "up"
DOWN = "down"
LEFT = "left"
RIGHT = "right"
SELECT = "select"
BACK = "back"
PLAYPAUSE = "playpause"
NEXT = "next"
PREV = "prev"
VOLUP = "volup"
VOLDOWN = "voldown"
MENU = "menu"

DEFAULT_KEYMAP = {
    pygame.K_UP: UP,
    pygame.K_DOWN: DOWN,
    pygame.K_LEFT: LEFT,
    pygame.K_RIGHT: RIGHT,
    pygame.K_RETURN: SELECT,
    pygame.K_KP_ENTER: SELECT,
    pygame.K_ESCAPE: BACK,
    pygame.K_BACKSPACE: BACK,
    pygame.K_SPACE: PLAYPAUSE,
    pygame.K_n: NEXT,
    pygame.K_p: PREV,
    pygame.K_PLUS: VOLUP,
    pygame.K_EQUALS: VOLUP,
    pygame.K_KP_PLUS: VOLUP,
    pygame.K_MINUS: VOLDOWN,
    pygame.K_KP_MINUS: VOLDOWN,
    pygame.K_F10: MENU,
}

# Mapeo típico de encoders/gamepads de arcade (ajustable por usuario).
DEFAULT_BUTTONMAP = {
    0: SELECT,
    1: BACK,
    2: PLAYPAUSE,
    3: MENU,
    4: PREV,
    5: NEXT,
    6: VOLDOWN,
    7: VOLUP,
}


class InputManager:
    def __init__(self, keymap=None, buttonmap=None, deadzone: float = 0.5):
        self.keymap = keymap or dict(DEFAULT_KEYMAP)
        self.buttonmap = buttonmap or dict(DEFAULT_BUTTONMAP)
        self.deadzone = deadzone
        self.joysticks: list = []
        self._axis_state: dict = {}

    def init_joysticks(self) -> int:
        pygame.joystick.init()
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            self.joysticks.append(joy)
        return len(self.joysticks)

    def translate(self, event) -> str | None:
        """Devuelve la acción para un evento de pygame, o None."""
        if event.type == pygame.KEYDOWN:
            return self.keymap.get(event.key)
        if event.type == pygame.JOYBUTTONDOWN:
            return self.buttonmap.get(event.button)
        if event.type == pygame.JOYHATMOTION:
            x, y = event.value
            if y == 1:
                return UP
            if y == -1:
                return DOWN
            if x == -1:
                return LEFT
            if x == 1:
                return RIGHT
            return None
        if event.type == pygame.JOYAXISMOTION:
            return self._axis_action(event)
        return None

    def _axis_action(self, event) -> str | None:
        key = (event.joy, event.axis)
        value = event.value
        pos = -1 if value <= -self.deadzone else (1 if value >= self.deadzone else 0)
        if pos == self._axis_state.get(key, 0):
            return None  # sin cambio: evita repeticiones mientras se mantiene
        self._axis_state[key] = pos
        if pos == 0:
            return None
        if event.axis % 2 == 0:  # ejes pares = horizontal
            return LEFT if pos < 0 else RIGHT
        return UP if pos < 0 else DOWN  # ejes impares = vertical
