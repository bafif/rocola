"""The jukebox's texts in Spanish and English, and which language to show.

Every text on screen comes from CATALOG through t(). The language is picked at start
(detect) and changed from the menu; the choice is saved in /etc/rocola/language.conf,
next to audio.conf. The same rule in bash is /usr/local/bin/rocola-lang
(os/rootfs-overlay), which the installer and the console scripts use: keep both in
step (tests/test_i18n.py runs them side by side).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

LANGUAGES = ("es", "en")
FALLBACK = "en"  # a system whose preferred languages include no Spanish gets English

# Written by the menu (and by the installer on the disk it installs to). The image
# ships it empty and owned by `rocola` (os/Containerfile), like audio.conf.
LANGUAGE_CONF = Path(os.environ.get("ROCOLA_LANGUAGE_CONF", "/etc/rocola/language.conf"))
# rocola.lang=en on the kernel command line: the "English" entry of the USB stick's
# boot menu (image/build-image.sh), where nothing saved survives a reboot.
CMDLINE = Path(os.environ.get("ROCOLA_CMDLINE", "/proc/cmdline"))

CATALOG: dict[str, dict[str, str]] = {
    # Headers
    "header.library": {"es": "BIBLIOTECA", "en": "LIBRARY"},
    "header.nowplaying": {"es": "REPRODUCIENDO", "en": "NOW PLAYING"},
    "header.menu": {"es": "MENÚ", "en": "MENU"},
    "header.audio": {"es": "SALIDA DE AUDIO", "en": "AUDIO OUTPUT"},
    "header.info": {"es": "INFORMACIÓN", "en": "SYSTEM INFO"},
    "header.inputtest": {"es": "CONTROLES", "en": "CONTROLS"},
    "header.bluetooth": {"es": "BLUETOOTH", "en": "BLUETOOTH"},
    # Library
    "library.empty": {
        "es": "Sin música. Importá canciones (ver menú).",
        "en": "No music yet. Import some songs (see the menu).",
    },
    "library.mpd_error": {"es": "MPD: {error}", "en": "MPD: {error}"},
    "library.all_songs": {"es": "Todas las canciones", "en": "All songs"},
    "library.all_by": {"es": "Todas de {artist}", "en": "All by {artist}"},
    "library.unknown_artist": {"es": "(sin artista)", "en": "(no artist)"},
    "library.unknown_album": {"es": "(sin álbum)", "en": "(no album)"},
    "library.unknown_song": {"es": "(desconocido)", "en": "(unknown)"},
    "library.one_song": {"es": "1 canción", "en": "1 song"},
    "library.songs": {"es": "{n} canciones", "en": "{n} songs"},
    "library.page": {"es": "Página {page} de {pages}", "en": "Page {page} of {pages}"},
    # The legend of the buttons, at the bottom of the jukebox's screens
    "legend.move": {"es": "Mover", "en": "Move"},
    "legend.page": {"es": "Página", "en": "Page"},
    "legend.choose": {"es": "Elegir", "en": "Choose"},
    "legend.back": {"es": "Atrás", "en": "Back"},
    "legend.menu": {"es": "Menú", "en": "Menu"},
    "legend.pause": {"es": "Pausa", "en": "Pause"},
    "legend.play": {"es": "Seguir", "en": "Play"},
    "legend.next": {"es": "Siguiente", "en": "Next"},
    "legend.volume": {"es": "Volumen", "en": "Volume"},
    "legend.library": {"es": "Biblioteca", "en": "Library"},
    # Now playing
    "status.play": {"es": "Reproduciendo", "en": "Playing"},
    "status.pause": {"es": "En pausa", "en": "Paused"},
    "status.stop": {"es": "Detenido", "en": "Stopped"},
    "nowplaying.volume": {"es": "Volumen", "en": "Volume"},
    "nowplaying.next": {"es": "A continuación: {song}", "en": "Up next: {song}"},
    # Menu
    "menu.audio": {"es": "Salida de audio", "en": "Audio output"},
    "menu.info": {"es": "Información del sistema", "en": "System info"},
    "menu.inputtest": {"es": "Probar controles", "en": "Test controls"},
    "menu.update": {"es": "Actualizar biblioteca", "en": "Update library"},
    # Both words, so whoever does not read the current language still finds it.
    "menu.language": {"es": "Idioma / Language: Español", "en": "Language / Idioma: English"},
    "menu.install": {"es": "Instalar en disco", "en": "Install to disk"},
    "menu.back": {"es": "Volver", "en": "Back"},
    "installer.failed": {
        "es": "No se pudo abrir el instalador.",
        "en": "Could not open the installer.",
    },
    "installer.failed_detail": {
        "es": "No se pudo abrir el instalador: {detail}",
        "en": "Could not open the installer: {detail}",
    },
    # Audio output
    "audio.pair": {"es": "+  Emparejar Bluetooth...", "en": "+  Pair Bluetooth..."},
    "audio.unavailable": {
        "es": "PipeWire no responde todavía. Reintentá en unos segundos.",
        "en": "PipeWire is not answering yet. Try again in a few seconds.",
    },
    "audio.hint": {
        "es": "Enter: elegir salida y probar tono   -   Esc: volver",
        "en": "Enter: choose the output and play a test sound   -   Esc: back",
    },
    "audio.kind.bluetooth": {"es": "Bluetooth", "en": "Bluetooth"},
    "audio.kind.usb": {"es": "USB", "en": "USB"},
    "audio.kind.hdmi": {"es": "HDMI/Digital", "en": "HDMI/Digital"},
    "audio.kind.analog": {"es": "Analógica", "en": "Analog"},
    "audio.kind.other": {"es": "Audio", "en": "Audio"},
    # System info
    "info.hint": {"es": "Esc: volver", "en": "Esc: back"},
    "info.audio_output": {"es": "Salida de audio", "en": "Audio output"},
    "info.audio_driver": {"es": "Driver de audio", "en": "Audio driver"},
    "info.video_driver": {"es": "Driver de video", "en": "Video driver"},
    "info.resolution": {"es": "Resolución", "en": "Resolution"},
    "info.display_mode": {"es": "Modo de pantalla", "en": "Display mode"},
    "info.hostname": {"es": "Equipo", "en": "Hostname"},
    "info.ip": {"es": "IP", "en": "IP"},
    "info.kernel": {"es": "Kernel", "en": "Kernel"},
    "info.no_pipewire": {"es": "— (PipeWire no disponible)", "en": "— (PipeWire not available)"},
    "info.kms": {"es": "con KMS", "en": "with KMS"},
    "info.no_kms": {"es": "sin KMS (fbdev)", "en": "no KMS (fbdev)"},
    # Controls test
    "input.intro": {"es": "Apretá teclas o botones.", "en": "Press keys or buttons."},
    "input.waiting": {"es": "Esperando...", "en": "Waiting..."},
    "input.key": {"es": "Tecla «{name}»", "en": 'Key "{name}"'},
    "input.button": {
        "es": "Joystick {joy} · botón {button}",
        "en": "Joystick {joy} · button {button}",
    },
    "input.hat": {"es": "Joystick {joy} · cruceta {value}", "en": "Joystick {joy} · D-pad {value}"},
    "input.axis": {
        "es": "Joystick {joy} · eje {axis} ({value:+.1f})",
        "en": "Joystick {joy} · axis {axis} ({value:+.1f})",
    },
    "input.no_action": {"es": "sin acción", "en": "no action"},
    "input.hint": {
        "es": "Volver: Atrás dos veces o {seconds} s sin tocar nada",
        "en": "To leave: Back twice, or {seconds} s without touching anything",
    },
    # Bluetooth pairing
    "bt.scanning": {
        "es": "Buscando dispositivos... ({seconds}s)",
        "en": "Looking for devices... ({seconds}s)",
    },
    "bt.choose": {
        "es": "Elegí un dispositivo (Enter para emparejar):",
        "en": "Choose a device (Enter to pair):",
    },
    "bt.connecting": {
        "es": "Conectando con {name}... ({seconds}s)",
        "en": "Connecting to {name}... ({seconds}s)",
    },
    "bt.connected": {
        "es": "Conectado: {name}\n\nElegilo como salida (Enter para volver).",
        "en": "Connected: {name}\n\nChoose it as the output (Enter to go back).",
    },
    "bt.failed": {
        "es": "No se pudo conectar a {name}.\n\nReintentá (Enter para volver).",
        "en": "Could not connect to {name}.\n\nTry again (Enter to go back).",
    },
    "bt.empty": {
        "es": "No se encontraron dispositivos.\n\nPoné el parlante en"
        " modo emparejamiento y reintentá (Enter para volver).",
        "en": "No devices found.\n\nPut the speaker in pairing mode"
        " and try again (Enter to go back).",
    },
    "bt.noadapter": {
        "es": "No hay adaptador Bluetooth.\n\nMuchas PCs no traen BT:"
        " conectá un dongle USB (Enter para volver).",
        "en": "No Bluetooth adapter.\n\nMany PCs do not have one:"
        " plug in a USB dongle (Enter to go back).",
    },
    "bt.hint": {"es": "Enter: emparejar   -   Esc: volver", "en": "Enter: pair   -   Esc: back"},
}

_current = FALLBACK


def t(key: str, **fields: object) -> str:
    """The text for `key` in the current language, with `fields` filled in."""
    text = CATALOG[key][_current]
    return text.format(**fields) if fields else text


def language() -> str:
    return _current


def set_language(lang: str) -> None:
    global _current
    if lang not in LANGUAGES:
        raise ValueError(f"unknown language {lang!r}")
    _current = lang


def next_language(lang: str) -> str:
    return LANGUAGES[(LANGUAGES.index(lang) + 1) % len(LANGUAGES)]


def normalize(value: str | None) -> str | None:
    """Language code of a locale or a setting: es_AR.UTF-8 -> es, en-US -> en, else None."""
    code = "".join(c for c in value or "" if not c.isspace() and c not in "\"'").lower()
    for sep in "_.@-":
        code = code.split(sep, 1)[0]
    return code if code in LANGUAGES else None


def from_locale(environ: Mapping[str, str]) -> str:
    """Spanish if any of the preferred languages is Spanish, English otherwise.

    The preferred languages are GNU's LANGUAGE list plus the first of LC_ALL,
    LC_MESSAGES and LANG that is set (the one that decides the messages).
    """
    prefs = environ.get("LANGUAGE", "").split(":")
    messages = (environ[k] for k in ("LC_ALL", "LC_MESSAGES", "LANG") if environ.get(k))
    prefs.append(next(messages, ""))
    return "es" if any(normalize(p) == "es" for p in prefs) else FALLBACK


def saved(path: Path | None = None) -> str | None:
    """The language chosen in the menu or the installer (LANGUAGE= in language.conf)."""
    value = None
    try:
        with open(path or LANGUAGE_CONF, encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("LANGUAGE="):
                    value = s.split("=", 1)[1]
    except OSError:
        return None
    return normalize(value)


def from_cmdline(path: Path | None = None) -> str | None:
    """rocola.lang=<es|en> on the kernel command line."""
    try:
        words = Path(path or CMDLINE).read_text(encoding="utf-8").split()
    except OSError:
        return None
    values = [w.split("=", 1)[1] for w in words if w.startswith("rocola.lang=")]
    return normalize(values[-1]) if values else None


def detect(
    environ: Mapping[str, str] | None = None,
    conf: Path | None = None,
    cmdline: Path | None = None,
) -> str:
    """The language to start in. First wins:

    1. ROCOLA_LANG (development and tests, like the other ROCOLA_* variables);
    2. the choice saved from the menu or the installer;
    3. rocola.lang= on the kernel command line;
    4. the system locale.
    """
    env = os.environ if environ is None else environ
    return (
        normalize(env.get("ROCOLA_LANG"))
        or saved(conf)
        or from_cmdline(cmdline)
        or from_locale(env)
    )


def save(lang: str, path: Path | None = None) -> bool:
    """Rewrite LANGUAGE= in language.conf, keeping its comments. Best-effort, like
    audio.conf: the file is rewritten in place because `rocola` owns the file but not
    /etc/rocola, so it cannot replace it."""
    target = path or LANGUAGE_CONF
    lines: list[str] = []
    found = False
    try:
        if os.path.exists(target):
            with open(target, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip().startswith("LANGUAGE="):
                        if not found:
                            lines.append(f"LANGUAGE={lang}\n")
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f"LANGUAGE={lang}\n")
        with open(target, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
    except OSError:
        return False
    return True
