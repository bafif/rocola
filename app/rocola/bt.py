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


def _run(args, timeout: float = _TIMEOUT, stdin: str | None = None):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=stdin)


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
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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
    """Empareja, confía y conecta un dispositivo. Bloquea unos segundos (la UI muestra
    'Conectando…' antes). El agente 'NoInputNoOutput' acepta el pairing 'just works'.
    """
    # 'pair' tiene que ir en la MISMA sesión donde se registra el agente (vía stdin).
    pair_seq = f"power on\nagent NoInputNoOutput\ndefault-agent\npair {mac}\n"
    try:
        _run(["bluetoothctl"], timeout=20.0, stdin=pair_seq)
        time.sleep(0.5)
        _run(["bluetoothctl", "trust", mac])
        _run(["bluetoothctl", "connect", mac], timeout=12.0)
        time.sleep(1.0)
    except (OSError, subprocess.SubprocessError):
        pass  # aún con timeout en algún paso, abajo verificamos si quedó conectado
    return is_connected(mac)
