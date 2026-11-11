# 12 · Verification (what's tested and what isn't)

*English · [Español](12-verificacion.md)*

Here I keep track of what I built and booted end to end, what problems came up along the way and
what still needs testing, which is mostly whatever depends on physical hardware. Everything in this
document was built and tested on an x86-64 PC with containers (which run i386 natively) and QEMU/KVM.

## What works end to end

1. **OS build** (`make rootfs`). The OS image (`FROM i386/debian:bookworm`) builds with all the
   packages, the overlay, the systemd symlinks and the initramfs with live-boot. The layer weighs
   about 478 MB.
2. **Rootfs contents.** The architecture is i386, with the `6.1.0-686-pae` kernel and its initrd;
   the initrd includes `sr_mod`, `squashfs` and `overlay` (`MODULES=most`). The `rocola` user has
   its groups, `grub-install`, `update-grub` and `efibootmgr` are present (the installer needs them)
   and the app imports fine (pygame 2.1.2 with SDL 2.26.5). The services that start by themselves
   are `rocola-hostname`, `rocola-display-setup`, `rocola-selftest`, `rocola-music-import`,
   `rocola-ssh` (which only turns sshd on with `rocola.ssh`), `systemd-networkd` and `bluetooth`.
   `mpd.service` and `mpd.socket` are masked: MPD is started by `rocola-session` inside the `rocola`
   session (see [14](14-audio.en.md)), and the UI starts from the tty1 autologin, with no service of
   its own. That is what `os/Containerfile` sets today; in May `mpd` and `rocola` were system
   services, and the next build checks it again on the image.
3. **Headless UI rendering** (`SDL_VIDEODRIVER=dummy`). The library, now-playing and menu scenes
   render with the theme (today Ámbar: its artwork, fonts and colors). You can see them in
   [screenshots/ui-menu.png](screenshots/ui-menu.png) and [ui-nowplaying.png](screenshots/ui-nowplaying.png).
4. **Bootable image** (`make image`). `grub-mkrescue` produces `out/rocola-i386.img`, a hybrid ISO
   with a dual El Torito catalog (a BIOS entry with GRUB i386-pc and a UEFI entry with `efi.img`)
   plus an MBR so it can be written with `dd`. I checked it with `xorriso -report_el_torito`.
5. **BIOS boot in QEMU, with KVM.** The whole path works:

   ```
   GRUB → i386 kernel → live-boot mounts /live/filesystem.squashfs (overlay in RAM)
        → systemd (multi-user) → autologin of rocola on tty1 → startx
        → rocola-session (PipeWire, MPD) → Xorg on tty1 → full-screen jukebox UI,
          with MPD connected
   ```

   The screenshot is [screenshots/qemu-boot-ui.png](screenshots/qemu-boot-ui.png). It shows "No
   music. Import songs", meaning MPD is connected and the library is empty because that test build
   didn't include any music.

6. **UEFI x64 boot in QEMU, with OVMF.** The full firmware chain works too:

   ```
   OVMF (UEFI x64) → El Torito UEFI → GRUB EFI amd64 → i386 kernel → live-boot
        → systemd → mpd → Xorg → full-screen jukebox UI
   ```

   This confirms the project's core decision: a 64-bit GRUB loads the i386 kernel without any
   trouble. On the serial console you can see `BdsDxe … → Welcome to GRUB! → Booting 'Rocola'`. The
   screenshot is [screenshots/qemu-uefi-boot-ui.png](screenshots/qemu-uefi-boot-ui.png).

