# app/ — UI de la rocola

Interfaz a pantalla completa hecha con **pygame-ce (SDL2)** que controla **MPD**.

## Estructura

```
rocola/
  __main__.py   arranque (python3 -m rocola)
  app.py        loop principal, manejo de escenas
  mpdclient.py  cliente MPD por socket (sin deps externas)
  input.py      teclado + joystick → acciones
  ui.py         escenas: biblioteca, now-playing, menú
  theme.py      branding (logo, colores, fuentes) desde assets/
  config.py     ajustes (host MPD, resolución, tema…)
assets/
  logo.svg
  fonts/
  themes/default/theme.toml
```

## Correr en desarrollo

```bash
# Necesita un MPD local (con música en su music_directory) y pygame-ce.
sudo apt install mpd mpc python3-pygame      # Debian/Ubuntu
python3 -m rocola
```

Ajustes por variables de entorno (ver `config.py`): `ROCOLA_MPD_HOST`, `ROCOLA_MPD_PORT`,
`ROCOLA_RES` (p. ej. `640x480` para simular CRT), `ROCOLA_THEME`, `ROCOLA_WINDOWED=1`.

Ver también [../docs/07-rocola-app.md](../docs/07-rocola-app.md).
