# 07 · La app (UI SDL2 + MPD)

La rocola en sí: una **UI propia** a pantalla completa hecha con **SDL2** (Python + pygame-ce) que
usa **MPD** como motor de audio.

## Por qué esta arquitectura

- **MPD** resuelve lo difícil del audio: biblioteca, tags, cola, gapless, reproducción robusta, y es
  **liviano** (ideal i386/2 GB). Se controla por un protocolo de texto sobre socket.
- **La UI** solo dibuja y manda comandos: control total del **branding** y render **nativo** a baja
  resolución (clave para CRT 15 kHz), sin el peso de un media center o un navegador.

```
┌─────────────────────────────┐   socket (TCP 6600 / unix)   ┌───────────┐
│ app/rocola (SDL2)           │ ───────────────────────────► │   MPD     │
│  ui.py     render/escenas   │  play, pause, next, seek,     │  biblioteca
│  mpdclient.py  protocolo MPD│  add, setvol, status…         │  + cola   │
│  input.py  teclado+joystick │ ◄───────────────────────────  │  + audio  │
│  theme.py  branding/colores │   estado, lista, metadata     └─────┬─────┘
│  config.py mapeos/ajustes   │                                     │
└─────────────────────────────┘                              /music (archivos)
```

## Módulos (`app/rocola/`)

| Módulo | Rol |
|--------|-----|
| `__main__.py` | arranque: init SDL, carga config/tema, loop principal |
| `app.py` | orquesta escenas, estado global, bucle de eventos/render |
| `mpdclient.py` | cliente MPD por socket (sin dependencias externas) |
| `input.py` | capa de input: teclado + joystick → acciones de la rocola |
| `ui.py` | widgets/escenas: biblioteca, now-playing, menús |
| `theme.py` | carga branding desde `assets/` (logo, colores, fuentes) |
| `config.py` | ajustes y mapeos (defaults + archivo de usuario) |

## Escenas (UI)

- **Biblioteca**: navegación por artistas/álbumes/carpetas con portadas; selección → encola/reproduce.
- **Now playing**: portada grande, título/artista, progreso, volumen.
- **Menú**: ajustes, re-escanear música, acceso al instalador (combo).

## Render y rendimiento

- Resolución nativa del display activo (320×240 / 640×480 en CRT; mayor en VGA/moderno).
- Sin animaciones costosas por defecto; objetivo fluido en GPUs viejas.
- Fuentes y assets escalados al modo activo; layouts conscientes del *title-safe area* del CRT.

## Desarrollo local

```bash
# requiere un MPD corriendo localmente y python3-pygame (pygame-ce)
make app-run        # = cd app && python3 -m rocola
```

Variables/ajustes útiles (ver `config.py`): host/puerto de MPD, ruta de música, tema activo,
resolución forzada (para probar 640×480 en una pantalla moderna).

Siguiente: [08 · Música](08-music-management.md).