7. **End-to-end disk installation, in QEMU.** This is the device's complete flow:

   ```
   live + empty 2nd disk → rocola-install (unattended) → GPT partitioning
        (BIOSBOOT+ESP+ROOT+MUSIC) → rsync of the live system → GRUB BIOS+UEFI → fstab
   → the disk boots on its own (no USB stick) → the jukebox opens by itself, via BIOS and UEFI
   ```

   The installation finishes with `SELFTEST_RESULT: OK`: it partitions, clones, runs `grub-install`
   for i386-pc and x86_64-efi, and `update-grub` detects the target's kernel. The installed disk
   booting on its own can be seen in [screenshots/installed-bios-boot-ui.png](screenshots/installed-bios-boot-ui.png)
   (BIOS) and [screenshots/installed-uefi-boot-ui.png](screenshots/installed-uefi-boot-ui.png) (UEFI).

   To automate it, the installer has an unattended mode (`ROCOLA_UNATTENDED=1`) that triggers
   `rocola-selftest.service`; that service only acts if the kernel boots with `rocola.selftest` on
   the command line, so in normal use it does nothing. The test scripts are in `out/test/`
   (`installer-selftest.sh` and `boot-installed.sh`).

   I also booted the installed disk several times in a row and every boot reached the full-screen
   jukebox. That test is what uncovered the video race that left one in three boots at the console
   (it's in the table below). Since I removed the resume wait from the initramfs, the UI shows up
   after 55 to 65 seconds in QEMU/KVM, about 30 seconds faster than before.

### How to reproduce it

```bash
make rootfs && make image
file out/rocola-i386.img
podman run --rm -i rocola-builder sh -c 'cat > /tmp/r.img && xorriso -indev /tmp/r.img -report_el_torito plain' \
  < out/rocola-i386.img                                            # lists BIOS and UEFI
# Live boot to the UI (BIOS):
qemu-system-i386  -enable-kvm -m 2048 -cdrom out/rocola-i386.img
# Live boot to the UI (UEFI x64):
qemu-system-x86_64 -enable-kvm -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=/tmp/vars.fd -cdrom out/rocola-i386.img
# End-to-end installer and booting the installed disk: out/test/installer-selftest.sh and boot-installed.sh
```

## Problems that came up during testing, and how I fixed them

Actually building the image and booting it brought several real problems to light. I'm writing them
down because more than one could come back if the build or the installer changes.

| Problem | Symptom | Fix |
|----------|---------|---------|
| Builder with loop devices | `make image` failed on WSL2 | switch to `grub-mkrescue`, which doesn't need privileges |
| `grub-mkrescue` arguments | xorriso rejected `-quiet` and `--volid=` | `-- -volid ROCOLA` (mkisofs syntax) |
| rocola.service didn't start | tty1 stayed at the text login, with no UI | mask `getty@tty1` and make the service a getty replacement (without `Conflicts`, which made systemd discard it) |
| squashfs without `/boot` | the installed system ended up with no kernel | include `/boot` in the squashfs |
| Xorg without root | `Cannot open virtual console` | `Xwrapper.config` with `needs_root_rights=yes` |
| The installer wiped `/music` | `--zap-all` destroyed the partition that was supposed to be kept | when keeping the music, don't repartition; only reformat ESP and ROOT |
| `grub-install` was missing | the installer couldn't install GRUB | `grub2-common`, `efibootmgr` and `mtools` in the image |
| GPT without a BIOS Boot Partition | `grub-install i386-pc` failed ("no BIOS Boot Partition") and the PC wouldn't boot via BIOS | add a 2 MiB `ef02` partition to the layout |
| The installer accepted a failed installation | `{ … } \|\| die` disables `set -e`, so errors from grub, rsync or mkfs got lost and it ended in OK | `trap … ERR` and remove the `\|\| die` from the group |
| `grub-install` in a chroot without `/dev` | rsync excludes `/dev`, `/proc` and `/sys`, the `mount --bind` calls failed and GRUB asked "is /dev mounted?" | `grub-install` outside the chroot with `--boot-directory`, and `mkdir -p` of the mount points for `update-grub` |
| Video race: the jukebox sometimes booted without UI | `rocola-display-setup`, with `DefaultDependencies=no`, ran before the root was remounted read-write; it couldn't write `xorg.conf`, Xorg started with no configuration and you got the console instead of the jukebox (one in three boots of the installed disk) | remove `DefaultDependencies=no`, order it `After=local-fs.target` and make the script tolerate a read-only `/etc` |
| rsync aborted valid installations | cloning a live system returns 24 or 23 for files that change during the copy, and with `set -e` and the trap it was treated as a fatal error | accept 24 and 23 as non-fatal |
| The initramfs waited about 30 s for resume | the initrd inherited from the live system looked, on every installed boot, for a suspend device that doesn't exist | `RESUME=none` and `update-initramfs -u` in the chroot |
| Black screen for about 30 s at boot | the app blocked in `_connect_mpd` (up to 30 s) before drawing anything | draw first, connect to MPD from the loop and refresh the library on connect |
| The selftest dragged in `udev-settle` | the selftest unit pulled a deprecated service into every boot | drop the dependency and run `udevadm settle` inside the script, only in the selftest |
| `systemctl enable` in the build | could fail without systemd running | the `*.wants/` symlinks are created by hand |
| Flaky network | `apt` cut the build short | `Acquire::Retries` and a retry of the install |
| `make image` rebuilt everything | the rootfs got built twice | the `ensure-os` guard |
| The default entry didn't show the UI (QEMU, BIOS and UEFI) | `insmod all_video` loaded GRUB's `bochs` driver, which grabs QEMU's VGA and leaves an 800×600 framebuffer at 24 bpp; the firmware framebuffer doesn't change modes and Xorg 21 with `fbdev` doesn't accept 24 bpp ("Specified fbbpp (24) is not a permitted value"), so X died with "FBIOPUT_VSCREENINFO succeeded but modified mode" | GRUB loads only the firmware drivers (GOP/UGA, VBE/VGA); on BIOS it asks for 32 bpp modes first and then 16 (some VBE BIOSes have 24 bpp modes), and with 16 or 8 bpp `rocola-display-setup` gives Xorg the same `DefaultDepth` |
| USB import | `TEMA01.MP3` or `Folder.jpg` weren't picked up (rsync filters are case-sensitive) and every photo and folder on the stick got copied | case-insensitive filters, only audio and `cover.*`/`folder.*`, and `--prune-empty-dirs` |
| The initrd picked up the host's swap | `update-initramfs` during the build took the swap of the machine building the image as the resume device | `RESUME=none` in the rootfs |
| The installed disk always booted with KMS | without `/etc/default/grub`, `update-grub` set up the disk without `nomodeset` even if the live system had booted with the default entry | the installer writes `/etc/default/grub.d/rocola-video.cfg` with the same video settings as the live system (except with a 15 kHz CRT) |
| The installation stick showed up as a target | with the medium mounted as a whole device, `LIVE_DISK` ended up as `/dev/` | if there's no parent disk, the disk is the medium itself |
| A small disk gave a cryptic error | ROOT takes a fixed 12 GiB and with less `sgdisk` failed halfway through | 14 GB minimum, stated in the menu and rejected with a clear message |
| Picking a song with the queue finished | the first song in the queue played instead of the chosen one (MPD has no current song and `play` starts from position 0); when paused, the previous one resumed | `playid` of the chosen song when nothing is playing |
| Covers from the stick not showing | MPD's `albumart` only looks for `cover.png`, `cover.jpg` or `cover.webp` spelled exactly like that, not `Folder.jpg` | the import adds a `cover.<ext>` (hard link) in each folder |

## Tests from October 31, 2026 (QEMU/KVM)

- The app tests (`make app-test`, with pytest, dummy SDL and a fake MPD) pass, and CI also runs
  ruff and shellcheck.
- Import from a second USB: with a FAT stick holding two WAVs plugged in at boot, the library shows
  both songs (udev triggers it via `rocola-usb-music@.service`).
- The `console-getty` race: if it isn't masked, the boot can end up at `rocola login:` on the
  console instead of opening the UI. It happened to me on the first boot of this test.
- The default entry ("Rocola", with `nomodeset` and fbdev) on BIOS left GRUB in text mode and the
  kernel booted without a framebuffer, so Xorg said "no screens found". Now GRUB switches to
  `gfxterm` on BIOS and the kernel has a framebuffer. After that it failed in `ScreenInit` because of
  the color depth (the 24 bpp from the table above), and the same happened on UEFI. That's fixed now:
  the default entry opens the UI on BIOS (800×600 at 32 bpp via VBE, and I also tried 16 bpp) and on
  UEFI (OVMF's GOP, 1280×800 at 32 bpp) in QEMU/KVM, with the ISO built from what's committed. It
  still needs testing on a real PC via BIOS.
- Hot import: with the jukebox running I plugged in a FAT stick with `Album/TEMA01.MP3`,
  `Album/b.flac` and `DCIM/IMG_0001.JPG`. After a few seconds the library shows both songs, and
  neither the photo nor `DCIM/` is in `/music`. Screenshot:
  [screenshots/qemu-bios-usb-import.png](screenshots/qemu-bios-usb-import.png).
- The installer from the default entry: the unattended installation to a 16 GB disk finishes with
  `SELFTEST_RESULT: OK`, the disk's `grub.cfg` has `nomodeset` and the 32 and 16 bpp modes, and the
  disk boots on its own to the UI via BIOS and UEFI. A 6 GB disk is rejected with the minimum size
  message.
- Reinstalling while keeping the music (`rocola.selftest.keep_music=yes`): I did a clean install,
  the installed disk imported two songs from a stick, I reinstalled keeping the data ("keeping data
  on /dev/sda4", `SELFTEST_RESULT: OK`) and the disk booted without the stick with both songs still
  in the library.
- Preloaded library: with two files in `os/rootfs-overlay/opt/rocola/music/` before
  `make rootfs`, the live system boots and the library shows them without plugging anything in.
- Mappings from `rocola.toml`: with `m = "menu"` under `[keys]` inside the image, the `m` key opens
  the menu.
- Test controls: F10 enters "Test controls"; `n` and the space bar show up as
  `Key "n" -> next` and `Key "space" -> playpause`, and after 15 seconds without touching anything
  it goes back to the menu by itself.

## Tests from November 1, 2026 (QEMU/KVM)

I used the ISO built from what's committed, with the default entry on BIOS (800×600 at 32 bpp via
VBE) and a FAT stick plugged in at boot. The stick had 10 WAVs with ID3 tags in `Artista/Álbum/`
(a made-up demo library) and a `Folder.jpg` per album.

- Import with covers: the library shows "All songs" (10) and the three artists, and in `/music`
  each album has its `cover.jpg` next to the `Folder.jpg`.
- Navigation: Enter on an artist shows "All by …" and their two albums (the 1988 one before the
  1991 one); Enter on an album shows its numbered tracks.
- Playback: Enter on a track opens "Now playing" with the album cover, the title, the artist, the
  album and `[play]`. Pressing Esc three times goes back through the album and the artist to the
  artist list, with the same artist selected.
- Picking with the queue finished, against the image's MPD (0.23.12): before, the first song in the
  queue played again; now the chosen one plays.

## What still needs testing on hardware

Everything above is tested in QEMU. What follows needs a real machine:

- 15 kHz video for an arcade CRT or a TV depends on the graphics card and the driver, and there's
  no way to check it in QEMU.
- Arcade controls: the keyboard and joystick mapping is done and the UI responds in the render, but
  I haven't tested it with a real USB encoder.
- Import from a second USB is tested in QEMU (at boot and hot); it still needs a real stick.
- The preloaded library is tested in QEMU in live mode; it still needs hardware.
- Reinstalling while keeping `/music` was tested in QEMU on October 31, 2026; it still needs a real
  disk.
- And most importantly, the actual goal of the project: an old desktop with a CRT and arcade
  controls.

The plan for that is to write the `.img` to a USB stick (`make flash`) and boot it on an old
desktop, via BIOS and, if the machine has it, via UEFI. Then hook it up to a 15 kHz CRT with an
arcade encoder, and on that same machine import music from a second stick and reinstall keeping
`/music`.