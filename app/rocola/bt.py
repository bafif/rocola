"""Emparejamiento Bluetooth desde la app, vía `bluetoothctl` (no-interactivo).

Pensado para parlantes/auriculares BT estándar ("just works", sin PIN). Corre como el
usuario `rocola`: puede hablar con BlueZ (bus del sistema) gracias a la política D-Bus
del grupo `bluetooth` (ver os/rootfs-overlay/etc/dbus-1/system.d/rocola-bluetooth.conf).
Todo best-effort: si no hay adaptador o `bluetoothctl`, las funciones degradan a vacío/False
en vez de romper la UI. La UI (BtPairScene) maneja el escaneo y la selección con flechas.
"""

from __future__ import annotations

import subprocess
import time

_TIMEOUT = 6.0


def _run(args, timeout: float = _TIMEOUT):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def available() -> bool:
    """¿Hay un adaptador Bluetooth (controller) presente?"""
    try:
        r = _run(["bluetoothctl", "list"])
        return r.returncode == 0 and bool(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def power_on() -> None:
    try:
        _run(["bluetoothctl", "power", "on"])
    except (OSError, subprocess.SubprocessError):
        pass


def start_scan(seconds: int):
    """Arranca un escaneo en segundo plano (bluetoothctl --timeout sale solo)."""
    try:
        return subprocess.Popen(
            ["bluetoothctl", "--timeout", str(seconds), "scan", "on"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None


def stop_scan(proc=None) -> None:
    try:
        _run(["bluetoothctl", "scan", "off"])
    except (OSError, subprocess.SubprocessError):
        pass
    if proc is not None:
        try:
            proc.terminate()
        except OSError:
            pass


def devices() -> list[tuple[str, str]]:
    """Lista (MAC, nombre) de los dispositivos conocidos/descubiertos."""
    out: list[tuple[str, str]] = []
    try:
        r = _run(["bluetoothctl", "devices"])
    except (OSError, subprocess.SubprocessError):
        return out
    for line in r.stdout.splitlines():
        # "Device AA:BB:CC:DD:EE:FF Nombre del parlante"
        parts = line.split(None, 2)
        if len(parts) >= 2 and parts[0] == "Device":
            mac = parts[1]
            name = parts[2] if len(parts) == 3 else mac
            out.append((mac, name))
    return out


def is_connected(mac: str) -> bool:
    try:
        return "Connected: yes" in _run(["bluetoothctl", "info", mac]).stdout
    except (OSError, subprocess.SubprocessError):
        return False


def pair_connect(mac: str) -> bool:
    """Empareja, confía y conecta un dispositivo. Bloquea hasta ~1 min en el peor caso (la
    UI lo corre en un hilo y muestra 'Conectando…').

    Each step is its own one-shot `bluetoothctl <command>`: in that mode bluetoothctl
    waits for BlueZ's answer before it exits. Fed a script on stdin it read to the end
    of the input and quit at once, and BlueZ cancels a pairing whose requester is gone.
    With no agent, BlueZ pairs as NoInputNoOutput, which is what a speaker without a
    screen or keypad does anyway ("just works"). `trust` lets the speaker reconnect on
    its own later without asking anyone. A step that fails (pair says AlreadyExists for
    a speaker paired before) does not stop the next one; what counts is the end state.
    """
    steps = (
        (["bluetoothctl", "power", "on"], _TIMEOUT),
        (["bluetoothctl", "pair", mac], 40.0),
        (["bluetoothctl", "trust", mac], _TIMEOUT),
        (["bluetoothctl", "connect", mac], 30.0),
    )
    for args, timeout in steps:
        try:
            _run(args, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            pass
    for _ in range(5):  # the A2DP profile can take a moment after Connect answers
        if is_connected(mac):
            return True
        time.sleep(1.0)
    return False
