# 02 · Pipeline de build

De código a pendrive en tres pasos: **SO (Docker) → rootfs → imagen booteable**.

```
os/Dockerfile ──build──► imagen Docker del SO ──export──► out/rootfs.tar
                                                              │
                          image/build-image.sh (privilegiado)│
                                                              ▼
                                                   out/rocola-i386.img ──flash──► pendrive
```

## Requisitos del host

- **Docker** y **make**. Nada más.
- En CPUs **x86-64**, Docker ejecuta los contenedores `linux/386` de forma nativa (no hace falta
  emulador). En hosts que no puedan, instalá binfmt una sola vez:
  ```bash
  docker run --privileged --rm tonistiigi/binfmt --install all
  ```
- `make image` corre con un `docker run` **normal**: no necesita `--privileged`, loop devices ni
  `/dev` (usa `grub-mkrescue`). Por eso funciona en **WSL2** y en CI.

## Paso 1 — SO como imagen Docker (`make rootfs`)

`os/Dockerfile` parte de `i386/debian:bookworm` e instala el set mínimo (ver `os/packages.list`):
Xorg, MPD, SDL2/pygame-ce, switchres, kernel `linux-image-686-pae`, `live-boot`, GRUB, etc. Luego
copia `os/rootfs-overlay/` (configs, systemd units, la app) sobre el rootfs.

> Por qué bookworm: Debian 13 (trixie) discontinuó el kernel/instalador i386. Para un sistema i386
> **booteable**, bookworm es la base correcta.

## Paso 2 — Exportar el rootfs (`make export`)

`docker create` + `docker export` vuelcan el filesystem de la imagen a `out/rootfs.tar`. Como el
kernel, `live-boot` y GRUB se instalaron en el paso 1, el rootfs es **autosuficiente**.

## Paso 3 — Armar la imagen booteable (`make image`)

`image/Dockerfile.builder` trae el tooling (`mksquashfs`, `xorriso`, `mtools`, `grub-pc-bin`,
`grub-efi-amd64-bin`). `build-image.sh`:

1. Desempaqueta `rootfs.tar`.
2. `mksquashfs` → `filesystem.squashfs` (incluye `/boot`, para que el sistema **instalado** tenga
   kernel+initrd al clonarse desde la raíz viva).
3. Copia kernel+initrd a `/live/` y escribe `boot/grub/grub.cfg` (entradas normal y "modo seguro VGA").
4. **`grub-mkrescue`** ensambla `rocola-i386.img`: una **ISO híbrida (isohybrid)** con El Torito para
   **BIOS** (core GRUB i386-pc) **y UEFI x64** (imagen EFI + `/EFI/BOOT/BOOTX64.EFI`).

> **Sin privilegios ni loop devices.** `grub-mkrescue` trabaja en espacio de usuario (xorriso +
> mtools), así que `make image` corre con un `docker run` normal —no `--privileged`—. Esto es lo que
> permite construir en **WSL2/CI**, donde `losetup -P` no crea los nodos de partición. El `.img`
> resultante se graba con `dd` y bootea por BIOS y UEFI; live-boot monta el squashfs con overlay en RAM.

Resultado: `out/rocola-i386.img`, ISO híbrida booteable por BIOS y por UEFI x64.

## Paso 4 — Grabar (`make flash DEV=/dev/sdX`)

`dd` de la imagen al pendrive. Ver [10 · Grabar el pendrive](10-flashing-usb.md).

## Verificación rápida

```bash
file out/rocola-i386.img          # ISO 9660 / boot sector (isohybrid)
xorriso -indev out/rocola-i386.img -report_el_torito plain   # entradas BIOS + UEFI

# Probar en QEMU (la imagen es una ISO booteable; usar como cdrom):
qemu-system-i386 -cdrom out/rocola-i386.img -m 2048                                   # BIOS
qemu-system-i386 -bios /usr/share/ovmf/OVMF.fd -cdrom out/rocola-i386.img -m 2048     # UEFI x64
```

> El `.img` es una ISO híbrida: bootea igual grabada con `dd` a un pendrive (`dd if=…img of=/dev/sdX`).

Siguiente: [03 · Boot y modo live](03-boot-and-live.md).
