# Rocola Architecture

*English · [Español](ARCHITECTURE.md)*

This document describes the system design: how the image is built, how it boots, how it gets installed, and how the subsystems fit together. For the details of each part, see [`docs/`](docs/).

## 1. Goal and constraints

A **bootable USB stick** that turns an old desktop PC into a dedicated **jukebox**.

| Constraint | Decision |
|-------------|----------|
| Old hardware (~2 GB RAM, 32-bit) | Debian **i386**, `686-pae` kernel (non-PAE `686` fallback) |
| OS base | **Container image `FROM i386/debian:bookworm`** (Podman; bookworm still ships a bootable i386 kernel; trixie dropped it) |
| Boot | **BIOS** (32- and 64-bit PCs) **+ UEFI x64** (`grub-efi-amd64` loads an i386 kernel) |
| Monitors | **31 kHz VGA + 15 kHz arcade/TV** with fixed modelines |
| Controls | USB **keyboard and/or joystick** encoder, autodetected (SDL) |
| App | **Custom SDL2 UI** (Python + pygame-ce) on top of **MPD** |
| Installation | **Live on the USB stick + manual trigger → guided installer** (never auto-formats) |
| Music | **Preloaded** + **import from a 2nd USB drive** into a persistent data partition |

## 2. Build pipeline (container → USB stick)

```
┌──────────────────────────────────────────────────────────────────────┐
│ os/Containerfile  (FROM i386/debian:bookworm)                          │
│   · minimal packages (Xorg, MPD, SDL2/pygame, GRUB…)                   │
│   · rootfs-overlay/  (systemd units, autologin, mpd.conf, xorg, app)   │
└───────────────┬──────────────────────────────────────────────────────┘
                │  podman build  →  podman export
                ▼
        out/rootfs.tar
                │
                │  image/Containerfile.builder (mksquashfs + xorriso + grub-mkrescue)
                ▼  build-image.sh   (REGULAR container, unprivileged; in and out via podman cp)
        out/rocola-i386.img  (hybrid ISO / isohybrid)
          · El Torito BIOS (GRUB i386-pc core) + UEFI x64 (BOOTX64.EFI)
          · /live/{vmlinuz,initrd.img,filesystem.squashfs}  (live-boot, RAM overlay)
                │  make flash  (dd / Etcher)
                ▼
        BOOTABLE USB STICK
```

The two decisions that matter most:
- **The OS is a container image.** All of the userland, the configuration and the app live in `os/`.
  The kernel, `live-boot` and GRUB are installed inside that same image so the exported rootfs is
  enough on its own.
- **Packaging into `.img`** (`mksquashfs` and `grub-mkrescue`) runs in a separate, ordinary, rootless
  container: `grub-mkrescue` builds the hybrid ISO in user space (xorriso and mtools), with no loop
  devices or privileges. The container doesn't mount the repo: the rootfs goes in and the image comes
  out via `podman cp`. That's why the build works on WSL2 and in CI, and the host needs nothing but
  Podman. Installing to disk (partitioning, `grub-install`) is done by the installer on the
  already-booted system, where there's a real `/dev/sdX`.

Details: [docs/02-build-pipeline.en.md](docs/02-build-pipeline.en.md).

## 3. Boot and "live" mode

```
Power on + USB stick
   └─► GRUB (BIOS or UEFI x64)
         └─► i386 kernel + initrd (live-boot)
               └─► mounts filesystem.squashfs with an overlay in RAM/tmpfs  (doesn't write to the USB)
                     └─► systemd: rocola-display-setup (driver and VGA/15 kHz mode)
                           └─► autologin of `rocola` on tty1 → startx → rocola-session
                                 └─► PipeWire + MPD (in the session)  +  fullscreen SDL2 app
```

- **Live-boot, squashfs and overlay**: the system runs in RAM, so it barely writes to the USB
  stick or wears it out, and you can try everything before installing.
- **Direct boot, no desktop**: just `Xorg` and the app in fullscreen, which is what an i386
  machine with 2 GB can handle well.

Details: [docs/03-boot-and-live.en.md](docs/03-boot-and-live.en.md).

