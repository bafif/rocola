# 03 · Boot and live mode

*English · [Español](03-boot-and-live.md)*

## Boot chain

```
Firmware (BIOS or UEFI x64)
  └─ GRUB
      └─ i386 kernel (686-pae) + initrd with live-boot
          └─ mounts filesystem.squashfs + overlay (tmpfs)   ← runs in RAM, doesn't write to the USB
              └─ systemd
                  ├─ rocola-display-setup.service   (video driver and mode: VGA / 15 kHz)
                  └─ getty@tty1 with autologin for `rocola`
                      └─ ~/.bash_profile → startx → rocola-session
                          ├─ PipeWire + WirePlumber + MPD   (audio, in the session)
                          └─ fullscreen SDL2 app
```

## live-boot + squashfs + overlay

The root filesystem is **read-only** (`filesystem.squashfs`); `live-boot` mounts an **overlay** in RAM
on top of it. Advantages:

- **Doesn't wear out the USB stick** (writes go to tmpfs).
- Lets you **try the jukebox before installing**.
- Consistent boots: every boot starts from the same state.

The flip side is that **live changes don't persist** (on purpose). Real persistence comes when you
**install** to disk, where the root is read-write and `/music` is a separate partition.

## Autologin + autostart (no desktop)

There's no desktop environment. To keep it light on i386/2 GB:

- `getty@tty1` with **autologin** for the `rocola` user.
- Its `~/.bash_profile` launches `startx` with `rocola-session` as the only client: **minimal Xorg** and
  the **fullscreen SDL2 app**, no window manager. If X or the app exits, the login session ends, getty
  logs back in on its own, and the UI starts again (kiosk).
- Audio lives in that same session: `rocola-session` starts PipeWire, WirePlumber and **MPD** (MPD
  isn't a system service; `mpd.service` is masked) and the app connects to MPD.

Relevant files (in `os/rootfs-overlay/`):

```
etc/systemd/system/getty@tty1.service.d/autologin.conf
etc/systemd/system/rocola-display-setup.service
home/rocola/.bash_profile        (autologin → startx)
opt/rocola/                      (the app)
usr/local/bin/rocola-session     (audio + MPD + app, inside X)
```

If the UI exits 5 times within 2 minutes, autologin stops relaunching it: tty1 stays on the console
showing the reason and how to retry, instead of a loop that takes over the screen.

## Boot menu

| GRUB entry | What it does |
|------------|--------------|
| "Rocola" (default) | the jukebox in the system's language (Spanish), with the firmware's generic video |
| "Rocola — English" | the same, in English (`rocola.lang=en`) |
| "Rocola — GPU / CRT 15 kHz (KMS)" | loads the video card's driver; needed for 15 kHz (see [05](05-display-crt-15khz.en.md)) |
| "Rocola — consola de recuperación · recovery console" | `rocola.noui`: tty1 stays at the console, no X |
| "Rocola — SSH por red · SSH troubleshooting" | the UI plus `sshd` (see [11](11-troubleshooting.en.md)) |
| "Rocola — CPU sin PAE · without PAE (kernel 686)" | the non-PAE kernel, for some Pentium M, VIA C3 and AMD Geode |

Since the live system keeps nothing between boots, this is where you pick the language on the stick;
later you can switch it from the app's menu (**"Language / Idioma"**), and installing saves it in
`/etc/rocola/language.conf`.

On the installed disk, "Rocola — consola de recuperación · recovery console" does the same as on the
stick, and the non-PAE kernel lives in GRUB's "Advanced options" submenu. Debian's "recovery mode"
entries are turned off: they ask for the root password, and root is locked.

## BIOS and UEFI x64

- **BIOS**: GRUB-PC from the MBR. Works on both 32- and 64-bit PCs.
- **UEFI x64**: GRUB-EFI amd64 from the ESP, which loads the **i386 kernel**. (Pure 32-bit UEFI isn't
  supported.)

## Services

`rocola-hostname` (writes `/etc/hostname` and `/etc/hosts`), `rocola-display-setup`,
`rocola-music-import` (puts the preloaded music in `/music`), `systemd-networkd` and `bluetooth` start
on their own. `rocola-ssh` and `rocola-selftest` also run on every boot, but exit right away unless the
kernel command line has `rocola.ssh` or `rocola.selftest`. `mpd.service` and `mpd.socket` are masked:
MPD is launched by `rocola-session`. `rocola-installer.service` is started by the menu, and
`rocola-usb-music@.service` by udev when a USB stick is plugged in.

## Debugging

To see why the UI didn't start: `journalctl -b | grep -iE 'startx|xinit|Xorg|rocola-session'` and
`/var/log/Xorg.0.log`. `rocola` is in the `systemd-journal` group, so from the console `journalctl`
shows logs for the whole system without root. More in [11](11-troubleshooting.en.md).

Next: [04 · Installer](04-installer.en.md).