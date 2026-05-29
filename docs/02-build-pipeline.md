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

- **Docker** con soporte multiarch para `linux/386`:
  ```bash
  docker run --privileged --rm tonistiigi/binfmt --install all   # una sola vez
  ```
- **make**.
- Para `make image`: capacidad de correr `docker run --privileged` (usa loop devices + GRUB).

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

`image/Dockerfile.builder` trae el tooling (`mksquashfs`, `grub-pc-bin`, `grub-efi-amd64-bin`,
`genimage`, `dosfstools`, `e2fsprogs`). `build-image.sh`, dentro de un contenedor **privilegiado**:

1. Desempaqueta `rootfs.tar`.
2. `mksquashfs` → `filesystem.squashfs`.
3. `genimage` (según `genimage.cfg`) arma `rocola-i386.img` con:
   - **MBR híbrido**: GRUB-PC para BIOS.
   - **ESP (FAT32)** con GRUB-EFI amd64 para UEFI x64.
   - **Partición live** con `filesystem.squashfs` + kernel + initrd (`live-boot`).

Resultado: `out/rocola-i386.img`, booteable por BIOS y por UEFI x64.

## Paso 4 — Grabar (`make flash DEV=/dev/sdX`)

`dd` de la imagen al pendrive. Ver [10 · Grabar el pendrive](10-flashing-usb.md).

## Verificación rápida

```bash
fdisk -l out/rocola-i386.img      # ver particiones (ESP + live)
qemu-system-i386 -hda out/rocola-i386.img -m 2048           # BIOS
qemu-system-i386 -bios /usr/share/ovmf/OVMF.fd -hda out/rocola-i386.img -m 2048   # UEFI
```

Siguiente: [03 · Boot y modo live](03-boot-and-live.md).
