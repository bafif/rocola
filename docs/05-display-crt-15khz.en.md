# 05 · Video: VGA and 15 kHz CRT

*English · [Español](05-display-crt-15khz.md)*

The jukebox has to work on **modern or VGA monitors (31 kHz or higher)** and on **arcade CRTs or TVs
(15 kHz)** with no configuration after install. This is the trickiest part of the project, and here
I explain how I approached it and where its limits are.

## The problem

- Modern/VGA monitors report their modes via **EDID** → standard autoconfiguration.
- **15 kHz CRTs** (arcade, TVs over RGB/composite/SCART) **don't** provide reliable EDID and need
  **low-frequency modelines** (e.g. 320×240@60, 640×480i@60) that the regular driver doesn't generate.
- Sending 31 kHz to a 15 kHz CRT shows no picture (or damages it). You have to **force** 15 kHz.

## Strategy

1. **A single choice, at install time**: the installer asks for the monitor type (automatic, VGA or
   15 kHz) and saves the answer to `/etc/rocola/display.conf`. On every boot
   `rocola-display-setup` applies it and writes the Xorg config.
2. **Automatic and VGA**: a safe VGA config; Xorg takes the monitor's modes from **EDID** when
   available. Automatic mode doesn't pick 15 kHz even when there's no EDID: an old VGA monitor
   doesn't provide it either, and sending it 15 kHz would leave it black. 15 kHz has to be asked for
   on purpose.
3. **15 kHz**: applies the fixed modelines from `display/modelines/15khz.conf` and picks the
   resolution based on the TV standard (`TV_STANDARD`): 640×480i at 60 Hz for NTSC, 768×576i at
   50 Hz for PAL. `PREFERRED_RES` overrides it. It needs KMS: boot with the GRUB entry
   "Rocola — GPU / CRT 15 kHz (KMS)".
4. **No automatic fallback**: the system can't tell whether the monitor is showing a picture. If a
   CRT stays black, plug in a VGA monitor and change `MODE` in `/etc/rocola/display.conf` (or
   reinstall choosing VGA).

```
boot → rocola-display-setup
          ├─ reads /etc/rocola/display.conf  (mode chosen at install)
          ├─ auto / vga → safe VGA config; Xorg uses the EDID modes
          └─ crt15      → fixed 15 kHz modelines (NTSC or PAL per TV_STANDARD)
```

## Components

- **modelines** (`display/modelines/15khz.conf`): 320×240 and 640×480i (NTSC, 60 Hz), 384×288 and
  768×576i (PAL, 50 Hz). VGA doesn't need a file: Xorg gets them from EDID.
- **Xorg**: a minimal config that accepts custom modelines; the SDL2 app renders at the active mode.
- `switchres`, which calculates modelines tailored to each CRT, isn't in Debian and isn't included
  in the image.

## The hardware limit

15 kHz doesn't work on just any machine: you need a graphics card and a driver that accept
low-frequency modelines through the right output (usually the analog VGA one). The cards and
drivers that handle this best are the ones documented by the arcade community (GroovyArcade,
CRT_EmuDriver). On hardware that doesn't accept them, the jukebox still works with a VGA or modern
monitor (`MODE=vga`).

In other words: with VGA or a modern monitor it always works; with 15 kHz, wherever the hardware
allows it.

## The app and low resolution

The SDL2 UI draws directly at 320×240 or 640×480, so it looks good on a CRT, with no ugly scaling.
The branding and screen layouts take the CRT "title-safe area" into account.

Next: [06 · Arcade controls](06-arcade-controls.en.md).