## 4. Guided installer (cloning to disk)

**Manual** trigger from the live jukebox (menu → “Install to disk”; F10 or arcade button 3):

```
rocola-install (whiptail, as root on tty8; keyboard-driven)
  1. Asks for the language (Spanish | English) → saves it on the installed disk
  2. Detects disks (model, size)             → you pick the target (14 GB minimum)
  3. Typed anti-wipe confirmation             (shows what will be destroyed)
  4. Partitions the target (GPT):
        BIOSBOOT (ef02, BIOS) · ESP (FAT32, UEFI) · ROOT (ext4) · DATOS /music (ext4, persistent)
  5. Clones the OS:  rsync of the live system (/)  →  ROOT; the preloaded music → /music
  6. Asks for the monitor type (modern/VGA | 15 kHz) → persists the choice
  7. Installs GRUB on the target (BIOS + UEFI x64), generates fstab; same video mode as the live system
  8. Reboot → the PC boots the jukebox on its own from disk
```

The installer never formats a disk unless someone has selected it and confirmed.

Details: [docs/04-installer.en.md](docs/04-installer.en.md).

## 5. Video subsystem (VGA + 15 kHz)

The idea is for both kinds of CRT monitor to work without configuring anything after installing:

- On monitors with a usable EDID (VGA or modern), the standard modes are used.
- On a 15 kHz CRT (arcade or TV, without a reliable EDID), fixed 15 kHz modelines are forced,
  NTSC or PAL depending on the TV standard.
- The monitor type is chosen once, in the installer, and saved; from then on every boot applies it
  automatically.
- 15 kHz depends on the video card and the driver accepting it. The system can't tell whether the
  monitor is showing a picture, so it doesn't fall back to VGA on its own: if the CRT stays black,
  plug in a VGA monitor and change the mode in `/etc/rocola/display.conf`.

Details: [docs/05-display-crt-15khz.en.md](docs/05-display-crt-15khz.en.md).

## 6. Arcade controls

- Typical USB encoders (iPAC/Xin-Mo/zero-delay) show up as a **keyboard** and/or **joystick**.
- The app uses **SDL2** to read both and **autodetects** whichever device is present.
- Action mapping (up/down, select, back, volume, etc.) with defaults in
  `app/rocola/input.py`, adjustable via `[keys]` and `[buttons]` in `rocola.toml`.

Details: [docs/06-arcade-controls.en.md](docs/06-arcade-controls.en.md).

## 7. The app (UI + audio)

```
┌────────────────────────────┐        IPC (MPD socket)        ┌─────────────┐
│  app/rocola  (SDL2)         │  ───────────────────────────► │   MPD       │
│   · render fullscreen       │  play/pause/next/seek/queue    │  (audio     │
│   · navigation + branding   │  ◄───────────────────────────  │   engine)   │
│   · keyboard/joystick input │        status / library        └─────┬───────┘
└────────────────────────────┘                                      │
                                                            /music (library)
```

- **MPD** handles the library, the queue and playback (lightweight, ideal for i386).
- **The UI** is an MPD client: it shows covers/lists and "now playing", and sends commands.
- It renders at the monitor's native resolution (320×240/640×480 on a CRT, or higher on VGA/modern).
- It speaks Spanish or English: it starts in the system's language (or the one from the "Rocola —
  English" GRUB entry), and the "Language / Idioma" menu option switches it and saves it in
  `/etc/rocola/language.conf`.

Details: [docs/07-rocola-app.en.md](docs/07-rocola-app.en.md).

## 8. Data and persistence

| Partition | FS | Role | Survives reinstall |
|-----------|----|-----|--------------------|
| ESP | FAT32 | UEFI boot | n/a |
| ROOT | ext4 | system (OS clone) | rewritten |
| DATOS `/music` | ext4 | the music | **yes** |

Reinstalling or updating the OS doesn't erase the music.

Details: [docs/08-music-management.en.md](docs/08-music-management.en.md).

## 9. Repository layout

See [README.es.md](README.md#layout). Each top-level folder maps to a
subsystem of this architecture and has its matching doc in [`docs/`](docs/).