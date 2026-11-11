# 10 · Flashing the USB drive

*English · [Español](10-flashing-usb.md)*

How to put the jukebox image on a USB drive. Keep in mind the drive gets wiped completely.

The image is a **hybrid ISO 9660 (isohybrid)**: the same file boots on **BIOS and UEFI x64**
and can be written with `dd`, Rufus or balenaEtcher, or copied to Ventoy. `make image` outputs it as
`out/rocola-i386.img`; the Release publishes it as `rocola-i386-<version>.iso` (same content,
`.iso` extension so Windows/Rufus/Ventoy recognize it without hesitation).

## Requirements

- A USB drive of **1 GB or more**: the image takes about 671 MiB and the live system does not
  write to the stick (music comes in from another stick, see [08](08-music-management.en.md)).
- The image: a freshly built `out/rocola-i386.img` (see [02](02-build-pipeline.en.md)) **or** the
  `.iso` downloaded from [Releases](https://github.com/bafif/rocola/releases/latest).

## On Windows (Rufus / Ventoy / balenaEtcher)

Download the `.iso` from the Release and use one of these:

- **Rufus**: *Device* = your USB drive → *SELECT* the `.iso` → *START*. If it asks for the mode,
  choose **"Write in DD Image mode"** (the ISO is hybrid; DD mode preserves the MBR/El Torito).
  What MBR/GPT, "fixes for old BIOSes", "UEFI media validation", etc. mean, and why you don't need to
  touch them in DD mode: [13 · Flashing with Rufus](13-rufus-windows.en.md).
- **Ventoy**: install Ventoy on the drive **just once** (`Ventoy2Disk.exe`) and then **copy**
  the `.iso` to the Ventoy partition. To update, you replace the file; no reformatting.
- **balenaEtcher**: *Flash from file* → the `.iso` → pick the USB drive → *Flash*.

Verify the download before flashing (PowerShell):

```powershell
Get-FileHash rocola-i386-*.iso -Algorithm SHA256   # compare against SHA256SUMS.txt from the Release
```

## Identifying the device

```bash
lsblk -dpo NAME,SIZE,MODEL,TRAN      # find your USB drive by size/model, TRAN=usb
```

Write down the device for the whole disk (for example `/dev/sdb`), not a partition
(`/dev/sdb1`).

If you pick the wrong disk, you lose whatever's on it. Before flashing, double-check the size, the
model, and that it's USB.

## Option A — `make flash`

```bash
make flash DEV=/dev/sdb
```

It asks for confirmation (`si`) and then writes with `dd ... conv=fsync` + `sync`.

## Option B — Manual `dd`

```bash
sudo dd if=out/rocola-i386.img of=/dev/sdb bs=4M status=progress conv=fsync
sync
```

## Option C — Graphical tool

Use **balenaEtcher**, GNOME Disks or similar and select `out/rocola-i386.img`. It's the most
foolproof way to avoid picking the wrong disk.

## Verifying the write

```bash
sudo cmp -n $(stat -c%s out/rocola-i386.img) out/rocola-i386.img /dev/sdb && echo OK
```

(Compares byte by byte up to the size of the image.)

## Testing without hardware (QEMU)

```bash
qemu-system-i386 -hda out/rocola-i386.img -m 2048                                   # BIOS
qemu-system-x86_64 -bios /usr/share/ovmf/OVMF.fd -hda out/rocola-i386.img -m 2048   # UEFI x64
```

## Booting on the old PC

Open the boot menu (usually F12/F8/Esc/Del depending on the machine) and choose the USB drive. If it
doesn't show up, enable "USB boot"/"Legacy boot" in the BIOS.

Next: [11 · Troubleshooting](11-troubleshooting.en.md).