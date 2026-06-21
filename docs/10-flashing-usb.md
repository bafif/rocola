# 10 · Grabar el pendrive

Cómo pasar la imagen de la rocola a un pendrive. **Esto borra el pendrive por completo.**

La imagen es una **ISO 9660 híbrida (isohybrid)**: el mismo archivo arranca por **BIOS y UEFI x64**
y se puede grabar con `dd`, Rufus o balenaEtcher, o copiar a Ventoy. `make image` la deja como
`out/rocola-i386.img`; el Release la publica como `rocola-i386-<versión>.iso` (mismo contenido,
extensión `.iso` para que Windows/Rufus/Ventoy la reconozcan sin dudar).

## Requisitos

- Un pendrive de **≥ 4 GB** (recomendado 8 GB+).
- La imagen: `out/rocola-i386.img` recién construida (ver [02](02-build-pipeline.md)) **o** el
  `.iso` descargado desde [Releases](https://github.com/bafif/rocola/releases/latest).

## En Windows (Rufus / Ventoy / balenaEtcher)

Descargá el `.iso` del Release y usá una de estas:

- **Rufus**: *Dispositivo* = tu pendrive → *Seleccionar* el `.iso` → *Empezar*. Si pregunta el modo,
  elegí **"Escribir en modo Imagen DD"** (la ISO es híbrida; el modo DD respeta el MBR/El Torito).
  Qué significan MBR/GPT, "fixes para BIOS viejo", "UEFI media validation", etc. y por qué en modo
  DD no hace falta tocarlas: [13 · Grabar con Rufus](13-rufus-windows.md).
- **Ventoy**: instalá Ventoy en el pendrive **una sola vez** (`Ventoy2Disk.exe`) y después **copiá**
  el `.iso` a la partición de Ventoy. Para actualizar, reemplazás el archivo; no reformateás.
- **balenaEtcher**: *Flash from file* → el `.iso` → elegí el pendrive → *Flash*.

Verificá la descarga antes de grabar (PowerShell):

```powershell
Get-FileHash rocola-i386-*.iso -Algorithm SHA256   # comparar con SHA256SUMS.txt del Release
```

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
