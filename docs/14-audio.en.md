# 14 · Audio: output, PipeWire and Bluetooth

*English · [Español](14-audio.md)*

The goal is for it to play on as many old PCs as possible: analog output (the motherboard's line-out
or headphone jack), HDMI or DisplayPort, USB (a DAC or headphones) and Bluetooth (an A2DP speaker or
headset). And the output should be visible and selectable from the UI with the arcade controls.

## The problem

A "default" sound card isn't enough:

- On a PC with several cards (motherboard, HDMI, USB), ALSA's `default` points to just one of them,
  usually the motherboard's. If you plug in USB headphones, the audio comes out somewhere you're not
  listening.
- Many cards boot with the hardware mixer muted or at 0, so you hear nothing even when it's the
  right card.
- Bluetooth isn't an ALSA card: it needs a sound server to route it.

## How it works

Audio goes through **PipeWire** (with WirePlumber and `pipewire-pulse`), which runs in the `rocola`
user's graphical session. **MPD**, the jukebox engine, runs in that same session rather than as a
system service, so it shares that PipeWire instance, and it plays to the default sink. Choosing the
output means choosing PipeWire's default sink, and the same mechanism works for analog, HDMI, USB and
Bluetooth.

```
rocola session (startx → rocola-session)
   ├─ unmutes the hardware mixer (amixer, safety net)
   ├─ starts PipeWire + WirePlumber + pipewire-pulse
   ├─ rocola-audio-default → picks the default sink (heuristic / audio.conf)
   └─ MPD (type "pulse") ─→ pipewire-pulse ─→ default sink
                                                  ├─ analog / HDMI / USB (ALSA)
                                                  └─ Bluetooth A2DP (libspa-bluetooth)
```

### Choosing the default sink

`rocola-audio-default` does this at startup (inside the session), reading `/etc/rocola/audio.conf`:

- `OUTPUT=auto` (the default) uses this order: connected Bluetooth, USB, analog, HDMI and, if there's
  none of those, the first sink. USB comes before the motherboard's analog output because analog is
  always there even with nothing plugged in; with analog first, USB headphones would stay silent at
  boot.
- `OUTPUT=<text>` picks the first sink whose name contains `<text>` (for example `usb`, `analog`,
  `hdmi`, `bluez`, or an exact name from `pactl list short sinks`).
- `VOLUME=80` is the initial volume of the chosen sink.

The output you pick from the app's menu is saved to `audio.conf` (`OUTPUT=<sink>`), so it survives a
reboot.

## In the UI

In the menu (**F10** key or the menu button):

- **Audio output** lists PipeWire's sinks and marks the current one with `*`. Move with the arrows;
  Enter sets the output and plays a test sound (a short voice clip from alsa-utils) so you can
  confirm it by ear. At the bottom there's "+ Pair Bluetooth…".
- **System info** shows the active audio output, the audio driver (`/proc/asound/modules`)
  and the video driver, the resolution, the IP, the kernel and a few other things. It's useful for
  troubleshooting and for knowing which IP to SSH into.

## Bluetooth

- `bluez` provides the daemon (`bluetooth.service`) and `bluetoothctl`; the `libspa-0.2-bluetooth`
  plugin makes a connected speaker or headset show up as a PipeWire sink. `/etc/bluetooth/main.conf`
  powers on the adapter at boot (`AutoEnable=true`), and devices marked as *trusted* reconnect on
  their own.
- To pair: menu, "Audio output", "Pair Bluetooth…". This opens a screen inside the app (arrows and
  Enter) that scans for devices, lists them and runs `pair`, `trust` and `connect`, each with its own
  `bluetoothctl`, which waits for BlueZ's reply before exiting; pairing is "just works", no PIN. It
  works as the `rocola` user, without root, thanks to the D-Bus policy for the `bluetooth` group. When
  you go back, the Bluetooth sink shows up in the selector: pick it and try the test sound.
- Over SSH or from the console there's `rocola-bt-pair` (a whiptail TUI), which does the same pairing
  without the graphical interface.
- Watch out for the hardware: many old desktop PCs don't have Bluetooth and you'll need a USB dongle
  (its firmware is usually in the `firmware-*` packages that already ship in the image).

## Common problems

PipeWire and MPD live in the `rocola` session (tty1). Over SSH you have to target that session, not
the SSH one:

```bash
U=$(id -u rocola)
RUN="runuser -u rocola -- env XDG_RUNTIME_DIR=/run/user/$U"   # there's no sudo in the image

$RUN pactl info                      # is PipeWire responding?
$RUN pactl list short sinks          # available sinks (stable names)
$RUN pactl get-default-sink          # current output
$RUN pactl set-default-sink NAME     # change the output by hand
$RUN paplay --device=NAME /usr/share/sounds/alsa/Front_Center.wav   # test sound
$RUN wpctl status                    # PipeWire/WirePlumber tree
$RUN rocola-audio-default            # re-apply the heuristic / audio.conf

bluetoothctl                         # scan on / pair / trust / connect
amixer -c 0 scontrols                # hardware mixer (mute/volume) of card 0
mpc status; mpc outputs              # MPD status
```

If you hear nothing, in this order:

1. Does `pactl info` respond? If not, PipeWire didn't start in the session.
2. Is the default sink the right one? (`get-default-sink`). Change it and try the test sound.
3. Is the hardware mixer muted? `amixer -c N` and then `sset Master/Speaker/Headphone
   unmute 80%` (the session already tries this at startup, just in case).
4. If it's Bluetooth, is there an adapter? (`bluetoothctl list`). No dongle, no Bluetooth.

Next: [01 · Overview](01-overview.en.md) · Back to the
[documentation](../README.md#more-documentation).