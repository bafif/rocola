"""How much the jukebox moves: the effects level and the guard that lowers it on a slow PC.

`effects` in rocola.toml is "completo", "suave" or "apagado" (also "full", "soft", "off").
The scenes ask `level` before drawing anything that moves. If the frames take on average
more than BUDGET_MS, the level goes down one step, and it never goes back up while the app
runs: an old PC should look calm, not stutter.
"""

from __future__ import annotations

import sys

LEVELS = ("completo", "suave", "apagado")
_ALIASES = {"full": "completo", "soft": "suave", "off": "apagado"}


def parse_level(value: object, default: str = "completo") -> str:
    """The level named by `value` (Spanish or English), or `default` if it names none."""
    if not isinstance(value, str):
        return default
    name = value.strip().lower()
    name = _ALIASES.get(name, name)
    return name if name in LEVELS else default


class EffectsGovernor:
    """Measures every frame and lowers the effects level when the PC cannot keep up."""

    BUDGET_MS = 20.0
    WINDOW = 60  # frames per measure: two seconds at 30 fps

    def __init__(self, level: str = "completo") -> None:
        self.level = parse_level(level)
        self._total = 0.0
        self._count = 0

    def frame(self, ms: float) -> bool:
        """Record how long one frame took to draw; True when this lowered the level."""
        self._total += ms
        self._count += 1
        if self._count < self.WINDOW:
            return False
        average = self._total / self._count
        self._total, self._count = 0.0, 0
        if average <= self.BUDGET_MS or self.level == LEVELS[-1]:
            return False
        old = self.level
        self.level = LEVELS[LEVELS.index(old) + 1]
        print(
            f"[rocola] effects: {old} -> {self.level} (average frame {average:.1f} ms)",
            file=sys.stderr,
        )
        return True
