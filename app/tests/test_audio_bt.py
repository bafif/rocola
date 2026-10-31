"""pactl / bluetoothctl wrappers, with subprocess replaced by canned outputs."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from rocola import audio, bt

SHORT_SINKS = (
    "47\talsa_output.pci-0000_00_1b.0.analog-stereo\tPipeWire\ts32le 2ch 48000Hz\tSUSPENDED\n"
    "52\tbluez_output.AA_BB_CC_DD_EE_FF.1\tPipeWire\ts16le 2ch 48000Hz\tRUNNING\n"
)
LONG_SINKS = """Sink #47
\tState: SUSPENDED
\tName: alsa_output.pci-0000_00_1b.0.analog-stereo
\tDescription: Built-in Audio Analog Stereo
\tDriver: PipeWire
Sink #52
\tName: bluez_output.AA_BB_CC_DD_EE_FF.1
\tDescription: JBL Go
"""


def fake_runner(outputs: dict[tuple[str, ...], str], calls: list | None = None, rc: int = 0):
    def run(args, *_, **__):
        if calls is not None:
            calls.append(tuple(args))
        out = outputs.get(tuple(args))
        if out is None:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        return SimpleNamespace(returncode=rc, stdout=out, stderr="")

    return run


def missing_binary(*_args, **_kwargs):
    raise FileNotFoundError("pactl")


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("bluez_output.AA_BB.1", "Bluetooth"),
        ("alsa_output.usb-Generic_USB_Audio-00.analog-stereo", "USB"),
        ("alsa_output.pci-0000_01_00.1.hdmi-stereo", "HDMI/Digital"),
        ("alsa_output.pci-0000_00_1b.0.iec958-stereo", "HDMI/Digital"),
        ("alsa_output.pci-0000_00_1b.0.analog-stereo", "Analógica"),
        ("null-sink", "Audio"),
    ],
)
def test_sink_kind(name, kind):
    assert audio.Sink(name=name, description="").kind == kind


def test_list_sinks(monkeypatch):
    monkeypatch.setattr(
        audio,
        "_run",
        fake_runner(
            {
                ("pactl", "get-default-sink"): "bluez_output.AA_BB_CC_DD_EE_FF.1\n",
                ("pactl", "list", "short", "sinks"): SHORT_SINKS,
                ("pactl", "list", "sinks"): LONG_SINKS,
            }
        ),
    )
    sinks = audio.list_sinks()
    assert [(s.description, s.kind, s.is_default) for s in sinks] == [
        ("Built-in Audio Analog Stereo", "Analógica", False),
        ("JBL Go", "Bluetooth", True),
    ]


def test_default_sink_falls_back_to_pactl_info(monkeypatch):
    info = "Server Name: PulseAudio (on PipeWire 0.3.65)\nDefault Sink: alsa_output.x\n"
    monkeypatch.setattr(audio, "_run", fake_runner({("pactl", "info"): info}))
    assert audio.default_sink_name() == "alsa_output.x"


def test_without_pactl_everything_degrades(monkeypatch):
    monkeypatch.setattr(audio, "_run", missing_binary)
    assert audio.available() is False
    assert audio.default_sink_name() is None
    assert audio.list_sinks() == []
    assert audio.set_default("x") is False


def test_set_default_moves_streams_and_persists(monkeypatch, tmp_path):
    conf = tmp_path / "audio.conf"
    conf.write_text("# salida elegida\nOUTPUT=old\nVOLUME=80\n", encoding="utf-8")
    monkeypatch.setattr(audio, "AUDIO_CONF", str(conf))
    calls: list = []
    monkeypatch.setattr(
        audio,
        "_run",
        fake_runner(
            {
                ("pactl", "set-default-sink", "new"): "",
                ("pactl", "set-sink-mute", "new", "0"): "",
                ("pactl", "list", "short", "sink-inputs"): "12\t47\t88\tPipeWire\tfloat32le\n",
                ("pactl", "move-sink-input", "12", "new"): "",
            },
            calls,
        ),
    )
    assert audio.set_default("new") is True
    assert ("pactl", "move-sink-input", "12", "new") in calls
    assert conf.read_text(encoding="utf-8") == "# salida elegida\nOUTPUT=new\nVOLUME=80\n"


def test_persist_appends_when_missing(monkeypatch, tmp_path):
    conf = tmp_path / "audio.conf"
    monkeypatch.setattr(audio, "AUDIO_CONF", str(conf))
    audio._persist_output("sink-a")
    assert conf.read_text(encoding="utf-8") == "OUTPUT=sink-a\n"


def test_bt_devices(monkeypatch):
    out = (
        "Device AA:BB:CC:DD:EE:FF JBL Go 3\n"
        "Device 11:22:33:44:55:66\n"
        "[CHG] Controller 00:1A:7D:DA:71:13 Discovering: yes\n"
    )
    monkeypatch.setattr(bt, "_run", fake_runner({("bluetoothctl", "devices"): out}))
    assert bt.devices() == [
        ("AA:BB:CC:DD:EE:FF", "JBL Go 3"),
        ("11:22:33:44:55:66", "11:22:33:44:55:66"),
    ]


def test_bt_without_bluetoothctl(monkeypatch):
    monkeypatch.setattr(bt, "_run", missing_binary)
    assert bt.available() is False
    assert bt.devices() == []
    assert bt.is_connected("AA:BB:CC:DD:EE:FF") is False


def test_bt_is_connected(monkeypatch):
    info = "Device AA:BB:CC:DD:EE:FF (public)\n\tName: JBL Go\n\tConnected: yes\n"
    monkeypatch.setattr(
        bt, "_run", fake_runner({("bluetoothctl", "info", "AA:BB:CC:DD:EE:FF"): info})
    )
    assert bt.is_connected("AA:BB:CC:DD:EE:FF") is True


def test_timeouts_are_subprocess_errors():
    # The wrappers catch SubprocessError; TimeoutExpired must be one of them.
    assert issubclass(subprocess.TimeoutExpired, subprocess.SubprocessError)
