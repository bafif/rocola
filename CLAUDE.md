# CLAUDE.md — Guía para Claude Code

Contexto operativo para trabajar en este repo. Leer junto con [ARCHITECTURE.md](ARCHITECTURE.md).

## Qué es

**Rocola**: un pendrive booteable basado en **Debian i386** que convierte PCs de escritorio viejas
en rocolas (jukebox) dedicadas. Live en el USB + instalador guiado que clona el SO al disco interno.
App propia SDL2 + MPD, controles de arcade, soporte CRT (VGA y 15 kHz).

## Decisiones fijas (no re-litigar sin pedirlo)

- **Arquitectura: i386.** Base **`i386/debian:bookworm`** (NO trixie: discontinuó kernel/booteable i386).
- **Kernel:** `linux-image-686-pae` por defecto; `686` (no-PAE) como fallback para CPUs muy viejas.
- **Arranque:** BIOS (32/64-bit) + **UEFI x64** (`grub-efi-amd64` carga kernel i386). UEFI 32-bit: fuera de alcance.
- **App:** UI propia con **SDL2 / pygame-ce** (Python) sobre **MPD**. No usar Kodi/navegador.
- **Instalación:** live + **disparo manual** → instalador guiado. **Nunca** auto-formatear un disco.
- **Música:** precargada en la imagen **+** import desde 2º USB a partición `/music` persistente.
- **Idioma:** documentación y UI en **español**. Código/identificadores en inglés.
- **Licencia:** MIT. Repo: `bafif/rocola` (público).

## Layout

```
os/         Dockerfile (FROM i386/debian:bookworm) + packages.list + rootfs-overlay/
image/      Dockerfile.builder + build-image.sh + genimage.cfg  (rootfs -> .img)
app/        UI SDL2 (Python): rocola/ (ui, mpd client, input, config, theme) + assets/
installer/  rocola-install (whiptail TUI)
display/    modelines/ + rocola-display-setup (VGA vs 15 kHz, switchres)
docs/       01..11 — un doc por subsistema
```

## Comandos

```bash
make rootfs     # build de la imagen Docker del SO
make image      # rootfs -> out/rocola-i386.img (privilegiado: loop/grub)
make flash DEV=/dev/sdX   # graba el pendrive (DESTRUCTIVO)
make app-run    # corre la UI localmente (necesita MPD + python3-pygame)
make clean
```

- `make image` requiere `docker run --privileged` (usa loop devices y `grub-install`).
- Para `linux/386` en build hace falta binfmt/qemu configurado (`docker run --privileged --rm tonistiigi/binfmt --install all` una vez).

## Convenciones

- **Scripts shell**: `bash`, `set -euo pipefail`, ejecutables (`chmod +x`), shebang explícito.
- **Python (app/)**: stdlib + `pygame-ce`; cliente MPD propio por socket (sin deps pesadas). Mantener
  liviano: target 2 GB RAM / i386. Evitar frameworks grandes.
- **Archivos del SO**: van en `os/rootfs-overlay/` replicando la ruta destino (p. ej.
  `os/rootfs-overlay/etc/systemd/system/rocola.service` → `/etc/systemd/system/rocola.service`).
- **Branding**: nunca hardcodear logos/colores en el código; leerlos de `app/assets/` y la config del tema.

## Gotchas

- **No** asumir que el host tiene `debootstrap`/`mkosi`/`live-build`: todo corre dentro de Docker.
- **15 kHz** no es universal: depende de GPU/driver. Siempre dejar fallback a VGA. No prometer
  zero-config absoluto en el código ni en docs; el tipo de monitor se elige 1 vez al instalar.
- El modo **live corre en overlay/RAM**: cambios al sistema en vivo no persisten (es a propósito).
- La música del usuario vive en `/music` (partición aparte): no escribir música al rootfs en runtime.
- Imágenes/fuentes binarias: si faltan, usar placeholders en `app/assets/` y documentarlo; no romper el build.

## Git

- Commits con `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Commit/push solo cuando el usuario lo pida. PRs con la firma de Claude Code.
