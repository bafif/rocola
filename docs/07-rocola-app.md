# 07 · La app (UI SDL2 + MPD)

*[English](07-rocola-app.en.md) · Español*

La rocola en sí: una **UI propia** a pantalla completa hecha con **SDL2** (Python + pygame) que
usa **MPD** como motor de audio.

En la imagen corre el `python3-pygame` de Debian bookworm (pygame 2.1.2). El entorno de desarrollo
y la CI usan **pygame-ce**, que mantiene la misma API pero es más nuevo: lo que use una función
reciente de pygame hay que probarlo en la ISO.

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
| `library.py` | vistas de la biblioteca por artista y álbum (sin pygame, se prueba sola) |
| `theme.py` | carga branding desde `assets/` (logo, colores, fuentes) |
| `config.py` | ajustes (defaults + `/etc/rocola/rocola.toml` + variables de entorno) |
| `audio.py` | salidas de PipeWire vía `pactl`: listar, elegir y recordar la salida |
| `bt.py` | emparejar parlantes Bluetooth vía `bluetoothctl` |
| `sysinfo.py` | datos de la pantalla de información (drivers, resolución, IP) |
| `i18n.py` | los textos de pantalla en español e inglés, y qué idioma mostrar |

## Escenas (UI)

- **Biblioteca**: por artista y álbum. Arriba, «Todas las canciones» y los artistas (por nombre;
  los temas sin tag de artista van al final, en «(sin artista)»), con cuántas canciones tiene cada
  uno. Un artista muestra «Todas de …» y sus álbumes, del más viejo al más nuevo según el tag
  `Date`; si tiene un solo álbum, se abre ese álbum directamente. Un álbum lista sus temas por
  disco y número de pista. Se agrupa por `AlbumArtist` si está (así un compilado queda junto) y
  si no por `Artist`. Con un solo artista (o ninguno con tags) queda la lista plana de canciones.
  ↑/↓ de a una, ←/→ de a diez; Atrás sube un nivel y, desde arriba, va a «Reproduciendo». Al
  recargarse la biblioteca (pendrive, «Actualizar biblioteca») se vuelve al mismo lugar.
  Seleccionar una canción → si no suena nada (o está en pausa) la reproduce; si ya suena otra, la
  suma al final de la cola. Todo sale del `listallinfo` que ya se carga: navegar no le pide nada
  más a MPD.
- **Now playing**: título, artista, álbum, estado y volumen de lo que suena, con la **portada** a
  la izquierda si la canción tiene una: la de su carpeta (`cover.jpg`, `cover.png` o `cover.webp`,
  lo que busca el `albumart` de MPD) o, si no, la embebida en el archivo (`readpicture`). Se pide
  una vez por canción, en bloques de 1 MiB (`binarylimit`), y se ignora si pesa más de 8 MB. Los
  textos largos se cortan con «…».
- **Menú** (botón 3 o F10): salida de audio, información del sistema, probar controles, actualizar
  la biblioteca, idioma y, desde el pendrive, instalar en disco.
- **Salida de audio**: elegir entre las salidas de PipeWire (analógica, HDMI, USB, Bluetooth) y
  emparejar un parlante Bluetooth.
- **Información**: drivers de audio y video, resolución, modo de pantalla, equipo, IP y kernel.
- **Probar controles**: muestra qué manda cada tecla o botón (el nombre o el índice que va en
  `[keys]`/`[buttons]`, ver [06](06-arcade-controls.md)) y qué acción le toca. Se sale con Atrás dos
  veces seguidas o a los 15 s sin tocar nada.

## Idioma

La rocola habla español o inglés. Al arrancar usa el idioma guardado en
`/etc/rocola/language.conf`; si no hay, el de la entrada de GRUB (`rocola.lang=en` en «Rocola —
English»), y si tampoco, el del sistema: español si el locale (`LANGUAGE`, `LC_ALL`,
`LC_MESSAGES`, `LANG`) prefiere español, inglés si no. La opción **«Idioma / Language»** del menú
pasa de uno al otro en el momento y lo guarda en ese archivo (en el pendrive dura hasta reiniciar,
como todo lo del modo live; en el disco instalado queda). El instalador también lo pregunta y lo
guarda. Los textos están en `app/rocola/i18n.py`; un test falla si a uno le falta un idioma o si
aparece un texto de pantalla escrito fuera de ahí.

## Render y rendimiento

- Resolución nativa del display activo (320×240 / 640×480 en CRT; mayor en VGA/moderno).
- Sin animaciones costosas por defecto; objetivo fluido en GPUs viejas.
- Fuentes y assets escalados al modo activo; layouts conscientes del *title-safe area* del CRT.

## Desarrollo local

```bash
make app-deps       # entorno con uv: pygame-ce, pytest, ruff (Python 3.11, como bookworm)
make app-test       # tests sin pantalla ni audio (SDL dummy, MPD falso)
make app-lint       # ruff (lint y formato)
make app-run        # la UI en una ventana; necesita un MPD local (por defecto 127.0.0.1:6600)
```

Ajustes: `/etc/rocola/rocola.toml` (o la ruta de `ROCOLA_CONFIG`) y, por encima, variables de
entorno. Un valor inválido se ignora y queda el default: la app nunca deja de arrancar por la
configuración.

| Clave en `rocola.toml` | Variable de entorno | Default |
|------------------------|---------------------|---------|
| `mpd_host` | `ROCOLA_MPD_HOST` | `127.0.0.1` |
| `mpd_port` | `ROCOLA_MPD_PORT` | `6600` |
| `theme` | `ROCOLA_THEME` | `ambar` |
| `display` (`lcd`, `crt`, `crt15`, `tv`; ver [09](09-branding-theming.md)) | `ROCOLA_DISPLAY` | `crt15` si `display.conf` dice `MODE=crt15`; si no, `lcd` |
| `effects` (`completo`, `suave`, `apagado`) | `ROCOLA_EFFECTS` | `completo` |
| `resolution` (`"640x480"` o `[640, 480]`) | `ROCOLA_RES` | resolución nativa |
| `windowed` | `ROCOLA_WINDOWED=1` | `false` |
| `fps` | — | `30` |
| — (`/etc/rocola/language.conf`, ver «Idioma») | `ROCOLA_LANG=es\|en` | según el locale |
| `[keys]`, `[buttons]` (mapeos de controles, ver [06](06-arcade-controls.md)) | — | los de `input.py` |

`ROCOLA_SCREENSHOT=/ruta.png` (y `ROCOLA_SCREENSHOT_SCENE=library|nowplaying|menu|audio|info|inputtest|btpair`)
dibuja una escena, guarda el PNG y sale: así se generan las capturas `docs/screenshots/ui-*.png`.

Siguiente: [08 · Música](08-music-management.md).
