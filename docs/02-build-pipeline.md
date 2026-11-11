# 02 · Pipeline de build

*[English](02-build-pipeline.en.md) · Español*

De código a pendrive en tres pasos: **SO (contenedor) → rootfs → imagen booteable**.

```
os/Containerfile ──build──► imagen del SO ──export──► out/rootfs.tar
                                                          │
                    image/build-image.sh (sin privilegios)│
                                                          ▼
                                               out/rocola-i386.img ──flash──► pendrive
```

## Requisitos del host

- **Podman** (alcanza sin root) y **make**. Nada más.
- En CPUs **x86-64**, los contenedores `linux/386` corren de forma nativa (no hace falta emulador).
  En hosts que no puedan, registrá binfmt una sola vez con el `qemu-user-static` de la distribución
  (en Arch, `qemu-user-static` y `qemu-user-static-binfmt`; en Debian y Ubuntu, `qemu-user-static`).
- `make image` corre en un contenedor **normal**: no necesita `--privileged`, loop devices ni
  `/dev` (usa `grub-mkrescue`). Por eso funciona en **WSL2** y en CI. Tampoco monta nada del repo:
  el rootfs entra y la imagen sale con `podman cp`.

## Paso 1 — SO como imagen de contenedor (`make rootfs`)

`os/Containerfile` parte de `i386/debian:bookworm` e instala el set mínimo (ver `os/packages.list`):
Xorg, MPD, SDL2/pygame, los kernels `linux-image-686-pae` y `linux-image-686` (el de respaldo sin
PAE), `live-boot`, GRUB, etc. Si un initrd queda sin `live-boot`, el build se corta ahí. Luego
copia `os/rootfs-overlay/` (configs, systemd units, la app) sobre el rootfs.

> Por qué bookworm: Debian 13 (trixie) discontinuó el kernel/instalador i386. Para un sistema i386
> **booteable**, bookworm es la base correcta.

## Paso 2 — Exportar el rootfs (`make export`)

`podman create` + `podman export` vuelcan el filesystem de la imagen a `out/rootfs.tar`. Como el
kernel, `live-boot` y GRUB se instalaron en el paso 1, el rootfs es **autosuficiente**.

## Paso 3 — Armar la imagen booteable (`make image`)

`image/Containerfile.builder` trae el tooling (`mksquashfs`, `xorriso`, `mtools`, `grub-pc-bin`,
`grub-efi-amd64-bin`). `make image` crea el contenedor, le copia `rootfs.tar` a `/work` con
`podman cp`, lo arranca y saca `rocola-i386.img` de la misma forma. `build-image.sh`:

1. Desempaqueta `rootfs.tar`.
2. `mksquashfs` → `filesystem.squashfs` (incluye `/boot`, para que el sistema **instalado** tenga
   kernel+initrd al clonarse desde la raíz viva).
3. Copia kernel+initrd a `/live/` y escribe `boot/grub/grub.cfg` con las entradas del menú (ver
   [03 · Menú de arranque](03-boot-and-live.md#menú-de-arranque)).
4. **`grub-mkrescue`** ensambla `rocola-i386.img`: una **ISO híbrida (isohybrid)** con El Torito para
   **BIOS** (core GRUB i386-pc) **y UEFI x64** (imagen EFI + `/EFI/BOOT/BOOTX64.EFI`).

`grub-mkrescue` trabaja en espacio de usuario (xorriso y mtools), así que no hacen falta loop
devices: en WSL2 y en el CI `losetup -P` no crea los nodos de las particiones.

Resultado: `out/rocola-i386.img`, ISO híbrida booteable por BIOS y por UEFI x64.

`make image` reutiliza la imagen del SO si ya existe, sin reconstruirla. Después de cambiar algo en
`os/`, `app/`, `installer/` o `display/`, corré `make rootfs` antes de `make image`.

## Paso 4 — Grabar (`make flash DEV=/dev/sdX`)

`dd` de la imagen al pendrive. Ver [10 · Grabar el pendrive](10-flashing-usb.md).

## Versiones publicadas (`make release VERSION=vX.Y.Z`)

Copia la imagen como `out/release/rocola-i386-<versión>.iso` y escribe su `SHA256SUMS.txt`: son los
dos archivos que se suben a cada versión de GitHub. La extensión `.iso` es para que Windows, Rufus y
Ventoy la reconozcan; el contenido es el mismo `.img`.

## Verificación rápida

```bash
file out/rocola-i386.img          # ISO 9660 / boot sector (isohybrid)
xorriso -indev out/rocola-i386.img -report_el_torito plain   # entradas BIOS + UEFI

# Probar en QEMU (la imagen es una ISO booteable; usar como cdrom):
qemu-system-i386 -cdrom out/rocola-i386.img -m 2048                                   # BIOS
qemu-system-x86_64 -bios /usr/share/ovmf/OVMF.fd -cdrom out/rocola-i386.img -m 2048   # UEFI x64
```

> El `.img` es una ISO híbrida: bootea igual grabada con `dd` a un pendrive (`dd if=…img of=/dev/sdX`).

Siguiente: [03 · Boot y modo live](03-boot-and-live.md).
