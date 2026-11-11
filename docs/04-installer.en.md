# 04 · Guided installer

*English · [Español](04-installer.md)*

Clones the OS from the USB stick to the internal disk. **Manually triggered** (not automatic) and with explicit
confirmation: the system **never** formats a disk on its own.

## How it's triggered

From the live jukebox: menu (**F10** or arcade button 3) → **Install to disk** (the option only shows up when the
jukebox is running from the USB stick). The app isn't root: it asks systemd to start `rocola-installer.service`, and
a polkit rule lets the `rocola` user start that unit and no other. The unit switches to the tty8 console, runs
`rocola-install` (source in `installer/`, linked in `/usr/local/bin/`) as root and goes back to the UI when it's
done. From a console it's the same thing: `systemctl start rocola-installer`.

The first thing it asks is the language (Spanish or English). The jukebox's current language is
preselected (the one from the "Language / Idioma" menu, the "Rocola — English" GRUB entry, or the
locale), and whichever you pick becomes the language of the installed jukebox.

It's a `whiptail` TUI driven by **keyboard**: the confirmation is typed, and an arcade encoder in joystick mode
doesn't send keys to a text console. Installing is a one-time thing; plugging in a keyboard for it is enough.

## Flow

```
1. Language              → Spanish | English; the jukebox's own comes preselected, and the
                           choice is saved on the installed disk (/etc/rocola/language.conf)
2. Disk detection        → lists model + size of each /dev/sdX, /dev/nvmeX, etc.
                           (the ones under 14 GB are flagged as "too small")
3. Selection             → pick the target disk (14 GB minimum)
4. Confirmation          → shows what's going to be erased and asks you to type "ERASE"
                           ("BORRAR" if you picked Spanish)
5. Target partitioning (GPT):
     ┌─────────┬──────────┬──────────────┬───────────────────────────┐
     │ BIOSBOOT│ ESP 256M │ ROOT 12G     │ DATA /music (rest)        │
     │ 2M ef02 │ FAT32    │ ext4         │ ext4 (persistent)         │
     └─────────┴──────────┴──────────────┴───────────────────────────┘
6. Cloning               → rsync of the live system (/) → ROOT (excludes /proc,/sys,/dev,/music…)
                           The preloaded music (and whatever was imported in the live session) goes
                           to the /music partition, if it has no music; it doesn't take up ROOT.
7. Monitor type          → automatic | VGA | 15 kHz → saved in /etc/rocola/display.conf (doc 05)
8. Bootloader            → GRUB BIOS (i386-pc, embedded in BIOSBOOT) + GRUB-EFI amd64
                           (BOOTX64.EFI on the ESP, --removable); /etc/fstab by UUID.
                           If the USB stick booted with the default entry (nomodeset)
                           and the monitor isn't 15 kHz, the disk boots the same way: same
                           generic video (/etc/default/grub.d/rocola-video.cfg).
9. Reboot                → the PC boots the jukebox from the disk, on its own
```

## Safety (anti-wipe)

- **Manual** disk selection; never "the first one it finds".
- Clear summary of the destructive operation before touching anything.
- Typed confirmation (writing a word), not just "Enter".
- Detection and warning if the target is the installation **USB stick itself** (it's excluded).
- Runs only from the USB stick: on an installed jukebox the option doesn't show up and the installer refuses to run,
  because the system's own disk would show up as a target.

## Partition layout and why

| Part | Type | Reason |
|------|------|--------|
| BIOSBOOT | `ef02` (2 MiB, no FS) | **required to boot via BIOS from GPT**: GRUB embeds its `core.img` there (GPT has no post-MBR gap like MBR does). Without it, `grub-install --target=i386-pc` fails. |
| ESP | FAT32 (`ef00`) | required to boot via UEFI x64 (`/EFI/BOOT/BOOTX64.EFI`) |
| ROOT | ext4 | system; it's **rewritten** on every (re)install |
| `/music` | ext4 | the music; **persists** across reinstalls |

With `/music` on its own partition you can update the OS without losing the music. And the GPT layout with the BIOS
Boot Partition plus the ESP lets the same disk boot via BIOS and via UEFI x64.

The full install (partitioning, cloning, GRUB) is tested in QEMU, and the resulting disk boots to the UI via BIOS
and via UEFI (see [12 · Verification](12-verificacion.en.md)).

## Reinstalling / updating

Running the installer again on the same disk rewrites ROOT but can **preserve** the `/music` partition (an option in
the TUI). See [08 · Music](08-music-management.en.md).

## Unattended mode (test / CI)

To validate the installer without intervention (QEMU/CI), `rocola-install` accepts environment variables that
replace the TUI prompts:

```bash
ROCOLA_UNATTENDED=1 ROCOLA_TARGET=/dev/sdX \
  ROCOLA_KEEP_MUSIC=no ROCOLA_DISPLAY=auto  rocola-install
```

`ROCOLA_LANG=en` (or `es`) also sets the language of the installed jukebox; without it, the jukebox
follows its locale.

It's not used in normal operation: the jukebox menu always launches the interactive flow with confirmation. It's used
by the test harness (`rocola-selftest.service`, which is only activated with `rocola.selftest` on the kernel command
line); see [12 · Verification](12-verificacion.en.md).

Next: [05 · VGA and 15 kHz video](05-display-crt-15khz.en.md).