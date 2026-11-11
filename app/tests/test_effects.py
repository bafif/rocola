from __future__ import annotations

import pytest

from rocola.effects import LEVELS, EffectsGovernor, parse_level


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("completo", "completo"),
        (" Suave ", "suave"),
        ("off", "apagado"),
        ("full", "completo"),
        ("soft", "suave"),
        ("turbo", "suave"),
        (3, "suave"),
        (None, "suave"),
    ],
)
def test_parse_level(value, expected):
    assert parse_level(value, "suave") == expected


def run(governor: EffectsGovernor, ms: float, frames: int) -> list[bool]:
    return [governor.frame(ms) for _ in range(frames)]


def test_fast_frames_keep_the_level():
    gov = EffectsGovernor("completo")
    assert not any(run(gov, 12.0, gov.WINDOW * 5))
    assert gov.level == "completo"


def test_slow_frames_lower_one_step_per_measure(capsys):
    gov = EffectsGovernor("completo")
    lowered = run(gov, 30.0, gov.WINDOW)
    assert lowered[-1] and not any(lowered[:-1])
    assert gov.level == "suave"
    run(gov, 30.0, gov.WINDOW * 3)
    assert gov.level == LEVELS[-1]
    assert "completo -> suave" in capsys.readouterr().err


def test_one_slow_frame_does_not_lower_it():
    gov = EffectsGovernor("completo")
    gov.frame(500.0 - 12.0 * (gov.WINDOW - 1) - 1)  # the average stays under budget
    run(gov, 12.0, gov.WINDOW - 1)
    assert gov.level == "completo"


def test_it_never_goes_back_up():
    gov = EffectsGovernor("suave")
    run(gov, 40.0, gov.WINDOW)
    run(gov, 1.0, gov.WINDOW * 3)
    assert gov.level == "apagado"
