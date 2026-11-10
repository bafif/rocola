# Modelines

*English · [Español](README.md)*

Video profiles that `rocola-display-setup` inserts into the Xorg config.

- **`15khz.conf`**: modelines for arcade/TV CRTs (15 kHz). Reference values;
  tune them per monitor (timings and position vary). For VGA/modern displays no file is
  needed: Xorg autodetects via EDID.

## Tuning a 15 kHz CRT

1. Boot with `MODE=crt15` in `/etc/rocola/display.conf`.
2. If the picture comes out shifted or without sync, adjust the corresponding `Modeline`.
3. When you touch a modeline, check the frequencies: horizontal = clock ÷ horizontal total (between
   15.0 and 16.5 kHz, which is what `rocola-display-setup` declares to Xorg) and vertical = horizontal ÷
   vertical total (double if interlaced). Xorg silently discards an out-of-range modeline.
   `switchres` computes them on the fly, but it isn't in Debian and doesn't ship in the image.

## Hardware warning

15 kHz requires a **GPU/driver compatible** with these modelines on the analog (VGA)
output. On incompatible hardware, use `MODE=vga`. See
[../../docs/05-display-crt-15khz.en.md](../../docs/05-display-crt-15khz.en.md).