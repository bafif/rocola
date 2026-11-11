# 11 · Troubleshooting

*English · [Español](11-troubleshooting.md)*

## Build

**`make rootfs` fails with "exec format error" / i386 won't run**
The host can't run i386 binaries. On x86-64 CPUs they usually run natively; if not, register
binfmt once with your distribution's emulator:
```bash
sudo pacman -S qemu-user-static qemu-user-static-binfmt   # Arch
sudo apt install qemu-user-static                         # Debian / Ubuntu
```

**`make rootfs` fails with `Failed to fetch ... Unable to connect to deb.debian.org`**
A network blip while downloading packages. The Containerfile already retries (`Acquire::Retries` plus
retrying the install with `--fix-missing`); run `make rootfs` again and it usually completes.

**`make image` fails**
The build uses `grub-mkrescue` (xorriso + mtools), **with no privileges or loop devices**. If it fails,
the builder is usually missing `xorriso`/`mtools`/`grub-pc-bin`/`grub-efi-amd64-bin` (they come from
`image/Containerfile.builder`). It doesn't need `--privileged` or `/dev`.

**The image ends up huge**
Check for preloaded music in `os/rootfs-overlay/opt/rocola/music/` and clean the apt caches in the
Containerfile (`rm -rf /var/lib/apt/lists/*`).

## Boot

**The PC won't boot from the USB stick**
- Enable USB/Legacy boot in the BIOS; try the boot menu (F12/F8/Esc).
- Re-flash the USB stick (see [10](10-flashing-usb.en.md)); it may have been only partially written.
- On UEFI, turn Secure Boot off: the jukebox's boot loader isn't signed (see [13](13-rufus-windows.en.md)).
- For very old UEFI: use BIOS/CSM mode.
- If it hangs right after the kernel starts on a very old CPU (some Pentium M, VIA C3, AMD
  Geode), try the "Rocola — CPU sin PAE · without PAE (kernel 686)" entry.

**It boots but stays at the console and the jukebox doesn't open**
The UI is launched by the tty1 autologin (`~rocola/.bash_profile` → `startx` → `rocola-session`).
To see the error:
```bash
journalctl -u rocola-display-setup.service -b        # video config
journalctl -b | grep -iE 'startx|xinit|Xorg|rocola-session'
```
It's usually video (see below) or Xorg not starting.

If the UI crashes 5 times within 2 minutes, the autologin stops relaunching it and the console shows
how to proceed. To get to the console on purpose: the GRUB entry "Rocola — consola de recuperación ·
recovery console", both on the USB stick and on the installed disk.
The `rocola` user is in the `systemd-journal` group, so `journalctl` there shows logs for the whole
system without root.

## Troubleshooting SSH (remote)

To debug a jukebox that won't open the UI, the ISO ships an SSH server that's off by default. It's only
enabled if you boot with the GRUB entry **"Rocola — SSH por red · SSH troubleshooting"** (which passes
`rocola.ssh` on the kernel command line); on a normal boot sshd doesn't start. It logs in as root and
only with a public key, no passwords, and the host keys are generated in RAM on every boot, so
the image doesn't carry fixed keys.

The official ISO doesn't trust any key: `os/rootfs-overlay/root/.ssh/authorized_keys` is empty
on purpose, so even if someone boots with `rocola.ssh`, nobody gets in. This SSH is for your own
build.

**Enabling it in your own build:**
1. Paste your **public** key into `os/rootfs-overlay/root/.ssh/authorized_keys` (one line, e.g.
   `ssh-ed25519 AAAA... vos@tu-pc`). Never put the private key there.
2. Rebuild and re-flash: `make rootfs && make image`, then `make flash DEV=/dev/sdX`.
3. Boot the PC with the GRUB entry **"Rocola — SSH por red · SSH troubleshooting"**.
4. The jukebox gets an IP via DHCP (systemd-networkd). Find out the IP (on your router, or with a local
   console via `ip -4 addr`) and connect:
   ```bash
   ssh -o StrictHostKeyChecking=accept-new root@<ip>
   ```

The hardened config is in `etc/ssh/sshd_config.d/10-rocola.conf`; the cmdline gate is handled by the
`rocola-ssh-maybe` script (triggered by `rocola-ssh.service` on every boot, but it exits immediately
unless `rocola.ssh` is present).

## Video / CRT

**Black screen or "out of range" on a 15 kHz CRT**
- The hardware may not support 15 kHz on that output (see [05](05-display-crt-15khz.en.md)). Try the
  VGA/modern option.
- To go back to VGA, plug in a VGA monitor and set `MODE=vga` in `/etc/rocola/display.conf` (or
  reinstall choosing VGA).

**Black screen with the "Rocola — GPU / CRT 15 kHz (KMS)" entry**
On some AMD APUs (Picasso, Raven2) the `amdgpu` driver doesn't work with the i386 kernel. Use the
default entry, "Rocola" (see [05](05-display-crt-15khz.en.md#video-driver)).

**Shifted/unsynced picture on a CRT**
Adjust the modeline (position/size) in `display/modelines/`; every CRT varies a bit.

**Modern monitor looks low-res**
With the default entry, the picture goes through the firmware's framebuffer, at the resolution GRUB
leaves. For the monitor's own, boot with "Rocola — GPU / CRT 15 kHz (KMS)"; if you install from that
entry, the disk stays the same. Also check that `display.conf` isn't forcing 15 kHz.

## Audio

**No sound at all**
- `mpc status` to see whether MPD is playing and `mpc outputs` to see its outputs.
- Check the mixer (`alsamixer`): it may be muted or have the volume at 0.
- On PCs with several outputs, pick the right one from the menu ("Audio output") or set it in
  `/etc/rocola/audio.conf`. The commands to check it over SSH are in [14](14-audio.en.md).

## Controls

**The buttons don't respond / do something else**
- Check whether the encoder is in keyboard or joystick mode; both should work (see
  [06](06-arcade-controls.en.md)).
- Menu → "Test controls" shows what each button sends; remap them with `[keys]` and `[buttons]` in
  `/etc/rocola/rocola.toml`.

## Music

**Imported songs don't show up**
- Force a rescan: the "Update library" menu or `mpc update`.
- Check that they were copied to `/music` and that MPD supports the formats.

## Installation

**The installer doesn't list my disk**
- Some uncommon NVMe or RAID disks may need extra modules; if that happens to you, open an issue
  with the model.
- The installation USB stick itself is excluded on purpose.

Something not covered? Open an issue in the repo with the output of `journalctl -b` and the hardware model.