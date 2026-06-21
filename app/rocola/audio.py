"""Salida de audio de la rocola: sinks de PipeWire vía `pactl`.

La app NO reproduce audio por SDL: el motor es MPD y el ruteo (analógica / HDMI / USB
/ Bluetooth) lo decide PipeWire. Acá envolvemos `pactl` para listar los sinks, saber
y elegir el sink por defecto, y disparar un tono de prueba. Todo por subprocess
liviano (sin dependencias nuevas) y best-effort: si PipeWire/pactl no están, las
funciones devuelven vacío en vez de romper la UI.
"""
from __future__ import annotations

import glob
import os
import subprocess
from dataclasses import dataclass

# audio.conf: la app persiste acá la salida elegida para que sobreviva al reboot
# (rocola-audio-default la re-aplica al arrancar). El Dockerfile la deja escribible
# por 'rocola'.
AUDIO_CONF = "/etc/rocola/audio.conf"
_TIMEOUT = 4.0


@dataclass
class Sink:
    name: str          # nombre PipeWire (estable), p. ej. alsa_output.usb-...analog-stereo
    description: str   # texto legible, p. ej. "USB Audio Analog Stereo"
    is_default: bool = False

    @property
    def kind(self) -> str:
        n = self.name.lower()
        if "bluez" in n:
            return "Bluetooth"
        if ".usb-" in n or "usb" in n:
            return "USB"
        if "hdmi" in n or "iec958" in n or "digital" in n:
            return "HDMI/Digital"
        if "analog" in n:
            return "Analógica"
        return "Audio"


def _run(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=_TIMEOUT)


def available() -> bool:
    """¿Hay pactl y PipeWire respondiendo?"""
    try:
        return _run(["pactl", "info"]).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def default_sink_name() -> str | None:
    try:
        r = _run(["pactl", "get-default-sink"])
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    # Fallback: parsear `pactl info`.
    try:
        for line in _run(["pactl", "info"]).stdout.splitlines():
            if line.startswith("Default Sink:"):
                return line.split(":", 1)[1].strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def list_sinks() -> list[Sink]:
    """Lista los sinks de PipeWire con su descripción, marcando el default."""
    sinks: list[Sink] = []
    default = default_sink_name()
    try:
        short = _run(["pactl", "list", "short", "sinks"])
        if short.returncode != 0:
            return sinks
        names = [ln.split("\t")[1] for ln in short.stdout.splitlines() if "\t" in ln]
    except (OSError, subprocess.SubprocessError, IndexError):
        return sinks
    descs = _sink_descriptions()
    for name in names:
        sinks.append(Sink(name=name, description=descs.get(name, name),
                          is_default=(name == default)))
    return sinks


def _sink_descriptions() -> dict[str, str]:
    """Mapa nombre -> Description, parseando `pactl list sinks`."""
    out: dict[str, str] = {}
    try:
        r = _run(["pactl", "list", "sinks"])
    except (OSError, subprocess.SubprocessError):
        return out
    if r.returncode != 0:
        return out
    name: str | None = None
    for line in r.stdout.splitlines():
        s = line.strip()
        if s.startswith("Name:"):
            name = s.split(":", 1)[1].strip()
        elif s.startswith("Description:") and name:
            out[name] = s.split(":", 1)[1].strip()
            name = None
    return out


def set_default(sink_name: str) -> bool:
    """Fija el sink por defecto, mueve los streams activos (MPD) y persiste la elección."""
    try:
        ok = _run(["pactl", "set-default-sink", sink_name]).returncode == 0
        _run(["pactl", "set-sink-mute", sink_name, "0"])
        si = _run(["pactl", "list", "short", "sink-inputs"])
        for ln in si.stdout.splitlines():
            sid = ln.split("\t", 1)[0].strip()
            if sid:
                _run(["pactl", "move-sink-input", sid, sink_name])
    except (OSError, subprocess.SubprocessError):
        return False
    if ok:
        _persist_output(sink_name)
    return ok


def _persist_output(sink_name: str) -> None:
    """Reescribe OUTPUT= en audio.conf para que la elección sobreviva al reboot."""
    try:
        lines: list[str] = []
        found = False
        if os.path.exists(AUDIO_CONF):
            with open(AUDIO_CONF, encoding="utf-8") as fh:
                for ln in fh:
                    if ln.lstrip().startswith("OUTPUT="):
                        lines.append(f"OUTPUT={sink_name}\n")
                        found = True
                    else:
                        lines.append(ln)
        if not found:
            lines.append(f"OUTPUT={sink_name}\n")
        with open(AUDIO_CONF, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
    except OSError:
        pass  # best-effort: si /etc no es escribible, igual quedó aplicado en vivo


def play_test_tone(sink_name: str | None = None) -> None:
    """Reproduce un tono corto al sink dado (o al default) para confirmar al oído."""
    tone = _first_tone()
    if not tone:
        return
    args = ["paplay"]
    if sink_name:
        args += ["--device", sink_name]
    args.append(tone)
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def _first_tone() -> str | None:
    for pattern in ("/music/*.wav", "/music/*.WAV", "/opt/rocola/music/*.wav"):
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]
    return None
