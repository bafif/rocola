# app/ — Jukebox UI

*English · [Español](README.md)*

Full-screen interface built with **pygame (SDL2)** that controls **MPD**. The image runs Debian bookworm's
`python3-pygame` (2.1.2); development and CI use pygame-ce, which has the same API.

## Structure

```
rocola/
  __main__.py   entry point (python3 -m rocola)
  app.py        main loop, scene handling
  mpdclient.py  socket-based MPD client (no external deps; cover art too)
  input.py      keyboard + joystick → actions
  ui.py         scenes: library, now-playing, menu
  library.py    library views by artist and album (no pygame)
  theme.py      branding (logo, colors, fonts) from assets/
  config.py     settings (MPD host, resolution, theme…)
  audio.py      PipeWire outputs (pactl)
  bt.py         Bluetooth pairing (bluetoothctl)
  sysinfo.py    data for the info screen
tests/          pytest (fake MPD, dummy SDL)
assets/
  logo.svg
  fonts/
  themes/default/theme.toml
```

## Running in development

With [uv](https://docs.astral.sh/uv/) (Python 3.11, same as Debian bookworm):

```bash
uv sync                          # pygame-ce, pytest, ruff
uv run pytest                    # tests with no display or audio (dummy SDL + fake MPD)
uv run ruff check .
ROCOLA_WINDOWED=1 uv run python -m rocola   # needs a local MPD with music
```

From the repo root, the equivalents are `make app-deps`, `make app-test`, `make app-lint` and
`make app-run`.

Settings via environment variables (see `config.py`): `ROCOLA_MPD_HOST`, `ROCOLA_MPD_PORT`,
`ROCOLA_RES` (e.g. `640x480` to simulate a CRT), `ROCOLA_THEME`, `ROCOLA_WINDOWED=1`, and
`ROCOLA_LANG=en` or `es` for the language (otherwise the one saved from the menu, or the locale's;
see `i18n.py`).

See also [../docs/07-rocola-app.en.md](../docs/07-rocola-app.en.md).