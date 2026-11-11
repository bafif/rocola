# 12 · Verification (what's tested and what isn't)

*English · [Español](12-verificacion.md)*

How the jukebox is tested and what is tested today. What still depends on physical hardware is at the
end.

## Automated tests

```bash
make app-test      # the app with pytest, no display or audio (SDL's dummy driver and a fake MPD)
make app-lint      # ruff
make os-test       # the OS scripts that run without root (the music import)
make theme-check   # contrast, accented letters and files of every theme
```

The app's tests also check that every on-screen text is in both languages, that every document has
its pair in the other language and that there are no broken links. CI (`.github/workflows/ci.yml`)
runs ruff, pytest, shellcheck on the scripts and the import test on every push to `main` and every
pull request. The image isn't built in CI: it's heavy, and it's built by hand.

## Trying the image in QEMU

```bash
make rootfs && make image
file out/rocola-i386.img                          # ISO 9660 with a boot sector
podman run --rm -i rocola-builder \
  sh -c 'cat > /tmp/r.img && xorriso -indev /tmp/r.img -report_el_torito plain' < out/rocola-i386.img
                                                  # one BIOS entry and one UEFI entry
qemu-system-i386 -enable-kvm -m 2048 -cdrom out/rocola-i386.img          # BIOS
qemu-system-x86_64 -enable-kvm -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=/tmp/vars.fd -cdrom out/rocola-i386.img   # UEFI x64
```

`/tmp/vars.fd` is a copy of `OVMF_VARS.fd`; the OVMF paths change from one distribution to another.
With the default entry, the jukebox comes up full screen with MPD connected; with no music, it says so
and points to the menu to import songs.

## The installer, unattended

`rocola-selftest.service` runs the installer in unattended mode when the kernel boots with
`rocola.selftest`; on any other boot it exits without doing anything. To try it:

1. Boot the ISO in QEMU with a second, empty disk of 14 GB or more.
2. In the GRUB menu, edit the entry (`e` key) and add `rocola.selftest` and
   `rocola.selftest.target=/dev/sdX` with the empty disk (`/dev/sdb` by default) to the `linux` line.
   With `rocola.selftest.keep_music=yes` it reinstalls keeping `/music`.
3. The console shows the partition table, the end of the installer's log and `SELFTEST_RESULT: OK`
   (or `FAIL(<code>)`), and the machine powers off.
4. Boot from that disk alone: the jukebox opens on its own, via BIOS and via UEFI.

## What is tested

In QEMU/KVM, with the ISO built from the repository:

- **Live boot** to the full-screen jukebox with MPD connected, with the default entry: via BIOS
  (800×600 through VBE, at 32 and at 16 bits of color) and via UEFI x64 (OVMF's GOP, 1280×800).
  Screenshots: [BIOS](screenshots/qemu-boot-ui.png) and [UEFI](screenshots/qemu-uefi-boot-ui.png).
- **Installing** to an empty disk: it partitions, clones, installs GRUB for BIOS and UEFI, and the
  disk boots on its own to the jukebox via BIOS and via UEFI, several times in a row
  ([BIOS](screenshots/installed-bios-boot-ui.png), [UEFI](screenshots/installed-uefi-boot-ui.png)).
  A disk under 14 GB is rejected with a message that says so.
- **Reinstalling while keeping the music**: the songs imported on the disk are still in the library.
- **Importing from a second USB stick**, plugged in at boot or while the jukebox is running: the audio
  gets in whatever its case (`TEMA01.MP3`) and with its covers (a `cover.jpg` appears next to a
  `Folder.jpg`), and photos and folders with no audio stay out
  ([screenshot](screenshots/qemu-bios-usb-import.png)).
- **Preloaded library**: with files in `os/rootfs-overlay/opt/rocola/music/`, the live system shows
  them without plugging anything in.
- **The app on the image**: browsing by artist and album, "Now playing" with the cover, picking a song
  with the queue finished (the chosen one plays), a `[keys]` mapping in `rocola.toml` and
  "Test controls".

The screenshots from these tests show the interface from before the Ámbar theme.

## On real hardware

The live system boots on a real PC from a Ventoy stick. Still to be tried:

- 15 kHz video on an arcade monitor or a TV: it depends on the video card and the driver, and QEMU
  can't check it.
- A real USB arcade encoder (the keyboard mapping is tested in QEMU).
- Importing from a second stick, the preloaded library and reinstalling while keeping `/music`.
- What the project is for: an old desktop with a CRT and arcade controls.

Next: [13 · Writing with Rufus](13-rufus-windows.en.md).
