# 10 · Grabar el pendrive

Cómo pasar `out/rocola-i386.img` a un pendrive. **Esto borra el pendrive por completo.**

## Requisitos

- Un pendrive de **≥ 4 GB** (recomendado 8 GB+).
- La imagen ya construida: `out/rocola-i386.img` (ver [02](02-build-pipeline.md)).

## Identificar el dispositivo (¡con cuidado!)

```bash
lsblk -dpo NAME,SIZE,MODEL,TRAN      # buscá tu pendrive por tamaño/modelo, TRAN=usb
```

Anotá el **device del disco entero** (p. ej. `/dev/sdb`), **no** una partición (`/dev/sdb1`).

> ⚠️ Elegir el disco equivocado destruye sus datos. Verificá dos veces (tamaño + modelo + que sea USB).

## Opción A — `make flash`

```bash
make flash DEV=/dev/sdb
```

Pide una confirmación (`si`) y luego graba con `dd ... conv=fsync` + `sync`.

## Opción B — `dd` manual

```bash
sudo dd if=out/rocola-i386.img of=/dev/sdb bs=4M status=progress conv=fsync
sync
```

## Opción C — Herramienta gráfica

Usá **balenaEtcher**, GNOME Disks o similar y seleccioná `out/rocola-i386.img`. Es lo más a prueba de
errores para no equivocar el disco.

## Verificar el grabado

```bash
sudo cmp -n $(stat -c%s out/rocola-i386.img) out/rocola-i386.img /dev/sdb && echo OK
```

(Compara byte a byte el tamaño de la imagen.)

## Probar sin hardware (QEMU)

```bash
qemu-system-i386 -hda out/rocola-i386.img -m 2048                                   # BIOS
qemu-system-i386 -bios /usr/share/ovmf/OVMF.fd -hda out/rocola-i386.img -m 2048     # UEFI x64
```

## Bootear en la PC vieja

Entrá al menú de booteo (suele ser F12/F8/Esc/Supr según el equipo) y elegí el pendrive. Si no
aparece, habilitá "USB boot"/"Legacy boot" en la BIOS.

Siguiente: [11 · Resolución de problemas](11-troubleshooting.md).
