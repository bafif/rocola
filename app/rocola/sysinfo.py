"""Información del sistema para la pantalla de diagnóstico de la rocola.

Junta datos de varias fuentes (PipeWire/pactl, /proc, la config de Xorg, pygame) y los
devuelve como una lista de (etiqueta, valor) lista para dibujar. Todo best-effort: si
una fuente falla, esa línea muestra '—' en vez de romper la pantalla.
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess

from . import audio
from .i18n import t

XORG_CONF = "/etc/X11/xorg.conf.d/10-rocola-display.conf"
DISPLAY_CONF = "/etc/rocola/display.conf"
_TIMEOUT = 4.0


def is_live() -> bool:
    """Running from the USB stick (live-boot mounts its medium there), not from a disk."""
    return os.path.isdir("/run/live/medium")


def _run(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=_TIMEOUT)


def _audio_output() -> str:
    d = audio.default_sink_name()
    if not d:
        return t("info.no_pipewire")
    for s in audio.list_sinks():
        if s.name == d:
            return f"{s.description}  [{s.kind}]"
    return d


def _audio_driver() -> str:
    """Módulo(s) de sonido en uso, de /proc/asound/modules (p. ej. snd_hda_intel)."""
    mods: list[str] = []
    try:
        with open("/proc/asound/modules", encoding="utf-8") as fh:
            for ln in fh:
                parts = ln.split(None, 1)
                if len(parts) == 2:
                    mods.append(parts[1].strip())
    except OSError:
        pass
    return ", ".join(dict.fromkeys(mods)) or "—"


def _video_driver() -> str:
    drv = "—"
    try:
        with open(XORG_CONF, encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("Driver") and '"' in s:
                    drv = s.split('"')[1]
                    break
    except OSError:
        pass
    kms = t("info.kms") if os.path.exists("/dev/dri/card0") else t("info.no_kms")
    return f"{drv} ({kms})"


def _display_mode() -> str:
    try:
        with open(DISPLAY_CONF, encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith("MODE="):
                    return line.strip().split("=", 1)[1]
    except OSError:
        pass
    return "—"


def _ip() -> str:
    try:
        ips = _run(["hostname", "-I"]).stdout.split()
        return ips[0] if ips else "—"
    except (OSError, subprocess.SubprocessError):
        return "—"


def collect(screen=None) -> list[tuple[str, str]]:
    """Devuelve las filas (etiqueta, valor) a mostrar en la pantalla de información."""
    rows: list[tuple[str, str]] = [
        (t("info.audio_output"), _audio_output()),
        (t("info.audio_driver"), _audio_driver()),
        (t("info.video_driver"), _video_driver()),
    ]
    if screen is not None:
        try:
            w, h = screen.get_size()
            rows.append((t("info.resolution"), f"{w}x{h}"))
        except Exception:  # noqa: BLE001
            pass
    rows += [
        (t("info.display_mode"), _display_mode()),
        (t("info.hostname"), socket.gethostname()),
        (t("info.ip"), _ip()),
        (t("info.kernel"), platform.release()),
    ]
    return rows
