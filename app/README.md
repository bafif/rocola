# app/ — UI de la rocola

*[English](README.en.md) · Español*

Interfaz a pantalla completa hecha con **pygame (SDL2)** que controla **MPD**. En la imagen corre el
`python3-pygame` de Debian bookworm (2.1.2); el desarrollo y la CI usan pygame-ce, con la misma API.

## Estructura

```
rocola/
  __main__.py   arranque (python3 -m rocola)
  app.py        loop principal, manejo de escenas
  mpdclient.py  cliente MPD por socket (sin deps externas; también portadas)
  input.py      teclado + joystick → acciones
  ui.py         escenas: biblioteca, now-playing, menú
  library.py    vistas de la biblioteca por artista y álbum (sin pygame)
  theme.py      temas v2: colores, fuentes, piezas, efectos y variantes por pantalla
  effects.py    nivel de efectos y la baja automática en una PC lenta
  skin.py       dibuja marquesina, tarjetas, cursor, lámparas, disco y panel con el tema
  config.py     ajustes (host MPD, resolución, tema…)
  audio.py      salidas de PipeWire (pactl)
  bt.py         emparejar Bluetooth (bluetoothctl)
  sysinfo.py    datos de la pantalla de información
  i18n.py       los textos de pantalla en español e inglés
  themecheck.py python -m rocola.theme check: contraste, letras con tilde y archivos de un tema
tests/          pytest (MPD falso, SDL dummy)
assets/
  fonts/
  themes/ambar/theme.toml
```

## Correr en desarrollo

Con [uv](https://docs.astral.sh/uv/) (Python 3.11, como Debian bookworm):

```bash
uv sync                          # pygame-ce, pytest, ruff
uv run pytest                    # tests sin pantalla ni audio (SDL dummy + MPD falso)
uv run ruff check .
ROCOLA_WINDOWED=1 uv run python -m rocola   # necesita un MPD local con música
```

Desde la raíz del repo, lo mismo es `make app-deps`, `make app-test`, `make app-lint` y
`make app-run`.

Ajustes por variables de entorno (ver `config.py`): `ROCOLA_MPD_HOST`, `ROCOLA_MPD_PORT`,
`ROCOLA_RES` (p. ej. `640x480` para simular CRT), `ROCOLA_THEME`, `ROCOLA_WINDOWED=1`, y
`ROCOLA_LANG=es` o `en` para el idioma (si no, el guardado desde el menú o el del locale; ver
`i18n.py`).

Ver también [../docs/07-rocola-app.md](../docs/07-rocola-app.md).
