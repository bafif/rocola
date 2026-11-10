# 01 · Overview

*English · [Español](01-overview.md)*

## The problem

There are lots of old desktop computers lying around. Turning one into an arcade jukebox usually
means installing an OS, drivers and software, setting up video (even more so if the monitor is a
CRT), mapping controls and getting everything to boot on its own. It's tedious, and you have to
repeat it for every machine.

## The solution

A **single USB stick** that:

1. **Boots a ready-to-use jukebox** on any PC (live mode, without touching the disk).
2. **Clones itself to the internal disk** with a manually triggered guided installer.
3. Leaves the PC turned into a **permanent jukebox**: it opens on its own at power-on, is driven with
   arcade controls and works on both modern and CRT monitors (VGA and 15 kHz) with no further
   configuration.

## Goals

- **Fast**: from old PC to jukebox in minutes, repeatable machine after machine.
- **Zero post-install friction**: power on → jukebox. No keyboard/mouse needed for everyday use.
- **Modest hardware**: i386, ~2 GB RAM, old GPUs, CRTs included.
- **Brandable**: its own look (logos, colors, fonts) without touching the logic.
- **Free**: 100% free software (MIT).

## Non-goals (for now)

- It's not a general-purpose media center (no video/photos/streaming): it's a music jukebox.
- It doesn't target pure 32-bit UEFI (rare). It does target BIOS and x64 UEFI.
- It doesn't guarantee 15 kHz on every GPU: that depends on the hardware (see [05](05-display-crt-15khz.en.md)).

## Glossary

- **Rocola**: jukebox; the machine/medium for choosing and playing music.
- **Live**: a system that runs from the USB stick without being installed (in RAM/overlay).
- **15 kHz**: the horizontal frequency of arcade/TV CRTs (vs. 31 kHz+ for VGA monitors).
- **MPD**: Music Player Daemon, the audio engine.
- **Modeline**: the description of a video mode (resolution and timings) passed to Xorg;
  the 15 kHz ones live in `display/modelines/`.

Next: [02 · Build pipeline](02-build-pipeline.en.md).