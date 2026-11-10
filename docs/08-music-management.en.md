# 08 · Music management

*English · [Español](08-music-management.md)*

There are two ways to load songs, and you can combine them: **preloaded in the image** and **imported from a 2nd USB drive**.
The library lives on a **persistent data partition** (`/music`).

## Where the music lives

| Context | Path | Persists |
|---------|------|----------|
| Live (USB stick) | `/music` is the preloaded folder from the squashfs, mounted on top; anything imported stays in RAM | no (the installer moves it to the disk) |
| Installed | **`/music`** partition (ext4, separate from ROOT) | **yes** |

MPD points its `music_directory` at `/music`. Keeping it apart from ROOT lets you **reinstall/upgrade the OS
without losing your songs**.

## Option 1 — Preloaded in the image

Before building, put music folders in:

```
os/rootfs-overlay/opt/rocola/music/
```

(that path is ignored by git except for `.gitkeep`, so heavy audio doesn't get versioned). On the USB stick,
`rocola-music-import` mounts that folder on top of `/music` instead of copying it: the live system runs in RAM,
and a copy took up the library twice in memory. When installing, the installer copies it to the disk's `/music`
partition (along with whatever was imported during the live session) if that partition has no music, so it
doesn't eat into the system's 12 GB. MPD scans it at boot. Handy for handing over the USB stick "with music
already on it".

## Option 2 — Import from a 2nd USB drive

1. Plug in a USB stick with your songs (in the root or in folders, e.g. `Music/Artist/Album/`),
   either while the jukebox is running or before turning it on. FAT32, exFAT, NTFS and ext2/3/4 all work.
2. udev detects it (`/etc/udev/rules.d/90-rocola-usb-music.rules`) and starts
   `rocola-usb-music@<dispositivo>.service`, which mounts each partition **read-only** under
   `/run/rocola-usb/`. There's nothing to confirm: the USB stick is never modified.
3. `rocola-music-import` copies the audio (mp3, flac, ogg, m4a, wav, opus, aac, case-insensitive:
   `TEMA01.MP3` gets in too) and the folder artwork (`cover.*`, `folder.*`) to `/music`, without
   overwriting what's already there, and asks MPD for a rescan. Other images (the photos on a
   USB stick) and folders with no audio aren't copied.
4. The UI library reloads on its own when MPD finishes scanning.
5. The USB stick is left unmounted: you can pull it out once the service finishes
   (`journalctl -u 'rocola-usb-music@*'` shows the "done").

Anything that's already mounted (the jukebox's own USB stick, or a USB disk the system was installed on)
is left alone. In live mode `/music` lives in RAM: whatever you import is lost on shutdown; on the installed
system it stays on the music partition.

```
2nd USB ──udev──► rocola-usb-music@sdX1 ──mount ro──► rocola-music-import ──► /music/… ──► MPD ──► UI
```

## Recommended layout

```
/music/
  Artista/
    Álbum/
      01 - Tema.flac
      cover.jpg
```

An album's cover is the `cover.jpg` (or `.png`/`.webp`) in its folder, or the image embedded
in the files. MPD only finds `cover.*` spelled exactly like that; the USB import adds a
`cover.<ext>` (a hard link, taking up no space) to every folder that only has `Folder.jpg`,
`COVER.JPG` or similar.

It's not mandatory: MPD indexes any folder. The UI groups by **tags** (artist, album,
track number), not by folders; a track without tags shows up under its file name, in
"(no artist)". See [07](07-rocola-app.en.md).

## Rescanning manually

From the jukebox menu ("Update library") or, from the console, `mpc update`.

Next: [09 · Branding](09-branding-theming.en.md).