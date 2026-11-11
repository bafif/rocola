# 13 · Writing with Rufus (Windows)

*English · [Español](13-rufus-windows.md)*

[Rufus](https://rufus.ie) is the most common way to write the `.iso` to a USB drive on Windows. The
jukebox image is a hybrid ISO 9660 (isohybrid): it already includes a protective MBR and GPT,
`grub2-mbr` for BIOS, the EFI partition (`/efi.img`) for UEFI x64, and El Torito with
*boot-info-table*. The whole bootable medium is inside the file, so all you need is to **write it in
DD mode**: in that mode every other option is disabled or ignored.

## The steps

1. **Device**: your USB drive. Double-check which one it is, because it gets completely erased.
2. **Boot selection**: *Disk or ISO image*, then **SELECT** and choose `rocola-i386-<version>.iso`.
3. **START**.
4. *ISOHybrid image detected* shows up. Choose **“Write in DD Image mode”**.
5. Confirm the erase and wait for it to finish.

In DD mode, Rufus copies the image byte for byte, just like `dd if=…iso of=/dev/sdX`. You don't need
to pick MBR or GPT, file system, cluster size, format or “fixes”: Rufus doesn't build anything, it
just copies.

## Why DD mode and not ISO mode?

Rufus only offers this choice with hybrid images:

- **DD mode**: copies the image byte for byte and leaves the MBR, the GPT, the EFI partition and the
  embedded GRUB exactly as they were built. This is what this image needs.
- **ISO mode**: Rufus discards the ISO's structure, creates its own FAT partition, copies the
  files and installs its own boot loader on them. With GRUB-based images like this one
  (made with `grub-mkrescue`), booting may not end up set up correctly and can fail.

So for the jukebox, always DD mode.

## What each option means (and why you don't touch it in DD mode)

They're all in the Rufus window (some under *Show advanced drive/format properties*). In DD mode
they're disabled or ignored; they'd only matter if you were writing in ISO mode.

| Rufus option | What it does | In DD mode |
|-----------------|----------|------------|
| **Partition scheme: MBR / GPT** | The partition table Rufus builds (MBR = old BIOS; GPT = pure UEFI). | Ignored: the ISO's own is used (protective MBR + GPT). |
| **Target system: BIOS / UEFI** | Which firmware Rufus prepares booting for. | Ignored: the image already boots via BIOS **and** UEFI x64. |
| **Add fixes for old BIOSes (extra partition, align, etc.)** | A Rufus tweak that adds a small partition and aligns, for BIOSes that refuse to boot from USB. | Ignored. The image brings its own BIOS booting (`grub2-mbr` + boot-info-table); the checkbox is something Rufus adds only in ISO mode. |
| **Enable UEFI media validation** | (Rufus 4.5+) Inserts a validator that, at **boot**, recomputes an MD5 of the files to detect corruption/tampering of the USB drive. Modifies the medium → **ISO mode only**. | Doesn't apply. (To verify the download, use `SHA256SUMS.txt`, see below.) |
| **File system / Cluster size** | Which FAT/NTFS and cluster size the partition Rufus creates uses. | Ignored: the content is defined by the ISO. |
| **Quick format** | Quick format (metadata only) vs. full (checks for bad blocks, slow). | Irrelevant. |

## UEFI and Secure Boot

On a UEFI PC you need to **disable Secure Boot** in the firmware before booting: the image's
`EFI/BOOT/BOOTX64.EFI` comes from `grub-efi-amd64` and isn't signed, so with Secure
Boot enabled UEFI booting is blocked. This doesn't apply to BIOS (Legacy) booting.

The UEFI x64 loader loads an i386 kernel; 32-bit UEFI is out of scope for the project (see
[ARCHITECTURE.en.md](../ARCHITECTURE.en.md)).

## Verifying the download

Before writing, it's a good idea to confirm the `.iso` downloaded completely and without corruption,
by comparing it against the Release's `SHA256SUMS.txt`:

```powershell
# PowerShell
Get-FileHash rocola-i386-<version>.iso -Algorithm SHA256
```

The value must match the one in `SHA256SUMS.txt`.

## If Rufus doesn't offer DD mode

It's rare with this image, but if it only lets you use ISO mode (or booting fails), use a tool
that always writes raw:

- **balenaEtcher** (cross-platform): *Flash from file*, the `.iso`, the USB drive and *Flash*. It
  always writes raw.
- **Ventoy**: install it once on the USB drive and copy the `.iso` to its partition (see
  [10 · Writing the USB drive](10-flashing-usb.en.md)).
- On Linux/macOS: `dd if=rocola-i386-<version>.iso of=/dev/sdX bs=4M status=progress conv=fsync`.

---

See also: [10 · Writing the USB drive](10-flashing-usb.en.md) ·
[11 · Troubleshooting](11-troubleshooting.en.md).