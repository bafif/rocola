# 07 · The app (SDL2 UI + MPD)

*English · [Español](07-rocola-app.md)*

The jukebox itself: a **custom** full-screen **UI** built with **SDL2** (Python + pygame) that
uses **MPD** as its audio engine.

The image runs Debian bookworm's `python3-pygame` (pygame 2.1.2). The development environment
and CI use **pygame-ce**, which keeps the same API but is newer: anything that relies on a recent
pygame function has to be tested on the ISO.

## Why this architecture

- **MPD** handles the hard parts of audio: library, tags, queue, gapless, robust playback, and it's
  **lightweight** (ideal for i386/2 GB). It's controlled through a text protocol over a socket.
- **The UI** only draws and sends commands: full control over **branding** and **native** rendering
  at low resolution (key for 15 kHz CRTs), without the weight of a media center or a browser.

```
┌─────────────────────────────┐   socket (TCP 6600 / unix)   ┌───────────┐
│ app/rocola (SDL2)           │ ───────────────────────────► │   MPD     │
│  ui.py     render/scenes    │  play, pause, next, seek,     │  library  │
│  mpdclient.py  MPD protocol │  add, setvol, status…         │  + queue  │
│  input.py  keyboard+joystick│ ◄───────────────────────────  │  + audio  │
│  theme.py  branding/colors  │   status, list, metadata      └─────┬─────┘
│  config.py mappings/settings│                                     │
└─────────────────────────────┘                              /music (files)
```

## Modules (`app/rocola/`)

| Module | Role |
|--------|-----|
| `__main__.py` | startup: SDL init, loads config/theme, main loop |
| `app.py` | orchestrates scenes, global state, event/render loop |
| `mpdclient.py` | MPD client over socket (no external dependencies) |
| `input.py` | input layer: keyboard + joystick → jukebox actions |
| `ui.py` | widgets/scenes: library, now playing, menus |
| `library.py` | library views by artist and album (no pygame, testable on its own) |
| `theme.py` | loads branding from `assets/` (logo, colors, fonts) |
| `config.py` | settings (defaults + `/etc/rocola/rocola.toml` + environment variables) |
| `audio.py` | PipeWire outputs via `pactl`: list, pick and remember the output |
| `bt.py` | pair Bluetooth speakers via `bluetoothctl` |
| `sysinfo.py` | data for the information screen (drivers, resolution, IP) |
| `i18n.py` | the on-screen texts in Spanish and English, and which language to show |

## Scenes (UI)

- **Library**: by artist and album. At the top, “All songs” and the artists (by name; tracks
  without an artist tag go at the end, under “(no artist)”), with how many songs each one has.
  An artist shows “All by …” and their albums, oldest to newest according to the `Date` tag; if
  they have a single album, that album opens directly. An album lists its tracks by disc and
  track number. Grouping is by `AlbumArtist` if present (so a compilation stays together) and
  otherwise by `Artist`. With a single artist (or none with tags) you get the flat song list.
  ↑/↓ move one at a time, ←/→ ten at a time; Back goes up one level and, from the top, goes to
  “Now playing”. When the library reloads (USB stick, “Update library”) you return to the same
  spot. Selecting a song → if nothing is playing (or it's paused) it plays it; if something else
  is already playing, it's added to the end of the queue. Everything comes from the `listallinfo`
  that's already loaded: browsing doesn't ask MPD for anything else.
- **Now playing**: title, artist, album, status and volume of what's playing, with the **cover
  art** on the left if the song has one: the one in its folder (`cover.jpg`, `cover.png` or
  `cover.webp`, which is what MPD's `albumart` looks for) or, if not, the one embedded in the file
  (`readpicture`). It's requested once per song, in 1 MiB chunks (`binarylimit`), and ignored if
  it's larger than 8 MB. Long text gets cut off with “…”.
- **Menu** (button 3 or F10): audio output, system information, test controls, update the library,
  language and, when running from the USB stick, install to disk.
- **Audio output**: choose among the PipeWire outputs (analog, HDMI, USB, Bluetooth) and pair a
  Bluetooth speaker.
- **Information**: audio and video drivers, resolution, display mode, machine, IP and kernel.
- **Test controls**: shows what each key or button sends (the name or index that goes in
  `[keys]`/`[buttons]`, see [06](06-arcade-controls.en.md)) and which action it maps to. Exit by
  pressing Back twice in a row or after 15 s without touching anything.

## Language

The jukebox speaks Spanish or English. At startup it uses the language saved in
`/etc/rocola/language.conf`; if there is none, the one from the GRUB entry (`rocola.lang=en` in
"Rocola — English"), and failing that, the system's: Spanish if the locale (`LANGUAGE`, `LC_ALL`,
`LC_MESSAGES`, `LANG`) prefers Spanish, English otherwise. The **"Language / Idioma"** menu option
switches between the two on the spot and saves the choice in that file (on the USB stick it lasts
until the next reboot, like everything in the live system; on the installed disk it stays). The
installer asks for it too and saves it. The texts live in `app/rocola/i18n.py`; a test fails if
one of them is missing a language or if an on-screen text is written outside that file.

## Rendering and performance

- Native resolution of the active display (320×240 / 640×480 on CRT; higher on VGA/modern).
- No expensive animations by default; the goal is smooth performance on old GPUs.
- Fonts and assets scaled to the active mode; layouts aware of the CRT's *title-safe area*.

## Local development

```bash
make app-deps       # environment with uv: pygame-ce, pytest, ruff (Python 3.11, like bookworm)
make app-test       # tests with no display or audio (SDL dummy, fake MPD)
make app-lint       # ruff (lint and format)
make app-run        # the UI in a window; needs a local MPD (127.0.0.1:6600 by default)
```

Settings: `/etc/rocola/rocola.toml` (or the path in `ROCOLA_CONFIG`) and, on top of that,
environment variables. An invalid value is ignored and the default stays: the app never fails to
start because of the configuration.

| Key in `rocola.toml` | Environment variable | Default |
|------------------------|---------------------|---------|
| `mpd_host` | `ROCOLA_MPD_HOST` | `127.0.0.1` |
| `mpd_port` | `ROCOLA_MPD_PORT` | `6600` |
| `theme` | `ROCOLA_THEME` | `default` |
| `resolution` (`"640x480"` or `[640, 480]`) | `ROCOLA_RES` | native resolution |
| `windowed` | `ROCOLA_WINDOWED=1` | `false` |
| `fps` | — | `30` |
| — (`/etc/rocola/language.conf`, see "Language") | `ROCOLA_LANG=es\|en` | from the locale |
| `[keys]`, `[buttons]` (control mappings, see [06](06-arcade-controls.en.md)) | — | the ones in `input.py` |

`ROCOLA_SCREENSHOT=/path.png` (and `ROCOLA_SCREENSHOT_SCENE=library|nowplaying|menu|audio|info|inputtest|btpair`)
draws a scene, saves the PNG and exits: that's how the `docs/screenshots/ui-*.png` screenshots are generated.

Next: [08 · Music](08-music-management.en.md).