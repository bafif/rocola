# 02 · Build pipeline

*English · [Español](02-build-pipeline.md)*

From code to USB drive in three steps: **OS (container) → rootfs → bootable image**.

```
os/Containerfile ──build──► OS image ───────export──► out/rootfs.tar
                                                          │
                    image/build-image.sh (unprivileged)   │
                                                          ▼
                                               out/rocola-i386.img ──flash──► USB stick
```

## Host requirements

- **Podman** (rootless is fine) and **make**. That's it.
- On **x86-64** CPUs, `linux/386` containers run natively (no emulator needed).
  On hosts that can't, register binfmt once with your distribution's `qemu-user-static`
  (on Arch, `qemu-user-static` and `qemu-user-static-binfmt`; on Debian and Ubuntu, `qemu-user-static`).
- `make image` runs in a **regular** container: it doesn't need `--privileged`, loop devices or
  `/dev` (it uses `grub-mkrescue`). That's why it works on **WSL2** and in CI. It doesn't mount anything from the repo either:
  the rootfs goes in and the image comes out via `podman cp`.

## Step 1 — OS as a container image (`make rootfs`)

`os/Containerfile` starts from `i386/debian:bookworm` and installs the minimal set (see `os/packages.list`):
Xorg, MPD, SDL2/pygame, the `linux-image-686-pae` and `linux-image-686` kernels (the latter as a non-PAE
fallback), `live-boot`, GRUB, etc. If an initrd ends up without `live-boot`, the build stops right there. Then
it copies `os/rootfs-overlay/` (configs, systemd units, the app) on top of the rootfs.

> Why bookworm: Debian 13 (trixie) dropped the i386 kernel/installer. For a **bootable** i386
> system, bookworm is the right base.

## Step 2 — Export the rootfs (`make export`)

`podman create` + `podman export` dump the image's filesystem to `out/rootfs.tar`. Since the
kernel, `live-boot` and GRUB were installed in step 1, the rootfs is **self-contained**.

## Step 3 — Build the bootable image (`make image`)

`image/Containerfile.builder` brings the tooling (`mksquashfs`, `xorriso`, `mtools`, `grub-pc-bin`,
`grub-efi-amd64-bin`). `make image` creates the container, copies `rootfs.tar` into `/work` with
`podman cp`, starts it and pulls `rocola-i386.img` out the same way. `build-image.sh`:

1. Unpacks `rootfs.tar`.
2. `mksquashfs` → `filesystem.squashfs` (includes `/boot`, so the **installed** system has
   a kernel+initrd when it's cloned from the live root).
3. Copies kernel+initrd to `/live/` and writes `boot/grub/grub.cfg` (normal and "VGA safe mode" entries).
4. **`grub-mkrescue`** assembles `rocola-i386.img`: a **hybrid ISO (isohybrid)** with El Torito for
   **BIOS** (i386-pc GRUB core) **and x64 UEFI** (EFI image + `/EFI/BOOT/BOOTX64.EFI`).

All of this runs without privileges or loop devices: `grub-mkrescue` works in user space
(xorriso and mtools), so `make image` uses a plain container, no `--privileged`. That's what
makes it possible to build on WSL2 and in CI, where `losetup -P` doesn't create the partition nodes. The
resulting `.img` is written with `dd` and boots via BIOS and UEFI; live-boot mounts the squashfs with an
overlay in RAM.

Result: `out/rocola-i386.img`, a hybrid ISO bootable via BIOS and x64 UEFI.

## Step 4 — Flash (`make flash DEV=/dev/sdX`)

`dd` the image to the USB drive. See [10 · Flashing the USB drive](10-flashing-usb.en.md).

## Quick check

```bash
file out/rocola-i386.img          # ISO 9660 / boot sector (isohybrid)
xorriso -indev out/rocola-i386.img -report_el_torito plain   # BIOS + UEFI entries

# Test in QEMU (the image is a bootable ISO; use it as a cdrom):
qemu-system-i386 -cdrom out/rocola-i386.img -m 2048                                   # BIOS
qemu-system-x86_64 -bios /usr/share/ovmf/OVMF.fd -cdrom out/rocola-i386.img -m 2048   # UEFI x64
```

> The `.img` is a hybrid ISO: it boots just the same when written to a USB drive with `dd` (`dd if=…img of=/dev/sdX`).

Next: [03 · Boot and live mode](03-boot-and-live.en.md).